# Reviewer guide

[Back to README](README.md)

## Access required

| What you want to test | What you need |
| --- | --- |
| Call the hosted number | A supported route to +1 (859) 689-8029; no application login |
| Inspect/change records through the API | Reviewer API key supplied privately |
| Use the existing Vapi browser assistant | Authorized access to the project owner's Vapi workspace |
| Reproduce on your own account | Your own Vapi account/credits/private key and reachable HTTPS backend; follow [SETUP.md](SETUP.md) |

Do not request or publish the owner's Vapi private key, Railway tokens, or webhook
secret. The reviewer API key authorizes all patient CRUD operations in this demo;
use only fictional records. A shared browser test can also be demonstrated by the
owner. There is no unauthenticated public browser-call URL in this project.

## Make a telephone call

1. Dial **+1 (859) 689-8029**, preferably from a supported U.S. calling route.
2. Say you want to register, answer the questions, and optionally correct a field.
3. Choose whether to add optional information. Confirm the complete read-back.
4. Expect a save acknowledgment and graceful call ending; verify the record below.
5. Call again, say you are returning, give the original registered phone number,
   and request one change. Unchanged demographics should be retained.

The number is active and attached to the assistant. A successful real telephone
conversation has not been verified. Vapi free-number routing has restrictions;
international access should not be assumed. See [Vapi's number documentation](https://docs.vapi.ai/free-telephony).

## Make a browser voice call

1. Sign in to [Vapi](https://dashboard.vapi.ai/) with authorized workspace access.
2. Open assistant `c7d70043-a8cd-4f65-97e3-e18dfe2823ab`. Its display name may appear
   as Patient Registration or Patient Registration Demo; identify it by the ID.
3. Ensure you are testing the current published configuration. An old editor draft
   can send overrides and change the behavior; do not publish stale draft contents.
4. Select **Talk**, allow microphone access, and use headphones if possible.
5. Speak the same registration/update scenario as for a phone call. End the session
   and inspect its transcript and tool results in Vapi's call logs.

Browser calls test speech, conversation, webhooks and database integration over the
internet. They bypass telephone-carrier routing and do not establish phone reachability.
See Vapi's [assistant quickstart](https://docs.vapi.ai/assistants/quickstart) and
[published-version guide](https://docs.vapi.ai/assistants/versioning/versioning-assistants).

## Verify the saved data

1. Open https://patient-api-production-2f36.up.railway.app/docs.
2. Select **Authorize**, enter the reviewer API key (without a Bearer prefix), and authorize.
3. Expand **GET /patients**, select **Try it out**, and filter by the supplied phone number.
4. Check every provided field. For an update, the patient UUID and created_at should
   remain the same, and updated_at should reflect the change.
5. Optional cleanup: DELETE that fictional patient by UUID; subsequent GET should
   return 404. This is soft deletion, so the row remains in storage.

An unauthenticated patient request returns 401. `/health` and `/docs` are public.
If your old key stops working, ask for the current reviewer key; it was rotated
before handoff. [API details](API.md).

## Fictional test scenario

Use Avery Morgan, February 12, 1991, Other, 202-555-0174,
100 Example Street, Boston, MA 02108. Optional email: avery.morgan@example.com.
If that phone already exists, either exercise the returning flow or choose another
unused fictional number in the 555-0100 through 555-0199 range.

After registration, call again and say: "I registered before. I want to add my email."
For a phone change, identify the record by its old number first. Optional nullable
fields can be removed; required fields and preferred_language cannot be null.

## What was actually tested

We used Vapi's browser microphone calls for new registrations, name corrections,
optional opt-out, email additions and returning-patient updates. We inspected the
tool responses and retrieved the resulting records from the deployed REST API.
Separately, automated tests and synthetic HTTP/webhook checks cover validation,
confirmation, all demographic update groups, retries, failures and persistence.

The tester did not have a supported international calling route available, so a
real telephone call was not completed. This is an access limitation, not proof
that telephone calls work or fail. Final post-save speech timing and the full manual
edge-case matrix remain acceptance checks. [Detailed testing evidence](TESTING.md).
