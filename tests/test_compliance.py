"""Tests for the Phase-08.1 compliance self-checks."""

from __future__ import annotations

from mmm_os.governance import controls_matrix, verify_least_privilege


def test_least_privilege_holds() -> None:
    """The shipped RBAC matrix has no least-privilege violations."""
    assert verify_least_privilege() == []


def test_controls_matrix_covers_core_cross_cutting() -> None:
    """The controls matrix maps each control to an implementing phase."""
    controls = controls_matrix()
    ids = {c.control_id for c in controls}
    assert {"AC-1", "AC-2", "AU-1", "SC-1"} <= ids
    assert all(c.implemented_by for c in controls)
