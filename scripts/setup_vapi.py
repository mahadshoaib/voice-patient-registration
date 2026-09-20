"""Generate configuration by default; --apply creates/updates only specified resources."""

import argparse
import json
import sys

import httpx

from app.core.config import settings
from app.voice.configuration import assistant_configuration


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    config = assistant_configuration(settings)
    if not args.apply:
        # Dry-run output must never disclose the webhook secret.
        config["server"]["headers"]["X-Vapi-Secret"] = "<VAPI_WEBHOOK_SECRET>"
        print(json.dumps(config, indent=2))
        return
    if not all(
        (
            settings.vapi_api_key,
            settings.vapi_webhook_secret,
            settings.public_base_url.startswith("https://"),
        )
    ):
        sys.exit("Set VAPI_API_KEY, VAPI_WEBHOOK_SECRET and an HTTPS PUBLIC_BASE_URL first")
    with httpx.Client(timeout=30) as client:
        health = client.get(settings.public_base_url.rstrip("/") + "/health")
        health.raise_for_status()
        if health.json().get("data", {}).get("status") != "ok":
            sys.exit("Backend health check failed")
        # Exercise authenticated server connectivity before modifying Vapi resources.
        probe = client.post(
            config["server"]["url"],
            headers=config["server"]["headers"],
            json={"message": {"type": "connectivity-check", "call": {"id": "setup-connectivity"}}},
        )
        probe.raise_for_status()
        client.headers["Authorization"] = "Bearer " + settings.vapi_api_key
        assistant_id = settings.vapi_assistant_id
        response = (
            client.patch(f"https://api.vapi.ai/assistant/{assistant_id}", json=config)
            if assistant_id
            else client.post("https://api.vapi.ai/assistant", json=config)
        )
        response.raise_for_status()
        assistant_id = response.json()["id"]
        print(f"VAPI_ASSISTANT_ID={assistant_id}")
        if settings.vapi_phone_number_id:
            response = client.patch(
                f"https://api.vapi.ai/phone-number/{settings.vapi_phone_number_id}",
                json={"assistantId": assistant_id},
            )
            response.raise_for_status()
            print(
                "Attached existing phone resource:", response.json().get("number", "see dashboard")
            )
        else:
            print("Next: select/create a U.S. phone number in Vapi and set VAPI_PHONE_NUMBER_ID.")


if __name__ == "__main__":
    try:
        main()
    except httpx.HTTPError as exc:
        # Provider response bodies may echo configuration/secrets; do not print them.
        sys.exit(
            f"Vapi setup failed ({type(exc).__name__}); check account, IDs and dashboard logs."
        )
