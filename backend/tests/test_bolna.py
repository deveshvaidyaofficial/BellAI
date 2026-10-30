"""Unit tests for the Bolna outbound client. Owner: Devesh."""

import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.config import Settings
from app.models import Elder, Task, TaskType
from app.services import bolna
from app.services.bolna import BolnaError, build_user_data, trigger_call


@pytest.fixture
def test_elder():
    return Elder(
        id=1,
        name="Asha Sharma",
        phone="+919876543210",
        language="hi",
        timezone="Asia/Kolkata",
    )


@pytest.fixture
def test_task():
    return Task(
        id=42,
        elder_id=1,
        type=TaskType.medication,
        title="Take Blood Pressure Tablet",
        details="After breakfast with warm water",
    )


def test_mock_mode_returns_mock_id_without_network_request(test_elder, test_task):
    mock_settings = Settings(
        bolna_mock=True,
        bolna_agent_id="c8fcf1f9-a513-4bff-83fc-2cb627bf6b1c",
        bolna_api_key="mock-key",
    )
    with patch("app.services.bolna.get_settings", return_value=mock_settings), \
         patch("httpx.post") as mock_post:
        call_id = trigger_call(test_elder, test_task)
        assert call_id.startswith("mock-")
        mock_post.assert_not_called()


def test_build_user_data_contains_expected_fields(test_elder, test_task):
    data = build_user_data(test_elder, test_task)
    assert data == {
        "elder_name": "Asha Sharma",
        "user_name": "Asha Sharma",
        "name": "Asha Sharma",
        "language": "hi",
        "task_type": "medication",
        "task_title": "Take Blood Pressure Tablet",
        "task_details": "After breakfast with warm water",
        "task_id": 42,
    }


def test_live_mode_sends_correct_payload_and_parses_execution_id(test_elder, test_task):
    live_settings = Settings(
        bolna_mock=False,
        bolna_agent_id="c8fcf1f9-a513-4bff-83fc-2cb627bf6b1c",
        bolna_api_key="secret-api-key",
        bolna_base_url="https://api.bolna.ai",
        bolna_from_phone_number="+18005550199",
        bolna_timeout_seconds=15,
    )
    mock_response = httpx.Response(
        200,
        json={"message": "done", "status": "queued", "execution_id": "exec-abc-123"},
        request=httpx.Request("POST", "https://api.bolna.ai/call"),
    )

    with patch("app.services.bolna.get_settings", return_value=live_settings), \
         patch("httpx.post", return_value=mock_response) as mock_post:
        call_id = trigger_call(test_elder, test_task)
        assert call_id == "exec-abc-123"

        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        assert kwargs["timeout"] == 15
        assert kwargs["headers"]["Authorization"] == "Bearer secret-api-key"
        payload = kwargs["json"]
        assert payload["agent_id"] == "c8fcf1f9-a513-4bff-83fc-2cb627bf6b1c"
        assert payload["recipient_phone_number"] == "+919876543210"
        assert payload["from_phone_number"] == "+18005550199"
        assert payload["user_data"]["elder_name"] == "Asha Sharma"
        assert payload["user_data"]["language"] == "hi"


def test_live_mode_omits_from_phone_number_when_empty(test_elder, test_task):
    live_settings = Settings(
        bolna_mock=False,
        bolna_agent_id="c8fcf1f9-a513-4bff-83fc-2cb627bf6b1c",
        bolna_api_key="secret-api-key",
        bolna_from_phone_number="",
    )
    mock_response = httpx.Response(
        200,
        json={"execution_id": "exec-999"},
        request=httpx.Request("POST", "https://api.bolna.ai/call"),
    )

    with patch("app.services.bolna.get_settings", return_value=live_settings), \
         patch("httpx.post", return_value=mock_response) as mock_post:
        call_id = trigger_call(test_elder, test_task)
        assert call_id == "exec-999"
        _, kwargs = mock_post.call_args
        assert "from_phone_number" not in kwargs["json"]


def test_alternative_id_fields_accepted(test_elder, test_task):
    live_settings = Settings(
        bolna_mock=False,
        bolna_agent_id="c8fcf1f9-a513-4bff-83fc-2cb627bf6b1c",
        bolna_api_key="secret-api-key",
    )
    for field_name in ["call_id", "id"]:
        mock_response = httpx.Response(
            200,
            json={field_name: f"call-{field_name}-123"},
            request=httpx.Request("POST", "https://api.bolna.ai/call"),
        )
        with patch("app.services.bolna.get_settings", return_value=live_settings), \
             patch("httpx.post", return_value=mock_response):
            call_id = trigger_call(test_elder, test_task)
            assert call_id == f"call-{field_name}-123"


def test_missing_api_key_raises_clear_error(test_elder, test_task):
    settings = Settings(
        bolna_mock=False,
        bolna_agent_id="c8fcf1f9-a513-4bff-83fc-2cb627bf6b1c",
        bolna_api_key="",
    )
    with patch("app.services.bolna.get_settings", return_value=settings):
        with pytest.raises(BolnaError, match="API key is not configured"):
            trigger_call(test_elder, test_task)


def test_missing_agent_id_raises_clear_error(test_elder, test_task):
    settings = Settings(
        bolna_mock=False,
        bolna_agent_id="",
        bolna_api_key="some-key",
    )
    with patch("app.services.bolna.get_settings", return_value=settings):
        with pytest.raises(BolnaError, match="agent ID is not configured"):
            trigger_call(test_elder, test_task)


def test_invalid_recipient_phone_raises_bolna_error(test_task):
    bad_elder = Elder(id=1, name="Asha", phone="not-a-number")
    settings = Settings(
        bolna_mock=False,
        bolna_agent_id="c8fcf1f9-a513-4bff-83fc-2cb627bf6b1c",
        bolna_api_key="key",
    )
    with patch("app.services.bolna.get_settings", return_value=settings):
        with pytest.raises(BolnaError, match="Invalid recipient phone"):
            trigger_call(bad_elder, test_task)


def test_http_4xx_error_handled_cleanly_without_secret_leakage(test_elder, test_task):
    settings = Settings(
        bolna_mock=False,
        bolna_agent_id="c8fcf1f9-a513-4bff-83fc-2cb627bf6b1c",
        bolna_api_key="super-secret-key-12345",
    )
    mock_response = httpx.Response(
        401,
        content=b'{"error": "Unauthorized"}',
        request=httpx.Request(
            "POST",
            "https://api.bolna.ai/call",
            headers={"Authorization": "Bearer super-secret-key-12345"},
        ),
    )
    with patch("app.services.bolna.get_settings", return_value=settings), \
         patch("httpx.post", return_value=mock_response):
        with pytest.raises(BolnaError) as exc_info:
            trigger_call(test_elder, test_task)
        assert "401" in str(exc_info.value)
        assert "super-secret-key-12345" not in str(exc_info.value)


def test_http_5xx_error_handled_cleanly(test_elder, test_task):
    settings = Settings(
        bolna_mock=False,
        bolna_agent_id="c8fcf1f9-a513-4bff-83fc-2cb627bf6b1c",
        bolna_api_key="key",
    )
    mock_response = httpx.Response(
        500,
        content=b'Internal Server Error',
        request=httpx.Request("POST", "https://api.bolna.ai/call"),
    )
    with patch("app.services.bolna.get_settings", return_value=settings), \
         patch("httpx.post", return_value=mock_response):
        with pytest.raises(BolnaError, match="status 500"):
            trigger_call(test_elder, test_task)


def test_timeout_handled_safely(test_elder, test_task):
    settings = Settings(
        bolna_mock=False,
        bolna_agent_id="c8fcf1f9-a513-4bff-83fc-2cb627bf6b1c",
        bolna_api_key="key",
    )
    with patch("app.services.bolna.get_settings", return_value=settings), \
         patch("httpx.post", side_effect=httpx.TimeoutException("timed out")):
        with pytest.raises(BolnaError, match="timed out"):
            trigger_call(test_elder, test_task)


def test_connection_error_handled_safely(test_elder, test_task):
    settings = Settings(
        bolna_mock=False,
        bolna_agent_id="c8fcf1f9-a513-4bff-83fc-2cb627bf6b1c",
        bolna_api_key="key",
    )
    with patch("app.services.bolna.get_settings", return_value=settings), \
         patch("httpx.post", side_effect=httpx.ConnectError("Connection refused")):
        with pytest.raises(BolnaError, match="Failed to connect to Bolna API"):
            trigger_call(test_elder, test_task)


def test_invalid_json_response_handled_safely(test_elder, test_task):
    settings = Settings(
        bolna_mock=False,
        bolna_agent_id="c8fcf1f9-a513-4bff-83fc-2cb627bf6b1c",
        bolna_api_key="key",
    )
    mock_response = httpx.Response(
        200,
        content=b'<html>Not JSON</html>',
        request=httpx.Request("POST", "https://api.bolna.ai/call"),
    )
    with patch("app.services.bolna.get_settings", return_value=settings), \
         patch("httpx.post", return_value=mock_response):
        with pytest.raises(BolnaError, match="Invalid JSON"):
            trigger_call(test_elder, test_task)


@pytest.mark.parametrize("bad_body", [
    [],
    "just a string",
    12345,
    None,
])
def test_non_dictionary_json_response_handled_safely(test_elder, test_task, bad_body):
    settings = Settings(
        bolna_mock=False,
        bolna_agent_id="c8fcf1f9-a513-4bff-83fc-2cb627bf6b1c",
        bolna_api_key="key",
    )
    mock_response = httpx.Response(
        200,
        content=json.dumps(bad_body).encode("utf-8"),
        request=httpx.Request("POST", "https://api.bolna.ai/call"),
    )
    with patch("app.services.bolna.get_settings", return_value=settings), \
         patch("httpx.post", return_value=mock_response):
        with pytest.raises(BolnaError, match="Unexpected non-dictionary response"):
            trigger_call(test_elder, test_task)


@pytest.mark.parametrize("empty_payload", [
    {},
    {"execution_id": ""},
    {"execution_id": "   "},
    {"execution_id": None},
    {"other_field": "something"},
])
def test_missing_or_empty_execution_id_raises_bolna_error(test_elder, test_task, empty_payload):
    settings = Settings(
        bolna_mock=False,
        bolna_agent_id="c8fcf1f9-a513-4bff-83fc-2cb627bf6b1c",
        bolna_api_key="key",
    )
    mock_response = httpx.Response(
        200,
        json=empty_payload,
        request=httpx.Request("POST", "https://api.bolna.ai/call"),
    )
    with patch("app.services.bolna.get_settings", return_value=settings), \
         patch("httpx.post", return_value=mock_response):
        with pytest.raises(BolnaError, match="No valid call/execution ID"):
            trigger_call(test_elder, test_task)
