"""Small authenticated Railway GraphQL client for deployment automation."""

import httpx
from dotenv import dotenv_values


def graphql(query: str, variables: dict | None = None) -> dict:
    values = {key.upper(): value for key, value in dotenv_values(".env").items()}
    response = httpx.post(
        "https://backboard.railway.com/graphql/v2",
        headers={"Authorization": "Bearer " + (values.get("RAILWAY_API_TOKEN") or "")},
        json={"query": query, "variables": variables or {}},
        timeout=60,
    )
    response.raise_for_status()
    result = response.json()
    if result.get("errors"):
        raise RuntimeError("; ".join(error["message"] for error in result["errors"]))
    return result["data"]
