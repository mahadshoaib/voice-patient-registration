# Voice AI Patient Registration

A conversational patient intake agent built with Vapi, FastAPI and PostgreSQL.
It collects validated demographics, reads them back for confirmation, and saves
them through the same service layer used by the REST API. Returning patients can
update their existing record. **Use fictional information only.**

## Try the demo

| Item | Access |
| --- | --- |
| Phone | **+1 (859) 689-8029** |
| API | https://patient-api-production-2f36.up.railway.app |
| Interactive API docs | https://patient-api-production-2f36.up.railway.app/docs |
| Credentials | Reviewer API key supplied privately; enter it in Swagger's **Authorize** dialog |
| Repository | [mahadshoaib/voice-patient-registration](https://github.com/mahadshoaib/voice-patient-registration) |

Call the number from a supported U.S. calling route, provide fictional details,
and confirm the read-back. Query `GET /patients` using your fictional phone number
to see the saved record. Call again with the same phone to request an update.
For browser calls, Vapi workspace access is required; there is no public browser
widget. See the [reviewer guide](REVIEWER_GUIDE.md) for both calling methods.

**Verified:** browser voice registration and returning-patient updates, API retrieval,
PostgreSQL persistence, **82 automated tests**, and clean lint.
**Not yet verified:** a real inbound telephone conversation. The tester did not
have a supported international calling route available. The latest post-save
completion guidance also needs a fresh spoken check. See [testing evidence](TESTING.md).

## Run locally

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).
Copy `.env.example` to `.env`; use SQLite defaults for local API testing.
Set independent random `API_KEY` and `VAPI_WEBHOOK_SECRET` values.

```sh
uv sync --frozen
uv run python -m scripts.start
```

Open http://localhost:8000/docs. Startup applies migrations before serving.
Local startup runs the backend; voice calls additionally require a configured Vapi
assistant and a reachable HTTPS backend. [Full setup and environment variables](SETUP.md).

## Design

`Phone/browser -> Vapi -> authenticated FastAPI webhook -> patient service -> PostgreSQL`

Vapi supplies speech and conversational orchestration; FastAPI/Pydantic provide
shared validation; PostgreSQL provides durable transactions. SQLite keeps local
setup simple. Alembic manages schema changes. Patient records are separate from
unfinished call drafts; corrections invalidate consent, and saves return success
only after commit. [Architecture and trade-offs](ARCHITECTURE.md).

The [system prompt](app/voice/prompts/patient_registration_system.md) is included
with sections explaining extraction, corrections, optional information, returning
patients, consent and recovery. [Tool/model configuration](app/voice/configuration.py)
and a [redacted configuration preview](AGENT_CONFIGURATION.preview.json) are included.

## Scope and limitations

- All 19 required model fields, five CRUD operations, three search filters and soft deletion.
- Duplicate detection and automated tests are implemented bonuses.
- Caller consent and speech interpretation rely on the model; phone matching is not identity verification.
- One active record per phone; shared household numbers are not supported by this duplicate policy.
- English conversation only. No scheduling, patient dashboard or patient-linked transcript storage.
- This is an assessment demo, not a production healthcare or HIPAA-compliant system.

## Documentation

| Document | Purpose |
| --- | --- |
| [Reviewer guide](REVIEWER_GUIDE.md) | Phone/browser calls, credentials and a short test scenario |
| [Setup](SETUP.md) | Environment variables, local startup, deployment and Vapi provisioning |
| [Architecture](ARCHITECTURE.md) | Structure, design decisions, safeguards and limitations |
| [API](API.md) | Endpoints, authentication, examples and response formats |
| [Testing](TESTING.md) | Executed checks, evidence and pending voice scenarios |
| [Submission](SUBMISSION.md) | The four requested handoff items |
| [Requirements](REQUIREMENTS.md) | Five functional requirements, evaluation coverage and completed bonuses |

Run checks with `uv run pytest -q` and `uv run ruff check app scripts tests alembic`.
Next priorities: real telephone acceptance, spoken completion quality, then identity
verification, draft retention and pagination for any production-oriented extension.
