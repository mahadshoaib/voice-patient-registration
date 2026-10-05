# Submission

## 1. Repository URL

https://github.com/mahadshoaib/voice-patient-registration

Public repository; no reviewer invitation is required.

## 2. Phone number to call

**+1 (859) 689-8029** — provisioned, active and attached to the Vapi assistant.
Please test from a supported U.S. calling route. Real telephone acceptance is pending.

## 3. API base URL

https://patient-api-production-2f36.up.railway.app

- [Interactive API documentation](https://patient-api-production-2f36.up.railway.app/docs)
- [Health check](https://patient-api-production-2f36.up.railway.app/health)
- [Patient dashboard](https://patient-api-production-2f36.up.railway.app/dashboard)

## 4. Credentials and testing notes

The **reviewer API key** is the application's `API_KEY`, used only for authenticated
patient/appointment API and dashboard access. It is NOT the Vapi private key, Railway token, or webhook secret.
Delivery is pending; the owner can share this reviewer key through a private channel.
In Swagger, select Authorize and
enter the key; programmatic patient requests use the `X-API-Key` header.
No login is needed to call the phone number. Browser testing of the hosted assistant
requires authorized Vapi workspace access or an owner-led demonstration. Provider
credentials are not included in the repository and are not needed for telephone/API review.

**Testing disclosure:** We completed live browser voice calls through Vapi, including
new registration and returning-patient updates, and verified the saved data through
the deployed API. We did not complete a real telephone call because a supported
international calling route was unavailable to the tester. Browser testing bypasses
telephone routing; inbound telephone acceptance remains pending.

**Other evidence:** Automated regression tests and lint passed (latest counts in TESTING.md). Remote CRUD, authenticated
webhooks, database persistence across restart/redeploy, confirmation safeguards and
retry recovery were verified. All demographic field-group updates and nullable-field
removal are tested at the tool/API layer; this does not claim every field was tested
through speech. The latest post-save completion guidance requires a fresh spoken check.

Use fictional information only. Phone matching is not identity verification; the
agent is English-only. Voice consent is interpreted by the model. This is a technical
assessment, not a production healthcare system. No HIPAA compliance is claimed.

Start with the [reviewer guide](REVIEWER_GUIDE.md) for phone/browser instructions,
a fictional scenario and API verification. [Architecture](ARCHITECTURE.md) explains
decisions and trade-offs; [testing](TESTING.md) distinguishes checked and pending cases.
The [requirements mapping](REQUIREMENTS.md) covers all five functional requirements,
non-functional expectations and four implemented bonuses: duplicate detection, tests,
patient dashboard and mock appointment booking. Bookings use one demonstration calendar:
weekdays 14:00–20:00 UTC, 30-minute visits, next 14 days. These are not real clinic
appointments. Voice booking and final spoken completion need a fresh spoken acceptance check.

Before sending: privately provide the current reviewer API key,
keep hosting/call credits available, and confirm the assessment deadline. This
document is a prepared handoff, not evidence that a submission has been sent.
