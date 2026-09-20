"""Read-only deployment access check; prints resource summaries, never credentials."""

import json

import httpx
from dotenv import dotenv_values


def main():
    values = {key.upper(): value for key, value in dotenv_values(".env").items()}
    with httpx.Client(timeout=30) as client:
        for name in ("RAILWAY_API_TOKEN", "VAPI_API_KEY"):
            print(f"{name}: {'configured' if values.get(name) else 'missing'}")
        if values.get("VAPI_API_KEY"):
            response = client.get(
                "https://api.vapi.ai/phone-number",
                headers={
                    "Authorization": "Bearer " + values["VAPI_API_KEY"],
                },
            )
            print("Vapi phone lookup HTTP:", response.status_code)
            if response.is_success:
                numbers = response.json()
                print(
                    json.dumps(
                        {
                            "phone_numbers": [
                                {
                                    key: item.get(key)
                                    for key in (
                                        "id",
                                        "number",
                                        "provider",
                                        "status",
                                        "assistantId",
                                        "name",
                                    )
                                }
                                for item in numbers
                            ]
                        },
                        indent=2,
                    )
                )
        if values.get("RAILWAY_API_TOKEN"):
            response = client.post(
                "https://backboard.railway.com/graphql/v2",
                headers={
                    "Authorization": "Bearer " + values["RAILWAY_API_TOKEN"],
                },
                json={"query": "query { projects { edges { node { id name } } } }"},
            )
            print("Railway project lookup HTTP:", response.status_code)
            if response.is_success:
                result = response.json()
                if result.get("errors"):
                    print(
                        "Railway errors:",
                        json.dumps([{"message": item.get("message")} for item in result["errors"]]),
                    )
                else:
                    print(json.dumps(result.get("data"), indent=2))


if __name__ == "__main__":
    main()
