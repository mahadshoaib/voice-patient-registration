# Assessment requirements audit - updated September 21, 2026

This current assessment supersedes the historical audit below.

## Current verdict

Core data model, PostgreSQL persistence, CRUD API and voice integration are implemented.
Browser calls have now demonstrated new registration and returning-patient updates.
The latest reviewed calls are `01a0c01f-dc86-755c-a11c-229d5d284ba1` (create) and
`01a0c023-0dba-7774-bc41-9d2470f2b1e0` (email update to the same patient).
Both saved successfully and invoked endCall. ZIP 02108 retained its leading zero.
The failed email-edit loop was fixed and did not recur in the latest update.

## Current evidence by requirement

| PDF area | Current status |
| --- | --- |
| All 19 demographic fields | Implemented with shared validation and typed database columns; detailed field mapping below remains valid |
| Persistent database | Railway PostgreSQL and volume verified; prior restart checks and subsequent returning calls prove persistence |
| Five REST operations and three filters | Implemented/tested, server validation, data/error envelopes, proper HTTP codes and soft deletion |
| Voice integration | Shared service layer, full read-back, consent tokens, create/update and rollback tests |
| Optional fields | Transcript-checked offer; spoken opt-out and email opt-in demonstrated |
| Returning patient | Saved demographics load before changes; name/email updates demonstrated |
| Real U.S. number | +1 (859) 689-8029 active and correctly attached; inbound telephone acceptance still pending |
| Deployment/auth/logging | Health/docs 200, unauthenticated patients 401, authenticated list 200; four active patients; final payload logging enabled |
| Tests | 82 passed and clean lint; all field-group updates and nullable-field removal tested |
| Code/docs | Source, prompt, setup, architecture and limitations present; repository publication still pending |

Latest verified deployment: `d076f9eb-471c-4a0e-90e0-293500c4360c` (SUCCESS).
Live greeting and system prompt matched source at audit. The public repository target
is `mahadshoaib/voice-patient-registration`; do not represent it as published until verified.

## Remaining core and submission work

1. Final spoken completion: latest returning call said "I'm saving your registration
   now. Goodbye" without explicitly acknowledging save success. Earlier message order
   suggested premature success. A post-result completion hint is deployed in v7; actual
   audio timing still requires acceptance. Fillers/repetition remain quality risks.
2. Complete one real inbound telephone registration and second-call update. All
   successful reviewed calls are webCall. User currently lacks a supported calling
   route. Document this limitation and retain the working browser/local fallback.
3. Finish voice edge-case acceptance: invalid DOB/phone, interruption/correction,
   start-over, pre-consent hangup, optional removal, phone change and failed-write speech.
   Automated checks do not establish acoustic performance.
4. Publish source publicly to the agreed GitHub account, fill submission links, and
   exclude secrets, databases, local diagnostics and the confidential challenge PDF.
5. Reviewer API key rotation is done, with old-key rejection/new-key access verified.
   Privately share access and send the
   repository URL, phone, API URL and honest testing notes. No submission has been sent.
6. Confirm the PDF's three-hour deadline with the reviewer. Receipt time and deadline
   compliance cannot be established from this workspace.

Bonuses completed: duplicate detection and automated tests. Optional bonuses not
implemented: scheduling, Spanish switching, patient-linked transcript storage, dashboard.
Swagger is not a patient dashboard; Vapi artifacts do not satisfy linked DB storage.

The five equally weighted evaluation areas are working system, conversational quality,
architecture, code/docs and resilience. Architecture/backend evidence is strong;
telephone acceptance and spoken completion remain the principal review risks.
The assessors prioritize dependable end-to-end behavior and clear trade-offs over
extra features. HIPAA/production uptime are not required; use fictional data only.

Publication status: GitHub CLI installed locally, but not authenticated. Permission
prompts rejected git initialization and GitHub login. No repository was created or
published; do not interpret the proposed URL as a live repository.

Clarification: preferred_language defaults to English but is not nullable. Other
nullable optional fields may be removed; storing Spanish does not enable Spanish speech.

---

# Historical assessment (superseded where noted above)

Audit date: 2026-09-20.
Source: **Voice AI Agent Coding Challenge ..pdf**, all eight pages, including the
data model table, evaluation rubric, submission instructions and FAQs.

This is a review of the current implementation, not an instruction to add features
or submit the project. The original PDF is the assessment authority. The earlier
expanded implementation request added safeguards and tooling beyond its requirements.
No application behavior or cloud configuration was changed during this audit.

## Verdict

The demographic model, persistent database, REST API and backend registration tools
are implemented and tested. Deployment is live. **The submission is not yet fully
verified end to end:** there is no completed spoken registration in the available
Vapi call evidence, and the repository has not been published.

The priority is to prove a real call can complete registration, validate corrections,
persist a patient, and find/update that same record on a second call. Optional bonus
work should not delay that proof or publishing the source.

## Evidence checked

- Read the entire PDF and visually inspected its requirement/rubric pages.
- Inspected ORM model, migration, validators, schemas, REST routes, services,
  repositories, webhook parser, registration state machine and voice prompt/configuration.
- Re-ran `uv --cache-dir .uv-cache run pytest -q`: **49 passed**, with two upstream
  dependency deprecation warnings.
- Re-ran `uv --cache-dir .uv-cache run ruff check app scripts tests alembic`:
  **all checks passed**.
- Read-only live API check: health 200/ok, Swagger 200, OpenAPI contains all required
  routes, unauthenticated patient access 401, authenticated patient listing 200.
- Current active patient count: **0**. Previous verification records were intentionally
  soft-deleted; an empty active list is not evidence of data loss.
- Vapi assistant: `Patient Registration`, `gpt-4o-mini`, Vapi `Elliot`, Deepgram
  `nova-2` English; current greeting and system prompt match source; all nine tools present.
- Vapi number: **+1 (859) 689-8029**, active, attached to the correct assistant.
- Railway: production configuration, PostgreSQL reference, auth secrets configured,
  confirmed-payload logging enabled, and `postgres-volume` present.
- Latest API deployment: `e7878918-a201-4cfb-bdb6-ccc46b7974de`, **SUCCESS**.
- Earlier execution evidence in this conversation: all nine remote CRUD smoke checks
  passed; production webhook confirmation/correction checks passed; a fake patient
  survived an application redeployment and was subsequently soft-deleted. These were
  synthetic HTTP/tool tests, not a completed telephone conversation.

## Functional requirements: telephony and voice (PDF pp. 2-3)

| Requirement | Status | Evidence / remaining work |
| --- | --- | --- |
| Real dialable U.S. phone number | Provisioned; inbound acceptance pending | Active Vapi number is attached. The available logs contain no inbound telephone registration. Test from a supported calling route. |
| Natural conversational interaction | Implemented; subjective quality unverified | Professional greeting and concise coordinator prompt deployed. Hearing the greeting alone does not establish a natural complete intake. |
| LLM understands varied phrasing | Configured; live extraction unverified | GPT-4o-mini and extraction instructions are present. Unit tests feed structured fields; they do not test recognition of spoken language. |
| Clarification and corrections | Backend verified; spoken behavior pending | Field errors and replacement of captured data are tested, including invalid corrections and stale-token rejection. Test spoken name spelling and ambiguous dates. |
| Read back all data before saving | Implemented and tool-tested | Backend generates full read-back, returns a token, and requires explicit confirmation text for save. Model must actually read it and accurately report caller consent. |
| Re-prompt invalid fields only | Implemented and tool-tested | Shared field validators preserve valid fields and return targeted errors. Verify spoken recovery from a three-digit phone and future DOB. |
| Success acknowledgment and graceful ending | Configured; complete-call verification pending | Prompt waits for save success and invokes endCall. No successful full audio registration in available evidence. |
| Optional information offered, not interrogated | Prompt implemented | Required fields precede a single optional offer. Verify both opt-out and opt-in in a call. |

### Actual call evidence at audit time

The recent-call query returned four calls for this assistant:

- Three **web calls**, all ended by the customer; two had no user turns and one had
  one user turn. No registration tool invocation was found in their available messages.
- One **outbound phone call** failed with
  `call.start.error-vapi-number-international`.

This demonstrates that the browser voice session can start and that international
outbound dialing was rejected. It does **not** prove that registration logic failed,
nor that the full voice-to-database path succeeded. The earlier incoming call attempt
from the user did not appear in Vapi's call logs at the time it was checked.

Vapi's free number has U.S. national/inbound restrictions. Confirm the reviewer's
calling route. If they must test through an unsupported international route, resolve
the number/provider limitation before review. A browser call is useful for debugging
but is not a substitute for the PDF's phone-number acceptance requirement.

## Patient demographic model (PDF p. 3)

All **19 listed fields** are present: nine required demographics, seven optional
demographics, and three generated fields. `deleted_at` is an additional field required
by the API's soft-delete requirement.

| Field | Current implementation | Finding |
| --- | --- | --- |
| first_name | Required; 1-50 letters, hyphens/apostrophes | Matches |
| last_name | Required; same validation, indexed | Matches |
| date_of_birth | Required SQL DATE; accepts MM/DD/YYYY and ISO; rejects impossible/future dates | Matches input requirement; JSON output is ISO |
| sex | Required four-value Literal; database CHECK for Male, Female, Other, Decline to Answer | Matches; enum semantics implemented using VARCHAR plus CHECK |
| phone_number | Required; normalized to ten digits; accepts formatting, +1 and individual spoken digits | Format validation implemented; no ownership/geographic assignment lookup |
| email | Optional validated EmailStr | Matches |
| address_line_1 | Required nonblank street-address text | Matches; no external address verification required by PDF |
| address_line_2 | Optional nonblank apartment/unit text, nullable | Matches |
| city | Required, 1-100 characters | Matches |
| state | Required actual state/territory code, normalized uppercase | Matches; also permits territories |
| zip_code | Required five digits or ZIP+4 | Matches |
| insurance_provider | Optional company-name text | Matches |
| insurance_member_id | Optional alphanumeric identifier | Matches |
| preferred_language | Optional, defaults to English when omitted | Matches; storing a preference does not mean multilingual speech is implemented |
| emergency_contact_name | Optional name text, spaces supported | Matches |
| emergency_contact_phone | Optional, same phone normalization/validation | Matches at format level |
| created_at | Automatic UTC timestamp through ORM | Matches |
| updated_at | Automatic UTC timestamp on modification | Matches |
| patient_id | Automatic UUID primary key | Matches |
| deleted_at | Nullable UTC soft-delete timestamp | Matches additional DELETE requirement |

Nuance: phone validation is structural NANP validation, not proof a number belongs to
the U.S. or is assigned. The PDF does not require a lookup service. Database constraints
cover requiredness, selected lengths, sex options, primary key and active-phone uniqueness;
more detailed email/date/state/name rules are enforced in the shared application layer.

## Database (PDF p. 4)

| Requirement | Finding |
| --- | --- |
| Persistent database engine | PostgreSQL deployed on Railway; SQLite file fallback locally. PDF allows either. |
| Data survives restarts | Verified previously with real local process restarts and a Railway API redeployment. |
| Types and constraints | UUID, DATE, timezone-aware timestamp handling, length/enum constraints and indexes; Alembic migration present. |
| Optional seed records | No dedicated seed script or permanent demo patients. Not required; smoke test creates temporary fake records and soft-deletes them. |

The reviewer still needs the second-call experience exercised: technical persistence
has been established, but returning via the phone has not.

## Web service (PDF p. 4)

| Requirement | Finding |
| --- | --- |
| GET /patients | Implemented/tested; active records only; last_name, date_of_birth and phone_number filters supported. |
| GET /patients/:id | Implemented/tested; UUID validation; 404 for missing/deleted records. |
| POST /patients | Implemented/tested; 201 with generated UUID and complete patient object. |
| PUT /patients/:id | Implemented/tested; partial updates; validates changed and merged data. |
| DELETE /patients/:id | Implemented/tested; sets deleted_at; physical row retention verified. |
| Appropriate status codes | 200/201/404/422/500 implemented; application 400 handling exists; 401/409 added for auth/conflict. Not every endpoint needs to emit every listed code. |
| Server-side validation | Shared Pydantic validators, independent of LLM; tested invalid/missing input. |
| Consistent JSON envelope | REST returns data/error envelopes, including validation and server errors. |

Vapi's webhook uses its required `results` protocol instead of the REST envelope.
That is a provider-integration detail, not a failure of the patient REST requirements.
The partial-update OpenAPI body is a generic object rather than a fully enumerated
update schema; runtime validation is present. Improving its docs is optional polish.

## Voice agent and database integration (PDF p. 4)

| Requirement | Finding |
| --- | --- |
| Shared persistence path | Voice tools and REST invoke PatientService/PatientRepository. Matches the permitted service-layer alternative to REST calls. |
| Save only after confirmation | Current-draft token plus explicit phrase required; invalid/missing/ambiguous/stale confirmation tested. |
| Relay successful write | Result returned only after transaction commit; prompt announces success afterward. Synthetic production save verified. |
| Relay failed write gracefully | Commit failure/rollback tests pass; tool returns safe failure; prompt supplies spoken error. Actual audio during an outage still unverified. |
| Duplicate recognition/update offer | Implemented and automated-tested; consent selects existing record, fresh confirmation required for update. |

Consent is interpreted by the model and reported to the backend. The backend cannot
independently prove the caller heard the read-back or spoke those words. This is a
documented trust boundary, not a claim of independently verified audio consent.

## Non-functional requirements (PDF p. 5)

| Area | Status | Remaining work |
| --- | --- | --- |
| Deployment | Live API and active phone | Complete a supported inbound call; keep Railway/Vapi accounts funded and services available through review. |
| Code quality | Clear layers, type hints, tests, lint passes | Explain design choices during review; no blocking structural issue identified. |
| README | Required setup, architecture, choices, variables and limitations present | Add repository URL once published. Update dated deployment metadata where necessary. |
| Security | Env-based keys, API/webhook auth, ORM queries and validation | Rotate reviewer API_KEY before handoff because it has appeared in IDE-selected chat context; share replacement privately. No rotation performed during this audit. |
| Observability | Structured call/tool/error logs and final confirmed payload logging | Production LOG_PATIENT_PAYLOAD=true confirmed. Full transcript database storage is a separate optional bonus. |

The PDF explicitly does not require HIPAA compliance or 99.99% uptime. It explicitly
says not to store real patient data. Keeping that notice in reviewer documentation
is appropriate even though the spoken greeting now sounds professional.

## Evaluation criteria: five equal 20% categories (PDF pp. 5-6)

| Category | Our evidence | Main outstanding risk |
| --- | --- | --- |
| Working System - 20% | Live backend, persistence, CRUD and synthetic voice integration | No completed real inbound registration followed by an API lookup/second call |
| Conversational Quality - 20% | Professional prompt/greeting, corrections/read-back instructions | Naturalness, spelling, interruptions and out-of-order speech not demonstrated across a complete call |
| Technical Architecture - 20% | Shared validation/service/repository; proper types, migrations, separated provider logic | Documented application-vs-database constraint and consent trust boundaries |
| Code Quality & Documentation - 20% | 49 tests, clean lint, README/architecture/testing docs, included prompt | Missing published source and repository URL; small metadata cleanup |
| Edge Cases & Resilience - 20% | Tests for invalid input, start-over, dropped events, failed commits and retries | Actual spoken recovery and provider failure behavior need call acceptance |

These are evidence assessments, not invented reviewer scores. The first two categories
remain particularly exposed until phone registration is demonstrated end to end.

## Bonus challenges (PDF p. 6)

| Bonus | Status |
| --- | --- |
| Duplicate detection | Implemented; automated tests pass; complete spoken duplicate update still needs testing |
| Appointment scheduling | Not implemented |
| Spanish / multilingual switching | Not implemented; English STT is configured |
| Linked call transcript/summary storage | Not implemented in our database; Vapi's own artifacts and final payload logs do not satisfy this linked-storage bonus |
| Patient dashboard | Not implemented; Swagger is API documentation, not a patient dashboard |
| Automated API tests | Implemented; current total 49 tests |

Two of six bonus categories are implemented. The PDF says bonuses are not required
and do not affect the core score. The recommended technologies are suggestions only;
our Vapi/FastAPI/PostgreSQL/Railway choices are acceptable.

## Submission instructions (PDF p. 7)

| Instruction | Status |
| --- | --- |
| Public/private GitHub or GitLab repository | Missing: this working directory is not a Git repository; no published URL supplied. |
| Grant reviewer access if private | Pending repository publication and reviewer email details. |
| Live phone and API, both in README | Both listed and deployed; phone registration acceptance remains pending. |
| Submit within three hours of receiving challenge | Cannot verify the official receipt time/deadline from the files. Confirm with the reviewer; do not claim compliance. |
| Send repository URL | Missing; SUBMISSION.md still contains <REPOSITORY_URL>. |
| Send phone number | Ready: +1 (859) 689-8029, with accurate routing/testing notes. |
| Send API base URL | Ready: https://patient-api-production-2f36.up.railway.app |
| Send needed credentials/testing notes | Documented API-key authentication; share reviewer API key privately, not provider/deployment credentials. |

`DEPLOYMENT.md` currently names an older successful deployment as its latest verified
ID. The current successful ID is recorded in the evidence section above. That is a
small documentation correction, not a runtime blocker. This audit did not rewrite
the submission documents or submit anything on the user's behalf.

## What the assessors are looking for (PDF pp. 7-8)

They want practical integration under time pressure, sensible trade-offs, a complete
working flow, a good caller experience, and clear explanations in code/docs. They
prefer a simple dependable system to extra features that fail during a call. They
allow voice platforms and AI coding tools; they expect the candidate to understand
and explain the result. Vendor blockers should be documented with a usable fallback.

The strongest next investment is call acceptance, not appointment scheduling or a
dashboard. A good backend does not compensate for an unusable voice experience.

## Remaining work in priority order

1. **Complete a spoken registration.** First use the browser assistant to exercise
   every required field, optional opt-out, correction, full read-back and explicit yes.
   Confirm a successful save tool and retrieve the patient via the API.
2. **Complete a real inbound telephone call.** Use a supported calling route. Confirm
   the reviewer can reach it; resolve any international restriction if their route
   requires it. Repeat with the same phone and confirm duplicate update/persistence.
3. **Exercise voice edge cases.** Future DOB, short phone, corrected surname, interrupted
   read-back, start-over, ambiguous consent, dropped call, optional data and graceful
   failure. Record outcomes; avoid claiming acoustic behavior based only on unit tests.
4. **Publish source.** Initialize Git, check exclusions, publish to GitHub/GitLab, add
   the real URL, and grant access if private. Do not include .env, databases, caches,
   logs or the confidential challenge PDF in the repository.
5. **Prepare reviewer access.** Rotate the exposed API key and update the deployed
   secret/local file, share it privately, verify the submission deadline, and send
   repository URL, phone, API origin and test notes.
6. **Small documentation polish.** Update latest deployment metadata and record the
   final phone test result. More detailed partial-update OpenAPI docs are optional.

No additional bonus feature is necessary to satisfy the PDF's core requirements.
