"""On a restart the PIC driver runs only the steps left to max_steps (task 111)."""

from __future__ import annotations

import pytest


def test_checkpoint_step_from_name():
    from scripts.plasma_column_mcc_picmi_v7 import checkpoint_step

    assert checkpoint_step("results/x/chk034296") == 34296
    assert checkpoint_step("/abs/path/chk000000/") == 0


def test_checkpoint_step_rejects_other_names():
    from scripts.plasma_column_mcc_picmi_v7 import checkpoint_step

    with pytest.raises(ValueError):
        checkpoint_step("results/x/diag1034290")
