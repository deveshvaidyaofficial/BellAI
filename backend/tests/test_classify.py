"""classify() normalization. Owner: Utkarsh."""

import pytest

from app.models import CallOutcome
from app.services.outcomes import classify


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("completed", CallOutcome.completed),
        (" Completed ", CallOutcome.completed),
        ("LATER", CallOutcome.later),
        (" needs_help ", CallOutcome.needs_help),
        ("NO_ANSWER", CallOutcome.no_answer),
    ],
)
def test_stored_codes_ignore_case_and_whitespace(raw, expected):
    assert classify("completed", raw) == expected


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("requested-later", CallOutcome.later),
        (" Requested-Later ", CallOutcome.later),
        ("help-needed", CallOutcome.needs_help),
        ("HELP-NEEDED", CallOutcome.needs_help),
        ("unresolved", CallOutcome.needs_help),
        (" Unresolved ", CallOutcome.needs_help),
        ("no-answer", CallOutcome.no_answer),
        ("failed-call", CallOutcome.no_answer),
        (" Failed-Call ", CallOutcome.no_answer),
    ],
)
def test_discussion_aliases_map_to_stored_codes(raw, expected):
    assert classify(None, raw) == expected


@pytest.mark.parametrize(
    "status",
    [
        "no-answer",
        " No-Answer ",
        "busy",
        "BUSY",
        "failed",
        " canceled ",
        "call-disconnected",
        "Call-Disconnected",
    ],
)
def test_provider_no_answer_statuses_ignore_case_and_whitespace(status):
    assert classify(status, None) == CallOutcome.no_answer
    assert classify(status, "  ") == CallOutcome.no_answer


def test_extracted_outcome_wins_over_provider_status():
    assert classify("no-answer", "completed") == CallOutcome.completed
    assert classify("completed", "failed-call") == CallOutcome.no_answer


def test_unknown_outcome_on_a_finished_call_still_needs_help():
    assert classify("completed", "maybe") == CallOutcome.needs_help
    assert classify(None, None) == CallOutcome.needs_help
    assert classify("in-progress", "something-else") == CallOutcome.needs_help


def test_blank_outcome_is_ignored():
    assert classify("failed", "") == CallOutcome.no_answer
    assert classify("   ", "   ") == CallOutcome.needs_help
