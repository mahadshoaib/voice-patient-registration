import json

from app.core.config import Settings
from app.voice.configuration import assistant_configuration


def test_config_has_matching_tools_prompt_and_authenticated_servers():
    config = assistant_configuration(
        Settings(
            _env_file=None, public_base_url="https://example.com", vapi_webhook_secret="test-secret"
        )
    )
    assert config["server"]["url"] == "https://example.com/voice/vapi"
    tools = config["model"]["tools"]
    functions = {t["function"]["name"]: t for t in tools if t["type"] == "function"}
    assert set(functions) == {
        "collect_fields",
        "start_over",
        "decline_required_field",
        "lookup_patient_by_phone",
        "accept_existing_update",
        "prepare_confirmation",
        "create_patient",
        "update_patient",
        "select_appointment_patient",
        "list_appointment_slots",
        "prepare_appointment",
        "book_appointment",
    }
    for definition in functions.values():
        assert definition["server"]["headers"]["X-Vapi-Secret"] == "test-secret"
        assert not definition["async"]
        start_message = definition["messages"][0]
        if definition["function"]["name"] in {"create_patient", "update_patient"}:
            assert start_message["content"] == "I'm saving your registration now."
            assert start_message["blocking"] is True
            completion = definition["messages"][1]
            assert completion["type"] == "request-complete"
            assert completion["role"] == "system"
            assert "success=false" in completion["content"]
        else:
            assert start_message["content"] == ""
    assert "end-of-call-report" in config["serverMessages"]
    assert "WAIT" in config["model"]["messages"][0]["content"]
    assert json.loads(json.dumps(config))["model"]["model"] == "gpt-4o-mini"


def test_batch_tool_results_match_ids_and_malformed_arguments(client):
    response = client.post(
        "/voice/vapi",
        headers={"X-Vapi-Secret": "test-webhook-secret"},
        json={
            "message": {
                "type": "tool-calls",
                "call": {"id": "batched-call"},
                "toolCallList": [
                    {"id": "bad", "function": {"name": "collect_fields", "arguments": "not JSON"}},
                    {
                        "id": "good",
                        "function": {
                            "name": "collect_fields",
                            "arguments": {
                                "patient_payload": {"first_name": "Demo", "last_name": "Example"},
                            },
                        },
                    },
                ],
            },
        },
    )
    assert response.status_code == 200
    results = response.json()["results"]
    assert [r["toolCallId"] for r in results] == ["bad", "good"]
    assert not json.loads(results[0]["result"])["success"]
    assert json.loads(results[1]["result"])["draft"]["first_name"] == "Demo"
