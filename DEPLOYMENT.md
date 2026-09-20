# Live deployment

- Phone: **+1 (859) 689-8029** (Vapi status: active)
- API: https://patient-api-production-2f36.up.railway.app
- Docs: https://patient-api-production-2f36.up.railway.app/docs
- Health: https://patient-api-production-2f36.up.railway.app/health
- Railway project: https://railway.com/project/acea77ca-6b9e-4866-a0c1-0f8f3b25a4db
- Vapi assistant ID: `c7d70043-a8cd-4f65-97e3-e18dfe2823ab`
- Vapi phone resource ID: `29586033-0360-4e30-9659-21951db81756`

The dedicated Railway project contains `patient-api`, `Postgres`, and the persistent
`postgres-volume`. Production requires API authentication and uses the private
PostgreSQL connection. Both services deployed successfully. The API uses a Docker
build and runs Alembic before starting.

API and webhook secrets were generated and stored in local `.env` and Railway's API
service variables. Provider/deployment keys stay local and are excluded from the
upload. To use Swagger's Authorize button, enter the local `.env` value of `API_KEY`.
Do not publish this key. The Vapi server configuration has the matching webhook secret.

## Verified

- Remote CRUD smoke: all nine checks passed against PostgreSQL.
- `/docs`, OpenAPI and unauthenticated patient/webhook rejection.
- Production voice tools rejected missing/ambiguous confirmation and stale consent.
- Corrected, explicitly confirmed fake demographics were saved and retrieved via REST.
- The confirmed patient survived a successful Railway application redeployment.
- The verification patient was soft-deleted and its synthetic call closed afterward.
- Vapi accepted the assistant, all nine tools, and the production server configuration.
- The active U.S. number points to that assistant.

These are API/tool checks. They do not establish speech recognition quality or prove
that an inbound telephone conversation has been tested. Complete the manual scenarios
in TESTING.md with fictional information before submission. Vapi-managed free numbers
are intended for U.S. national inbound calls; see the provider's
[free number guide](https://docs.vapi.ai/free-telephony).

## Redeploy from this directory

The workspace token can perform Railway API operations, but the CLI's interactive
workspace discovery returned Unauthorized. A project/environment-scoped deployment
token was created and stored as `RAILWAY_TOKEN` in `.env`. The helper uses it without
putting secrets in command arguments. Direct deployment with explicit IDs works:

```sh
uv run python -m scripts.railway_cli up --project acea77ca-6b9e-4866-a0c1-0f8f3b25a4db --environment a4ee6d8f-b459-493e-b3e0-ce4fd5b70a2d --service 4430c02e-0136-4f3d-ba02-00c278ba8f9b --detach --json
uv run python -m scripts.smoke_test --base-url https://patient-api-production-2f36.up.railway.app
uv run python -m scripts.setup_vapi --apply
```

The last command updates the already-configured assistant and phone association.
`.railwayignore` excludes environment files, caches, logs and local databases.
`scripts.check_accounts` can inspect account resources without printing credentials.

The repository is not yet published; its submission URL remains to be supplied.

Latest verified API deployment ID: `d076f9eb-471c-4a0e-90e0-293500c4360c`.
The latest local regression run passed all 82 tests; lint passed as well.
Vapi v7 includes post-result completion guidance which distinguishes success from
application failure. Spoken timing remains a manual acceptance check.
Reviewer API key rotated September 21: old-key rejection and new-key access verified.
The replacement is in local .env; share privately. No provider keys were changed.
Production checks verified rejection of skipped/unanswered optional offers and
qualified consent, acceptance of "Yes. This is correct.", idempotent save, and
optional data persistence. The synthetic test record was soft-deleted; existing
active patient records were unchanged. A fresh spoken call is still needed to
evaluate speech and turn timing after these changes.

The returning-patient production regression loaded saved demographics using natural
edit permission and changed only a synthetic patient's last name. Patient ID,
creation timestamp and DOB were preserved. The test record was cleaned up and
existing active patient records were unchanged.

Loop recovery was verified in production: "Yes. I want to add my email" permits
loading, a corrected email persists after fresh confirmation, and invalid tokens
return the appropriate recovery step. Three rejected saves cancel the draft and
block further writes, returning an instruction to end the call. Physical hangup
still depends on Vapi following endCall. Existing patient records were unchanged.
