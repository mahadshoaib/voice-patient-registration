# Requirements and completed bonuses

[README](README.md) | [Testing evidence](TESTING.md) | [Architecture](ARCHITECTURE.md)

## Five functional requirements

| Requirement | Implementation and evidence | Remaining qualification |
| --- | --- | --- |
| 1. Telephony and voice agent | Active U.S. number, Vapi conversational LLM, corrections, optional offer, full read-back and explicit confirmation; browser calls completed registration and updates | Real inbound telephone acceptance and final post-save spoken completion remain pending |
| 2. Patient demographic data model | All 19 specified fields, UUID, UTC timestamps, date/enum/name/phone/email/state/ZIP validation; optional values and English default | Format validation does not prove phone ownership or address accuracy |
| 3. Persistent database | Railway PostgreSQL with persistent volume, SQLAlchemy models and Alembic migrations; restart/redeploy persistence verified | SQLite is the local development fallback |
| 4. REST web service | GET list with last_name/DOB/phone filters, GET by UUID, POST, partial PUT and soft DELETE; server validation, HTTP status codes and data/error envelopes | Reviewer API key required; shared demo authorization, no pagination |
| 5. Voice agent/database integration | Voice and REST share the patient service; validated drafts, confirmation tokens, atomic saves, error recovery and returning updates | Model interprets speech/consent; backend commits before reporting success, while spoken timing needs acceptance |

The demographic fields are first_name, last_name, date_of_birth, sex, phone_number,
email, address_line_1, address_line_2, city, state, zip_code, insurance_provider,
insurance_member_id, preferred_language, emergency_contact_name,
emergency_contact_phone, created_at, updated_at and patient_id.
An additional deleted_at implements soft deletion.

## Bonus challenges

| Bonus | Status |
| --- | --- |
| Duplicate detection | Completed: phone lookup, permission-based record loading, edits and fresh confirmation; demonstrated in browser calls |
| Automated tests | Completed: 82 passing tests covering API, validation, voice tools, failure handling and every demographic update group |
| Appointment scheduling | Not implemented; optional |
| Multilingual conversation | Not implemented; preferred_language stores a preference but does not change English speech |
| Patient-linked transcript/summary storage | Not implemented in our database; Vapi call artifacts are not claimed as this bonus |
| Patient dashboard | Not implemented; Swagger is API documentation, not a patient dashboard |

## Non-functional requirements and evaluation

| Area | How it is addressed |
| --- | --- |
| Deployment | Live Railway API/PostgreSQL and active Vapi phone association; phone acceptance disclosed as pending |
| Readable, consistent code | Separate routes, schemas/validators, services, repositories and provider integration; lint passes |
| Complete, accurate README | Concise entry point linking reviewer instructions, setup, architecture, API and test evidence |
| Documented trade-offs | Managed voice platform, local SQLite/hosted PostgreSQL, one active patient per phone, model consent boundary and deferred production controls described in ARCHITECTURE.md |
| Included and explained prompt | app/voice/prompts/patient_registration_system.md has labeled sections, examples, consent rules and recovery instructions; configuration.py defines tool behavior |
| Security | Environment-based credentials, API/webhook authentication and parameterized ORM access; reviewer key delivered privately |
| Observability | Structured tool/error logs and final confirmed fictional payload logging |

The five equally weighted evaluation categories are working system, conversational
quality, technical architecture, code/documentation, and edge cases/resilience.
Tests support backend correctness; browser calls support voice integration. Neither
is presented as proof of telephone-carrier access or perfect speech behavior.
Use fictional information only. This assessment does not claim HIPAA compliance.
