import time
import os
import json
import requests
# Airflow 3 SDK Imports
from airflow.sdk import dag, task
from airflow.sdk import BaseHook
import pendulum # Used for start_date calculation
# Airflow model imports are still generally compatible
from airflow.models import Variable
# The days_ago function is removed in Airflow 3
# from airflow.utils.dates import days_ago 
from airflow.exceptions import AirflowException

# --- CONFIGURATION ---
DAG_ID = 'tda_00_configure_with_questions'
CONN_ID = 'tda_api_conn'

default_args = {
    'owner': 'airflow',
    'retries': 0,
}


@dag(
    dag_id=DAG_ID, 
    default_args=default_args, 
    # FIX: Replaced 'schedule_interval' with the correct parameter 'schedule' for Airflow 3
    schedule=None, 
    start_date=pendulum.now(tz="UTC").subtract(days=1), 
    tags=['tda', 'setup'], 
    catchup=False
)
def tda_configure_from_file():
    """
    Uses the session / submit / poll pattern with access token authentication.
    Reads questions from `questions.txt` and requires a default profile.
    Each question is executed in a new session/query pair with async polling.
    """

    # BaseHook is now imported via airflow.sdk
    def get_base_url():
        return BaseHook.get_connection(CONN_ID).host

    # --- TASK 0: Get Access Token ---
    @task()
    def get_access_token():
        """
        Get or create a long-lived access token.
        Requires: Airflow Variable 'tda_jwt_token' with a valid JWT token.
        """
        jwt_token = Variable.get("tda_jwt_token", default_var=None)
        if not jwt_token:
            raise AirflowException(
                "Missing Airflow Variable 'tda_jwt_token'. "
                "Please set it to a valid JWT token from /auth/login."
            )
        
        token_name = Variable.get("tda_access_token_name", default_var="airflow-dag-token")
        expires_days = int(Variable.get("tda_access_token_expires_days", default_var=90))
        
        url = f"{get_base_url()}/api/v1/auth/tokens"
        headers = {"Authorization": f"Bearer {jwt_token}"}
        payload = {"name": token_name, "expires_in_days": expires_days}
        
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=10)
            resp.raise_for_status()
            access_token = resp.json().get('token')
            if not access_token:
                raise AirflowException("No access token returned from API")
            print(f"✅ Access token obtained: {access_token[:20]}...")
            return access_token
        except requests.exceptions.ConnectionError:
            raise AirflowException(f"Could not connect to TDA API at {url}. Is it running?")
        except Exception as e:
            raise AirflowException(f"Failed to get access token: {e}")

    # --- HELPER: Debug printer ---
    def log_full_request(prepped_req):
        print(f"\n--- DEBUG: SENDING HTTP REQUEST ---")
        print(f"Method: {prepped_req.method}")
        print(f"URL: {prepped_req.url}")
        print("Headers:")
        for k, v in prepped_req.headers.items():
             print(f"  {k}: {v}")
        print(f"Body: {prepped_req.body}")
        print("-----------------------------------\n")

    # --- TASK 1: Get or Create Session ---
    @task()
    def get_or_create_session(access_token: str):
        """
        Reuse existing session if tda_session_id is set, otherwise create new one.
        Requires user to have a default profile configured.
        Profile must have both LLM Provider and MCP Server.
        """
        # Check if reusing existing session
        existing_session_id = Variable.get('tda_session_id', default_var=None)
        if existing_session_id and len(existing_session_id.strip()) > 0:
            print(f"✅ Reusing existing session: {existing_session_id}")
            return existing_session_id.strip()
        
        # Create new session
        url = f"{get_base_url()}/api/v1/sessions"
        headers = {"Authorization": f"Bearer {access_token}"}
        
        session = requests.Session()
        req = requests.Request('POST', url, headers=headers)
        prepped = session.prepare_request(req)

        log_full_request(prepped)

        resp = session.send(prepped, timeout=10)
        print(f"Response Status: {resp.status_code}")
        
        if resp.status_code == 400:
            error_msg = resp.json().get('error', '')
            if 'default profile' in error_msg.lower():
                raise AirflowException(
                    f"No default profile configured. {error_msg}. "
                    "Please configure a profile (LLM + MCP Server) in the UI first."
                )
        
        resp.raise_for_status()
        session_id = resp.json()['session_id']
        print(f"✅ New session created: {session_id}")
        return session_id

    # --- TASK 2: Submit Query ---
    @task()
    def submit_query(access_token: str, session_id: str, question: str):
        """
        Submit a query to a session.
        Optionally use a different profile via tda_profile_id variable.
        Returns task_id for polling.
        """
        url = f"{get_base_url()}/api/v1/sessions/{session_id}/query"
        headers = {"Authorization": f"Bearer {access_token}"}
        
        payload = {'prompt': question}
        
        # Optional: Override profile if tda_profile_id is set
        profile_id = Variable.get('tda_profile_id', default_var=None)
        if profile_id and len(profile_id.strip()) > 0:
            payload['profile_id'] = profile_id.strip()
            print(f"Using profile override: {profile_id}")

        session = requests.Session()
        req = requests.Request('POST', url, json=payload, headers=headers)
        prepped = session.prepare_request(req)

        log_full_request(prepped)

        resp = session.send(prepped, timeout=10)
        print(f"Response Status: {resp.status_code}")
        resp.raise_for_status()

        task_data = resp.json()
        task_id = task_data.get('task_id')
        print(f"✅ Query submitted with task_id: {task_id}")
        return task_data

    # --- TASK 3: Poll for Completion ---
    @task()
    def poll_until_complete(access_token: str, task_start_data: dict):
        """
        Poll task status until completion.
        """
        status_url_path = task_start_data['status_url']
        full_url = f"{get_base_url()}{status_url_path}"
        headers = {"Authorization": f"Bearer {access_token}"}

        print(f"Starting polling loop for: {full_url}")

        while True:
            resp = requests.get(full_url, headers=headers, timeout=10)
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
    access_token = get_access_token()
    session_id = get_or_create_session(access_token)

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
        submit = submit_query.override(task_id=f'submit_Q{idx}')(access_token=access_token, session_id=session_id, question=q)
        wait = poll_until_complete.override(task_id=f'wait_for_Q{idx}')(access_token=access_token, task_start_data=submit)

        # Chain tasks: wait for prev before submitting next
        if prev_wait:
            prev_wait >> submit

        prev_wait = wait


configure_from_file_dag = tda_configure_from_file()
