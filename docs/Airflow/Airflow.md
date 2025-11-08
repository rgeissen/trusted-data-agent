## TDA DAGs (tda_00* and tda_01*)

This README documents the purpose and usage of the TDA-related DAGs in the scripts folder. It focuses on the `tda_00*` and `tda_01*` scripts and how to operate them in a typical Airflow deployment.

## Files

- `tda_00_configure_app.py`
  - Purpose: baseline configuration DAG. Reads required configuration values from Airflow Variables and POSTs a single `/api/v1/configure` request to the TDA API. Use this to set provider/model/apiKey and MCP server settings.
  - Key Airflow artifacts used:
    - Connection: `tda_api_conn` — Host should be the base URL of the TDA API (e.g. `http://tda-api:5050`).
    - Variables (required): `tda_provider`, `tda_model`, `tda_api_key`.
    - Variables (optional with defaults): `tda_mcp_name`, `tda_mcp_host`, `tda_mcp_port`, `tda_mcp_path`.
  - Behavior: single synchronous POST using `requests.post(...).raise_for_status()` so the task waits for the response and fails on non-2xx.

- `tda_01_configure_with_questions.py`
  - Purpose: read a `questions.txt` file (one question per line) and run a submit+poll workflow for each question using the same session/submit/poll pattern that the TDA master workflow uses.
  - Files used: `questions.txt` (placed in the same directory as the DAG). Lines starting with `#` are ignored.
  - Key Airflow artifacts used:
    - Connection: `tda_api_conn` — base URL of TDA API.
    - Variables:
      - `tda_user_uuid` (optional) — defaults to `airflow-dag-user-01` if not set.
      - `tda_session_id` (optional) — if present, the DAG will reuse this session instead of creating a new one.
  - Behavior:
    - At DAG-parse time the DAG reads `questions.txt` and creates a `submit_Q{i}` and `wait_for_Q{i}` task for each question found.
    - Each question is submitted to `/api/v1/sessions/<session_id>/query` and the returned `status_url` is polled until completion. The tasks use headers `X-TDA-User-UUID` matching the master workflow.
    - Tasks are chained so each question's submit waits for the previous question's poll to finish (serial ordering).
    - If you add/remove questions, the scheduler must reparse the DAG for changes to take effect (i.e., new runs use the updated task graph).

- `questions.txt`
  - Sample file (one question per line). Edit this file to change which questions the `tda_01*` DAG will run on the next DAG parse.

- `README_tda_questions.md`
  - Short usage notes for the questions-based DAG (also included in this folder).

## How to run

1. Ensure the Airflow Connection `tda_api_conn` is configured (Admin → Connections). The `Host` should contain the scheme+host[:port], e.g. `http://192.168.0.158:5050`.
2. Ensure required Airflow Variables are set (Admin → Variables):
   - For `tda_00_configure_app.py`: `tda_provider`, `tda_model`, `tda_api_key`.
   - For `tda_01_configure_with_questions.py`: `tda_user_uuid` (optional) and optionally `tda_session_id`.
3. Edit `questions.txt` (if using `tda_01_configure_with_questions.py`) with one question per line. Lines starting with `#` are ignored.
4. Trigger the DAG(s) in the Airflow UI or via CLI.

Example curl to test endpoints from an Airflow worker (replace host and payload as appropriate):

```bash
curl -v 'http://192.168.0.158:5050/api/v1/sessions' -X POST -H 'X-TDA-User-UUID: airflow-dag-user-01'

curl -v 'http://192.168.0.158:5050/api/v1/sessions/<session_id>/query' \
  -H 'Content-Type: application/json' \
  -H 'X-TDA-User-UUID: airflow-dag-user-01' \
  -d '{"prompt":"what is the system version?"}'
```

## Troubleshooting

- HTTP 404 when using the questions DAG
  - Symptom: Task logs show a 404 for the composed request URL (e.g. `http://192.168.0.158:5050/api/v1/ask`).
  - Likely cause: the constructed path does not exist on the TDA server. The questions DAG was previously using `/api/v1/ask` by default; the master/session workflow uses `/api/v1/sessions/.../query`.
  - Fixes:
    - Prefer using `tda_01_configure_with_questions.py` (session/submit/poll) which uses `/api/v1/sessions/.../query` and then polls the returned `status_url` (matching the master DAG behavior).
    - Verify `tda_api_conn` in Admin → Connections — Host should be base URL only (no extra path).
    - Use curl from the Airflow worker to inspect available endpoints and validate the correct path.

- Authentication / API key errors
  - Ensure `tda_api_key` (if used by your API) or `tda_user_uuid` are set as Airflow Variables.

## Notes & recommendations

- DAG parse vs run-time: the questions file is read at DAG parse time. If you edit `questions.txt`, wait for the scheduler to reparse the DAG (or trigger a DAG refresh) so new runs pick up changes.
- For many questions, consider converting the DAG to dynamic task mapping or using a single-task iterator to reduce scheduler load.
- If you want session reuse across DAG runs, consider updating `tda_01_configure_with_questions.py` to persist newly-created `session_id` back into Airflow Variable `tda_session_id`.

If you'd like, I can:
- Persist the session ID to `tda_session_id` automatically after creation.
- Convert the questions DAG to dynamic mapping (`.map`) for runtime mapping and better scalability.
- Add a preflight endpoint check that fails fast with a clearer message if the base URL or endpoints are misconfigured.
