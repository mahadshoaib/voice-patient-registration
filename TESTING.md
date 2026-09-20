# Testing

**Use fictional data only.** Local automated tests do not place telephone calls.

## Browser voice evidence

Actual microphone calls in Vapi's dashboard completed new registration and
returning-patient updates. Transcripts/tool results were compared with REST records.
Latest reviewed successful examples (September 20, 2026 UTC):

- 18:41: new registration, optional opt-out, full read-back, explicit consent and save.
- 18:45: lookup, edit permission, saved-demographic load, email addition, read-back,
  consent and update of the same UUID. The earlier email-update loop did not recur.

These were webCall sessions, not inboundPhoneCall sessions. A supported international
calling route was unavailable. Neither browser calls nor unit tests verify carrier
routing. Fillers/repetition and post-save acknowledgment remained quality findings;
Vapi v7's completion hint needs a new spoken acceptance test.

## Recorded local verification

The following commands were actually executed during implementation (Python 3.12.12,
Windows; SQLite). `--cache-dir` keeps uv's cache within this workspace.

| Exact command | Actual outcome |
| --- | --- |
| `uv --cache-dir .uv-cache run pytest -q` | 82 passed; two upstream dependency deprecation warnings |
| `uv --cache-dir .uv-cache run ruff check app scripts tests alembic` | All checks passed |
| `uv --cache-dir .uv-cache run ruff format --check app scripts tests alembic` | 43 files already formatted |
| `uv --cache-dir .uv-cache run python -m scripts.verify_restart` | All 16 checks passed, including empty migration, no schema drift, process restart and physical row retention |
| `uv --cache-dir .uv-cache run python -m scripts.smoke_test --base-url http://127.0.0.1:8000` | All 9 live HTTP checks passed |

The local server was started with `uv --cache-dir .uv-cache run python -m scripts.start`.
Subsequently, the Railway deployment and PostgreSQL runtime passed all nine remote
smoke checks. Production webhook checks also verified authentication, missing/ambiguous
confirmation rejection, invalidation after correction, and a confirmed PostgreSQL save.
The Vapi assistant's saved webhook configuration and its active phone attachment were
verified through Vapi's API. No real telephone conversation is claimed as verified.
The confirmed fake patient also survived a successful Railway application redeployment;
it was then soft-deleted and the synthetic call was closed.

## Automated commands

```sh
uv sync --frozen
uv run pytest -q
uv run ruff check app scripts tests alembic
uv run ruff format --check app scripts tests alembic
uv run python -m scripts.verify_restart
```

Tests cover REST CRUD, all validation cases, filters, normalized duplicate detection,
soft-delete row retention, timestamps, unknown UUIDs, response envelopes, API/webhook
authentication, provider batch parsing, voice corrections, invalid corrections,
required-field refusal, restart, dropped calls, stale tokens, explicit confirmation,
duplicate updates, retry idempotency and failed database commits.

`verify_restart` migrates a fresh temporary database, checks migration drift, starts
a real HTTP server, creates a patient, terminates/restarts the process, retrieves the
same record, runs the CRUD smoke script and checks retained soft-deleted rows via SQL.
Its temporary database is removed after successful verification. Server output is in
`.local/restart-server.log`, excluded from source control.

With your regular server running:

```sh
uv run python -m scripts.smoke_test --base-url http://127.0.0.1:8000
```

Run against the actual public HTTPS URL after deployment. Load the matching API_KEY
from `.env`. The script cleans up only records it creates, using soft deletion.

## Manual voice acceptance

First follow [SETUP.md](SETUP.md) and the [reviewer guide](REVIEWER_GUIDE.md). Before each scenario,
note active records for the fictional phone; afterward inspect Vapi tool logs and
query the API with X-API-Key. Use `415-555-0182` for the main fake patient; use another
555-0100–0199 number when a new registration must not trigger duplicate handling.

Base data: Jane Demo, June 14 1993, Female, 415-555-0182, 123 Fictional Street,
San Francisco, CA 94105. No real patient data.

| Scenario | Say / do | Expected behavior |
| --- | --- | --- |
| Happy path | Provide base data; decline optional information; answer “yes” after full read-back | One patient created only after confirmation; success spoken after backend success |
| Out of order | “I'm Sarah Connor, born May 12th 1988, and my number is 415-555-0123” | Captures both names, DOB and phone in one tool call; asks for remaining fields |
| Spelling correction | “Actually, my last name is Davis, D-A-V-I-S” | Replaces last name; read-back/API show Davis |
| Future DOB | “January first, 2999” | Re-prompts only DOB, keeps other valid fields; no create |
| Impossible/ambiguous date | “February thirtieth, 2000”; then an unclear date | Rejects impossible date and clarifies uncertainty instead of guessing |
| Incomplete phone | “One two three” | Requests full 10-digit phone number |
| Spoken phone | “Four one five, dash, five five five, dash, zero one eight two” | Captures and normalizes 4155550182 |
| State / ZIP / email | “ZZ”, “1234”, “not an email” | Specific correction for each invalid field; does not discard other valid data |
| Confirmation correction | During read-back: “The address is wrong; it's 456 Fictional Avenue” | Invalidates old consent token, corrects address, reads back again, waits for a new yes |
| Ambiguous confirmation | “Maybe” or “Yes, but the phone is wrong” | Asks for clarification/correction; no save |
| Start over | After several values: “I want to start again” | Clears all collected values, errors and selected duplicate; restarts with name |
| Duplicate accepted | Call again with a previously saved phone; agree to update | Retrieves draft for the existing patient; corrected record keeps same UUID; fresh confirmation required |
| Duplicate declined | Decline update | Existing record unchanged; asks for another phone or ends |
| Optional declined | “No thanks” when optional fields offered | Does not ask a checklist; English default; reads back required fields |
| Optional supplied | Give email, unit, insurance/member ID, emergency contact and language | Includes all supplied values in read-back and persisted patient |
| Required refused | Decline DOB twice | Explains once, asks again, then ends without creating a patient |
| Sex privacy | “Decline to answer” for sex | Accepts the supported enum; does not treat it as incomplete registration |
| Interruption | Interrupt mid-question/read-back with a correction | Lets caller finish; captures correction and restarts read-back before consent |
| Dropped call | Hang up before giving final yes | No patient created; end event clears and closes the draft |
| Save failure | Use automated failure injection below or stop a dedicated test database | Never announces success; says save was not confirmed, logs failure |
| Second call | Call again after a completed registration | New isolated call draft; phone duplicate policy still applies |

## Save failure injection

```sh
uv run pytest -q tests/test_voice_tools.py -k write_failure
uv run pytest -q tests/test_patients_api.py -k database_failure
```

The voice test raises an OperationalError at commit, after mutation was attempted,
asserts failure instead of success, verifies rollback left zero patient rows, then
restores the database and retries successfully. Do not add a public fail-write flag.
For manual audio failure testing, use an isolated demo deployment and temporarily
stop its database before final consent. Restore it immediately after the scenario.

## Verification boundaries

Tool tests verify structured multi-field extraction *inputs* and conversation state,
not the speech model's recognition quality. Real audio and interruptions still
need inbound-call acceptance. Public webhook reachability, PostgreSQL runtime and
provider configuration acceptance are now verified. Dependency warnings may appear from
Starlette's current httpx compatibility layer; they do not indicate failed tests.
