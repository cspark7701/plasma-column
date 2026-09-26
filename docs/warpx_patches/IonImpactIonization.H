/* Copyright 2026
 *
 * This file is an experimental extension for WarpX BackgroundMCC.
 *
 * Ion-impact ionization process:
 *
 *     ion_projectile + neutral_gas -> ion_projectile + gas_ion + electron
 *
 * Example:
 *
 *     p + H2 -> p + H2+ + e-
 *     p + Kr -> p + Kr+ + e-
 *
 * The parent projectile remains in the source species.  One electron and one
 * gas-ion macroparticle are created at the projectile position whenever the
 * MCC event is accepted.
 */

#ifndef WARPX_PARTICLES_COLLISION_ION_IMPACT_IONIZATION_H_
#define WARPX_PARTICLES_COLLISION_ION_IMPACT_IONIZATION_H_

#include "Particles/Collision/ScatteringProcess.H"
#include "Particles/Algorithms/KineticEnergy.H"
#include "Utils/ParticleUtils.H"
#include "Utils/WarpXConst.H"

#include <AMReX_Random.H>
#include <AMReX_REAL.H>

/**
 * \brief Filter functor for ion-impact ionization.
 *
 * The cross-section table is assumed to be tabulated against center-of-mass
 * collision energy in eV.  The background neutral gas is treated as stationary
 * in this first implementation; at 30 keV proton energy, thermal neutral
 * velocities at 300 K are negligible for H2/Kr.
 */
class IonImpactIonizationFilterFunc
{
public:
    IonImpactIonizationFilterFunc (
        ScatteringProcess const& mcc_process,
        double const projectile_mass,
        double const background_mass,
        amrex::ParticleReal const total_collision_prob,
        amrex::ParticleReal const nu_max,
        amrex::ParserExecutor<4> const& n_a_func,
        amrex::Real const t )
        : m_mcc_process(mcc_process.executor()),
          m_projectile_mass(projectile_mass),
          m_background_mass(background_mass),
          m_total_collision_prob(total_collision_prob),
          m_nu_max(nu_max),
          m_n_a_func(n_a_func),
          m_t(t)
    {}

    template <typename PData>
    AMREX_GPU_HOST_DEVICE AMREX_FORCE_INLINE
    bool operator() (
        PData& ptd,
        int const i,
        amrex::RandomEngine const& engine) const noexcept
    {
        using namespace amrex;

        if (Random(engine) > m_total_collision_prob) {
            return false;
        }

        const auto& p = ptd.getSuperParticle(i);

        ParticleReal x, y, z;
        get_particle_position(p, x, y, z);

        const ParticleReal n_a = m_n_a_func(x, y, z, m_t);

        const ParticleReal ux = ptd.m_rdata[PIdx::ux][i];
        const ParticleReal uy = ptd.m_rdata[PIdx::uy][i];
        const ParticleReal uz = ptd.m_rdata[PIdx::uz][i];

        // PIdx::u is gamma*v.  For the present low-energy cyclotron-injection
        // application gamma ~= 1, but use WarpX's collision-energy helper.
        const ParticleReal u2 = ux*ux + uy*uy + uz*uz;
        const ParticleReal u_coll = std::sqrt(u2);

        double gamma, E_coll;
        ParticleUtils::getCollisionEnergy(
            u2, m_projectile_mass, m_background_mass, gamma, E_coll);

        const ParticleReal sigma_E =
            m_mcc_process.getCrossSection(static_cast<ParticleReal>(E_coll));

        const ParticleReal nu_i = n_a * sigma_E * u_coll / m_nu_max;

        return (Random(engine) <= nu_i);
    }

private:
    ScatteringProcess::Executor m_mcc_process;
    double m_projectile_mass;
    double m_background_mass;
    amrex::ParticleReal m_total_collision_prob = 0;
    amrex::ParticleReal m_nu_max = 0;
    amrex::ParserExecutor<4> m_n_a_func;
    amrex::Real m_t;
};


/**
 * \brief Transform functor for ion-impact ionization.
 *
 * For each accepted event, this transform:
 *   1. subtracts the ionization energy from the parent ion projectile;
 *   2. creates a secondary electron with an isotropic fixed kinetic energy;
 *   3. creates a gas ion with a thermal velocity sampled from the neutral gas
 *      temperature.
 *
 * The product macroparticle weights and positions are inherited through
 * SmartCopy before this transform is called.
 */
class IonImpactIonizationTransformFunc
{
public:
    IonImpactIonizationTransformFunc (
        amrex::ParticleReal const energy_cost_eV,
        double const projectile_mass,
        amrex::ParticleReal const electron_energy_eV,
        amrex::ParticleReal const sqrt_kb_m_gas,
        amrex::ParserExecutor<4> const& T_a_func,
        amrex::Real const t )
        : m_energy_cost_eV(energy_cost_eV),
          m_projectile_mass(projectile_mass),
          m_electron_energy_eV(electron_energy_eV),
          m_sqrt_kb_m_gas(sqrt_kb_m_gas),
          m_T_a_func(T_a_func),
          m_t(t)
    {}

    template <typename ElectronData, typename IonData, typename SrcData>
    AMREX_GPU_HOST_DEVICE AMREX_FORCE_INLINE
    void operator() (
        ElectronData& dst_e,
        IonData& dst_i,
        SrcData& src,
        int const i_src,
        int const i_dst_e,
        int const i_dst_i,
        amrex::RandomEngine const& engine) const noexcept
    {
        using namespace amrex;
        using namespace amrex::literals;

        const auto& p = src.getSuperParticle(i_src);

        ParticleReal x, y, z;
        get_particle_position(p, x, y, z);

        // ------------------------------------------------------------------
        // Parent projectile: subtract ionization energy, preserving direction.
        // ------------------------------------------------------------------
        auto& ux = src.m_rdata[PIdx::ux][i_src];
        auto& uy = src.m_rdata[PIdx::uy][i_src];
        auto& uz = src.m_rdata[PIdx::uz][i_src];

        constexpr auto eV = PhysConst::q_e;
        constexpr auto c2 = PhysConst::c2;

        const ParticleReal u2 = ux*ux + uy*uy + uz*uz;
        const auto E_old_J =
            Algorithms::KineticEnergy(ux, uy, uz,
                                      static_cast<ParticleReal>(m_projectile_mass));

        const auto E_loss_J = m_energy_cost_eV * eV;

        if ((u2 > 0._prt) && (E_old_J > E_loss_J)) {
            const auto E_new_J = E_old_J - E_loss_J;
            const auto mc2 = m_projectile_mass * c2;
            const auto u_new =
                std::sqrt(E_new_J * (E_new_J + 2._prt*mc2)
                          * PhysConst::inv_c2)
                / m_projectile_mass;
            const auto scale = static_cast<ParticleReal>(u_new / std::sqrt(u2));
            ux *= scale;
            uy *= scale;
            uz *= scale;
        }

        // ------------------------------------------------------------------
        // Product electron: isotropic emission with fixed secondary energy.
        // A later refinement can sample the Rudd differential spectrum.
        // ------------------------------------------------------------------
        auto& e_ux = dst_e.m_rdata[PIdx::ux][i_dst_e];
        auto& e_uy = dst_e.m_rdata[PIdx::uy][i_dst_e];
        auto& e_uz = dst_e.m_rdata[PIdx::uz][i_dst_e];

        const auto Ee_J = m_electron_energy_eV * eV;
        const auto me_c2 = PhysConst::m_e * c2;
        const ParticleReal ue =
            (Ee_J > 0._prt)
            ? static_cast<ParticleReal>(
                std::sqrt(Ee_J * (Ee_J + 2._prt*me_c2) * PhysConst::inv_c2)
                / PhysConst::m_e )
            : 0._prt;

        ParticleUtils::RandomizeVelocity(e_ux, e_uy, e_uz, ue, engine);

        // ------------------------------------------------------------------
        // Product gas ion: sampled from neutral background temperature.
        // ------------------------------------------------------------------
        auto& i_ux = dst_i.m_rdata[PIdx::ux][i_dst_i];
        auto& i_uy = dst_i.m_rdata[PIdx::uy][i_dst_i];
        auto& i_uz = dst_i.m_rdata[PIdx::uz][i_dst_i];

        const ParticleReal ion_vel_std =
            m_sqrt_kb_m_gas * std::sqrt(m_T_a_func(x, y, z, m_t));

        i_ux = ion_vel_std * RandomNormal(0._prt, 1._prt, engine);
        i_uy = ion_vel_std * RandomNormal(0._prt, 1._prt, engine);
        i_uz = ion_vel_std * RandomNormal(0._prt, 1._prt, engine);
    }

private:
    amrex::ParticleReal m_energy_cost_eV = 0;
    double m_projectile_mass = 0;
    amrex::ParticleReal m_electron_energy_eV = 1;
    amrex::ParticleReal m_sqrt_kb_m_gas = 0;
    amrex::ParserExecutor<4> m_T_a_func;
    amrex::Real m_t;
};

#endif // WARPX_PARTICLES_COLLISION_ION_IMPACT_IONIZATION_H_
