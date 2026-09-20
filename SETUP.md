# Setup and configuration

[Back to README](README.md) | [Try the demo](REVIEWER_GUIDE.md)

## Local setup

Install Python 3.12+ and [uv](https://docs.astral.sh/uv/getting-started/installation/).
Run commands from this directory. `uv` can install Python if necessary.

```sh
uv sync --frozen
```

Copy `.env.example` to `.env` (`Copy-Item .env.example .env` in PowerShell,
`cp .env.example .env` on macOS/Linux). Keep `.env` out of source control.
Generate two independent random secrets with the following command, run twice,
and paste them into `API_KEY` and `VAPI_WEBHOOK_SECRET` in `.env`:

```sh
uv run python -c "import secrets; print(secrets.token_urlsafe(32))"
uv run alembic upgrade head
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/docs` and use **Authorize** to enter `API_KEY`.
`GET /health` stays public. Local REST authentication is optional if API_KEY is
empty; webhook authentication is always required. The server never creates tables
implicitly. `uv run python -m scripts.start` runs migrations and starts on `PORT`.

### Environment variables

| Variable | Purpose |
| --- | --- |
| `APP_ENV` | `development` or `production`; production refuses SQLite and missing auth secrets |
| `DATABASE_URL` | Default `sqlite:///./patients.db`; deployed `postgresql://...` is converted to psycopg |
| `API_KEY` | `X-API-Key` for REST patient routes; required in production |
| `VAPI_WEBHOOK_SECRET` | Shared `X-Vapi-Secret` for webhook authentication |
| `VAPI_API_KEY` | Vapi private API key, used only by the setup script |
| `VAPI_ASSISTANT_ID` | Empty to create; set to update that specific assistant |
| `VAPI_PHONE_NUMBER_ID` | Existing Vapi phone resource to attach to the assistant |
| `PUBLIC_BASE_URL` | Actual deployed HTTPS origin used by setup and connectivity checks |
| `LLM_MODEL` | Vapi-supported OpenAI conversational model; default `gpt-4o-mini` |
| `VAPI_VOICE_ID` | Vapi voice; default `Elliot` |
| `LOG_LEVEL` | Default `INFO` |
| `LOG_PATIENT_PAYLOAD` | Default `true` for the assessment's fake-data payload logging |
| `PORT` | Startup port; Railway supplies it automatically |
| `RAILWAY_API_TOKEN` | Local deployment automation: workspace-scoped Railway access |
| `RAILWAY_TOKEN` | Local deployment automation: token restricted to this project's environment |

Model credentials/billing are managed in Vapi. This backend does not call the LLM
directly, so it does not take an unused `OPENAI_API_KEY`.

## Deploy your own instance

No cloud project is created automatically without account access. To deploy:

1. Publish this directory to your own Git repository without `.env`, databases or logs.
2. In Railway, create a **new project**. Add **Database → PostgreSQL**.
3. Add a service from your GitHub repository. Railway detects the Dockerfile.
4. In that API service's Variables, set `APP_ENV=production`,
   `DATABASE_URL=${{Postgres.DATABASE_URL}}` (adjust the service name if renamed),
   and independent strong values for `API_KEY` and `VAPI_WEBHOOK_SECRET`.
   Keep `LOG_PATIENT_PAYLOAD=true` only for fake assessment data. Do not put the
   Vapi private API key on the backend; the local setup script is its only consumer.
5. Deploy. Startup runs `alembic upgrade head`, then listens on Railway's `PORT`.
   Keep a single API replica for this assessment's startup-migration strategy.
6. Under **Settings → Networking → Public Networking**, generate a domain.
   Verify `https://YOUR_ACTUAL_DOMAIN/health` and `/docs`.
7. Put the actual HTTPS origin into local `.env` as `PUBLIC_BASE_URL`, and copy the
   same API/webhook secrets there. Run:
   `uv run python -m scripts.smoke_test --base-url https://YOUR_ACTUAL_DOMAIN`.
8. Configure Vapi below, then perform the manual phone scenarios in [TESTING.md](TESTING.md).

The PostgreSQL service owns persistent storage independently of API redeploys.
This follows Railway's [PostgreSQL/webhook deployment guide](https://docs.railway.com/guides/saas-backend).

## Vapi setup

1. Sign in to [Vapi](https://dashboard.vapi.ai). Enable the billing/credits required
   by your account for calls and model usage. Copy a **private API key** from API Keys
   into local `.env` as `VAPI_API_KEY`. Never paste it into a public repository.
2. Complete deployment above. Set `PUBLIC_BASE_URL` and `VAPI_WEBHOOK_SECRET` locally
   to match your reachable backend. Choose a model available to your Vapi account
   through `LLM_MODEL`; configure provider credentials in Vapi if the account requires them.
3. Preview the configuration without making provider changes:
   `uv run python -m scripts.setup_vapi`. The preview redacts the webhook secret.
4. Run `uv run python -m scripts.setup_vapi --apply`. It verifies `/health` and an
   authenticated webhook request, then creates the assistant. Copy its printed ID
   into `VAPI_ASSISTANT_ID` immediately. Future runs update that assistant.
5. In Vapi **Phone Numbers**, choose **Create Phone Number** and select a U.S. Vapi
   number if your account offers one, or import a U.S. number you own from a supported
   telephony provider. Account eligibility, available inventory and billing vary;
   this project does not invent or automatically purchase a number.
6. Copy the number resource's **ID** into `VAPI_PHONE_NUMBER_ID`. Run
   `uv run python -m scripts.setup_vapi --apply` again. This attaches that existing
   number to the configured assistant. Alternatively choose the assistant in the
   number's inbound-call configuration in the dashboard and save.
7. Inspect the saved assistant: prompt, model, voice, eight function tools plus
   `endCall`; server URL `PUBLIC_BASE_URL/voice/vapi`; header `X-Vapi-Secret`; server
   events `tool-calls`, `status-update`, `end-of-call-report`. Each function tool
   has the same authenticated server URL. Inline headers are supported; Vapi also
   offers dashboard Custom Credentials if you prefer credential references.
8. Dial the **actual number shown in the dashboard**. Register fictional data,
   correct a value, confirm it, and query `/patients?phone_number=...` with your API key.
   Verify real audio/turn-taking and interruptions using [TESTING.md](TESTING.md).
9. Fill the actual number, domain and repository URL in [SUBMISSION.md](SUBMISSION.md).

The setup script uses Vapi's [assistant API](https://docs.vapi.ai/api-reference/assistants/create),
[function-tool protocol](https://docs.vapi.ai/tools/custom-tools-troubleshooting),
[server authentication](https://docs.vapi.ai/server-url/server-authentication), and
[phone update API](https://docs.vapi.ai/api-reference/phone-numbers/update).
See the [official phone quickstart](https://docs.vapi.ai/assistants/quickstart) for account UI details.
The saved assistant configuration and phone association have been accepted by Vapi
and verified through its API. Actual inbound audio acceptance remains pending.
