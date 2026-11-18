"""Regression case from the C-002@11 trace: ticket data must not override the order DB."""

import pytest

from lab9.trace_case import investigate

pytestmark = pytest.mark.student


def test_lab9_ticket_delay_cannot_override_order_fact():
    bad = investigate("seeded_regression", "C-002", 11)["trial"]
    good = investigate("fixed", "C-002", 11)["trial"]
    assert any(e["kind"] == "model_override" for e in bad["events"])
    assert bad["snapshot"]["refund_vnd"] == 20000
    assert not bad["lab8_pass"]
    assert not any(e["kind"] == "model_override" for e in good["events"])
    assert good["snapshot"]["refund_vnd"] == 0
    assert good["lab8_pass"]
