# REST API

[Back to README](README.md)

`/docs` and `/openapi.json` describe the schemas. Patient and appointment endpoints require
`X-API-Key` when configured. Successes return `{"data": ..., "error": null}`;
errors return `{"data": null, "error": {"code": "...", "message": "...", "details": ...}}`.

| Method | Path | Result |
| --- | --- | --- |
| GET | `/health` | 200 and database connectivity check |
| GET | `/patients` | Active records; optional `last_name`, `date_of_birth`, `phone_number` filters |
| GET | `/patients/{UUID}` | One active record, or 404 |
| POST | `/patients` | Validated create, 201 |
| PUT | `/patients/{UUID}` | Partial update, 200; omitted fields stay unchanged |
| DELETE | `/patients/{UUID}` | Set `deleted_at`, 200; never delete the row |
| GET | `/dashboard` | Public UI shell; all patient/appointment data requires the API key |
| GET | `/appointments/slots` | Available ISO timestamps, timezone UTC, duration and schedule description |
| GET | `/appointments` | Appointment history, optionally filtered by `patient_id` |
| POST | `/appointments` | Book `{ "patient_id": "UUID", "starts_at": "ISO timestamp with timezone" }`, 201 |
| DELETE | `/appointments/{UUID}` | Cancel idempotently, retain history and release the slot, 200 |

Choose `starts_at` from `/appointments/slots`: weekdays 14:00–20:00 UTC, 30-minute
visits, next 14 days. Past, off-grid, timezone-less or out-of-window timestamps
return 422. Taken slots return 409; repeating the same patient/slot returns the
existing active appointment. A database partial unique index protects concurrent
booking attempts. All visits are mock. Deleting a patient cancels upcoming visits.

Invalid input/UUIDs return 422; conflicts/duplicate active phones 409; unauthenticated
requests 401; write failures 500. Null clears optional fields; null cannot clear a
required field or preferred_language. Unknown fields are rejected. Searches combine
filters with AND; last-name matching is exact and case-insensitive.

Example POSIX shell commands (PowerShell users can use Swagger or `curl.exe` with
appropriate quoting). Replace `YOUR_API_KEY` with your configured key:

```sh
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/patients \
  -H 'X-API-Key: YOUR_API_KEY' -H 'Content-Type: application/json' \
  -d '{"first_name":"Jane","last_name":"Demo","date_of_birth":"06/14/1993","sex":"Female","phone_number":"415-555-0182","address_line_1":"123 Fictional Street","city":"San Francisco","state":"CA","zip_code":"94105"}'
curl 'http://127.0.0.1:8000/patients?phone_number=415-555-0182' -H 'X-API-Key: YOUR_API_KEY'
curl -X PUT 'http://127.0.0.1:8000/patients/PATIENT_UUID' \
  -H 'X-API-Key: YOUR_API_KEY' -H 'Content-Type: application/json' -d '{"last_name":"Davis"}'
curl -X DELETE 'http://127.0.0.1:8000/patients/PATIENT_UUID' -H 'X-API-Key: YOUR_API_KEY'
```
