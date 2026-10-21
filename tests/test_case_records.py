"""
tests/test_case_records.py

Provenance of case records (task 97): config.yaml/metadata.json of existing simulation output must not
be replaced by a dry run or a resume-skip, and stage summaries must report case status.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from plasma_column.warpx_io import has_simulation_output, write_case_records

PN_HEADER = ("#[0]step(),[1]time(s),[2]total_macroparticles(),[3]beam_protons_macroparticles(),"
             "[4]plasma_electrons_macroparticles(),[5]gas_ions_macroparticles(),[6]total_weight(),"
             "[7]beam_protons_weight(),[8]plasma_electrons_weight(),[9]gas_ions_weight()\n")


def _fake_run(case_dir: Path, last_step: int) -> None:
    (case_dir / "reducedfiles").mkdir(parents=True)
    rows = [f"{s},{s * 1e-11},3,1,1,1,30,10,9,8\n" for s in (0, last_step)]
    (case_dir / "reducedfiles" / "particle_number.txt").write_text(PN_HEADER + "".join(rows))
    (case_dir / "metadata.json").write_text(json.dumps({"origin": "original run"}))


def test_records_of_existing_output_are_protected(tmp_path):
    _fake_run(tmp_path, 100)
    assert has_simulation_output(tmp_path)
    assert not write_case_records(tmp_path, {"case_name": "x"}, {"origin": "dry run"}, launching=False)
    assert json.loads((tmp_path / "metadata.json").read_text())["origin"] == "original run"

    assert write_case_records(tmp_path, {"case_name": "x"}, {"origin": "restart"}, launching=True)
    assert json.loads((tmp_path / "metadata.json").read_text())["origin"] == "restart"
    assert json.loads((tmp_path / "metadata.prev.json").read_text())["origin"] == "original run"


def test_records_written_for_new_case_dir(tmp_path):
    assert write_case_records(tmp_path / "new", {"case_name": "x"}, {"origin": "dry run"}, launching=False)
    assert (tmp_path / "new" / "config.yaml").exists()


def test_stage_collect_case_status(tmp_path):
    from plasma_column.schema import SimulationCaseConfig
    from scripts.postprocess_stages import collect_case

    case = SimulationCaseConfig.from_dict({"case_name": "c1", "method": "seeded",
                                           "numerics": {"max_steps": 100}})
    assert collect_case(case, tmp_path)["status"] == "missing"
    _fake_run(tmp_path / "c1", 50)
    row = collect_case(case, tmp_path)
    assert row["status"] == "incomplete" and row["final_step"] == 50
    assert row["eta_net_global"] == (9 - 8) / 10
