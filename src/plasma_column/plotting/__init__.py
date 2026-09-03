"""
src/plasma_column/plotting/__init__.py

Modular plotting pipeline package for plasma column analysis.
Re-exports canonical plotting functions from sub-modules for backwards compatibility:
  - neutralization: Species counts, eta_net, K_eff overlays, growth rates, spatial profiles
  - scan: Multi-case comparison bars, heatmaps, parameter scans, timeseries grids
  - cross_sections: Proton-impact cross-section comparison plots
  - transport: Phase space scatter, RMS beam envelope, optics transport
  - paper_figures: Dedicated manuscript figure generators (fig01–fig10)
"""

from .neutralization import (
    setup_publication_style,
    save_figure,
    write_plot_manifest,
    plot_particle_counts,
    plot_neutralization_evolution,
    plot_keff_over_k0,
    plot_multi_case_neutralization,
    plot_species_growth_rates,
    plot_radial_density_profile,
    plot_neutralization_vs_z,
    plot_bunched_beam_keff,
    plot_neutralization_panel,
)
from .scan import (
    plot_keff_pressure_scan,
    plot_scan_eta_vs_pressure,
    plot_scan_keff_vs_pressure,
    plot_scan_method_comparison_bar,
    plot_scan_heatmap,
    plot_scan_neutralization_timeseries_grid,
    plot_scan_final_eta_bar_by_gas,
)
from .cross_sections import plot_cross_section_comparison
from .transport import plot_phase_space, plot_beam_envelope_transport
from .paper_figures import (
    generate_fig01_axial_injection_concept,
    generate_fig02_plasma_neutralizer_module,
    generate_fig03_cross_sections,
    generate_fig04_neutralization_evolution,
    generate_fig05_inflector_phase_space,
)

__all__ = [
    "setup_publication_style",
    "save_figure",
    "write_plot_manifest",
    "plot_particle_counts",
    "plot_neutralization_evolution",
    "plot_keff_over_k0",
    "plot_multi_case_neutralization",
    "plot_species_growth_rates",
    "plot_radial_density_profile",
    "plot_neutralization_vs_z",
    "plot_keff_pressure_scan",
    "plot_bunched_beam_keff",
    "plot_neutralization_panel",
    "plot_scan_eta_vs_pressure",
    "plot_scan_keff_vs_pressure",
    "plot_scan_method_comparison_bar",
    "plot_scan_heatmap",
    "plot_scan_neutralization_timeseries_grid",
    "plot_scan_final_eta_bar_by_gas",
    "plot_cross_section_comparison",
    "plot_phase_space",
    "plot_beam_envelope_transport",
    "generate_fig01_axial_injection_concept",
    "generate_fig02_plasma_neutralizer_module",
    "generate_fig03_cross_sections",
    "generate_fig04_neutralization_evolution",
    "generate_fig05_inflector_phase_space",
]
