"""Request one Vapi-managed free U.S. number, keeping account secrets local."""

import argparse
import json
import sys

import httpx
from dotenv import dotenv_values, set_key

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--area-code", default="415")
    args = parser.parse_args()
    values = dotenv_values(".env")
    with httpx.Client(
        timeout=45,
        headers={
            "Authorization": "Bearer " + (values.get("VAPI_API_KEY") or ""),
        },
    ) as client:
        response = client.get("https://api.vapi.ai/phone-number")
        response.raise_for_status()
        numbers = response.json()
        if numbers:
            sys.exit(
                "Account already has phone resources; inspect before selecting or provisioning."
            )
        response = client.post(
            "https://api.vapi.ai/phone-number",
            json={
                "provider": "vapi",
                "numberDesiredAreaCode": args.area_code,
                "name": "Patient Registration Demo",
            },
        )
        print("Phone provisioning HTTP:", response.status_code)
        result = response.json()
        if response.is_success:
            set_key(".env", "VAPI_PHONE_NUMBER_ID", result["id"])
            print(
                json.dumps(
                    {key: result.get(key) for key in ("id", "number", "provider", "status")},
                    indent=2,
                )
            )
        else:
            print(
                json.dumps(
                    {key: result.get(key) for key in ("message", "error", "statusCode")}, indent=2
                )
            )
            sys.exit(1)
