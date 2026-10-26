"""Manuscript PIC numbers are rebuilt from the frozen production dataset (paper/manuscript/pic_data)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
PIC_DATA = ROOT / "paper" / "manuscript" / "pic_data"

pytestmark = pytest.mark.skipif(not (PIC_DATA / "production_cases.csv").exists(), reason="no frozen PIC data")


def test_frozen_dataset_has_every_production_case():
    from plasma_column.schema import ScanMatrixConfig

    matrix = ScanMatrixConfig.from_yaml(ROOT / "cases" / "production.yaml")
    cases = pd.read_csv(PIC_DATA / "production_cases.csv")
    assert set(cases.case_name) == {c.case_name for c in matrix.cases}
    assert (cases.final_step == 23000).all()
    # Net core value never overcompensated; vacuum has no plasma.
    assert (cases.eta_net_local <= 1.0).all()
    assert cases.set_index("case_name").loc["vacuum_reference", "seed_fraction"] == 0.0


def test_macros_and_table_from_frozen_data(tmp_path):
    import make_manuscript_pic_results as m

    cases = pd.read_csv(PIC_DATA / "production_cases.csv")
    ts = pd.read_csv(PIC_DATA / "local_eta_vs_t.csv")
    tau_eff = json.loads((PIC_DATA / "provenance.json").read_text())["accelerated_tau_eff_s"]
    macros = m.build_pic_macros(cases, ts, tau_eff)
    assert macros["picncases"] == "15"
    assert all(k.isalpha() for k in macros)  # valid LaTeX command names
    assert float(macros["picHtwoeta"]) > float(macros["picKreta"])
    m.write_case_table(cases, tmp_path / "pic_table.tex")
    rows = [ln for ln in (tmp_path / "pic_table.tex").read_text().splitlines() if ln.endswith("\\\\")]
    assert len(rows) == 15
