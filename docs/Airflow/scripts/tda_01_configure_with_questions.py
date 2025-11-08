import time
import os
import json
import requests
from airflow.decorators import dag, task
from airflow.hooks.base import BaseHook
from airflow.models import Variable
from airflow.utils.dates import days_ago
from airflow.exceptions import AirflowException

# --- CONFIGURATION ---
DAG_ID = 'tda_01_configure_with_questions'
CONN_ID = 'tda_api_conn'

# Default user uuid (keeps behavior consistent with `tda_master_dag.py`)
USER_UUID = Variable.get('tda_user_uuid', default_var='airflow-dag-user-01')

default_args = {
    'owner': 'airflow',
    'retries': 0,
}


@dag(dag_id=DAG_ID, default_args=default_args, schedule_interval=None, start_date=days_ago(1), tags=['tda', 'setup'], catchup=False)
def tda_configure_from_file():
    """
    Uses the session / submit / poll pattern from `tda_master_dag.py`, but reads questions
    from `questions.txt` (one per line) and runs each as its own submit+poll pair.

    - Retrieves/creates a session via the same `get_or_create_session` logic.
    - For each question in `questions.txt`, it will call `submit_query` then `poll_until_complete`.
    - Tasks are chained so each question waits for the previous question's poll to finish before submitting.
    """

    def get_base_url():
        return BaseHook.get_connection(CONN_ID).host

    # --- HELPER: Debug printer (copied from master dag) ---
    def log_full_request(prepped_req):
        print(f"\n--- DEBUG: SENDING HTTP REQUEST ---")
        print(f"Method: {prepped_req.method}")
        print(f"URL: {prepped_req.url}")
        print("Headers:")
        for k, v in prepped_req.headers.items():
             print(f"  {k}: {v}")
        print(f"Body: {prepped_req.body}")
        print("-----------------------------------\n")

    # --- TASK 1: Get Existing or Create New Session ---
    @task()
    def get_or_create_session():
        existing_session_id = Variable.get('tda_session_id', default_var=None)

        if existing_session_id and len(existing_session_id.strip()) > 0:
             print(f"✅ Found existing session ID in Airflow Variables: {existing_session_id}")
             print("Skipping API creation call.")
             return existing_session_id.strip()

        print("ℹ️ No session ID found in variables (Variable 'tda_session_id' is missing or empty).")
        print("Creating a new session via API...")

        url = f"{get_base_url()}/api/v1/sessions"
        session = requests.Session()
        req = requests.Request('POST', url, headers={'X-TDA-User-UUID': USER_UUID})
        prepped = session.prepare_request(req)

        log_full_request(prepped)

        resp = session.send(prepped, timeout=10)
        print(f"Response Status: {resp.status_code}")
        resp.raise_for_status()

        new_session_id = resp.json()['session_id']
        print(f"✅ New session created successfully: {new_session_id}")
        return new_session_id

    # --- TASK 2: Submit Query ---
    @task()
    def submit_query(session_id: str, question: str):
        url = f"{get_base_url()}/api/v1/sessions/{session_id}/query"
        payload = {'prompt': question}

        session = requests.Session()
        req = requests.Request('POST', url, json=payload, headers={'X-TDA-User-UUID': USER_UUID})
        prepped = session.prepare_request(req)

        log_full_request(prepped)

        resp = session.send(prepped, timeout=10)
        print(f"Response Status: {resp.status_code}")
        resp.raise_for_status()

        return resp.json()

    # --- TASK 3: Poll for Completion ---
    @task()
    def poll_until_complete(task_start_data: dict):
        status_url_path = task_start_data['status_url']
        full_url = f"{get_base_url()}{status_url_path}"

        print(f"Starting polling loop for: {full_url}")

        while True:
            resp = requests.get(full_url, headers={'X-TDA-User-UUID': USER_UUID}, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            current_status = data.get('status')
            print(f"Current Status: {current_status}")

            if current_status in ['complete', 'error', 'cancelled']:
                print(f"Final state reached: {current_status}")
                if current_status != 'complete':
                    raise AirflowException(f"TDA Task failed with status: {current_status}")

                print(f"RESULT: {json.dumps(data.get('result'), indent=2)}")
                return data.get('result')

            time.sleep(5)

    # --- WORKFLOW DEFINITION ---
    active_session_id = get_or_create_session()

    # Read questions file
    dag_folder = os.path.dirname(__file__)
    questions_path = os.path.join(dag_folder, 'questions.txt')

    if not os.path.exists(questions_path):
        # Nothing to schedule if no file exists — keep DAG readable in Airflow UI
        def noop():
            print(f"No questions file found at {questions_path}; nothing to run.")
        noop()
        return

    with open(questions_path, 'r', encoding='utf-8') as fh:
        raw_lines = fh.readlines()

    questions = [ln.strip() for ln in raw_lines if ln.strip() and not ln.strip().startswith('#')]

    if not questions:
        def noop2():
            print(f"Questions file at {questions_path} is empty or only comments; nothing to run.")
        noop2()
        return

    prev_wait = None
    for idx, q in enumerate(questions, start=1):
        submit = submit_query.override(task_id=f'submit_Q{idx}')(session_id=active_session_id, question=q)
        wait = poll_until_complete.override(task_id=f'wait_for_Q{idx}')(task_start_data=submit)

        # If there was a previous question, ensure ordering: wait for prev before submitting this
        if prev_wait:
            prev_wait >> submit

        prev_wait = wait


configure_from_file_dag = tda_configure_from_file()
