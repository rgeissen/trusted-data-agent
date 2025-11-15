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
DAG_ID = 'tda_00_configure_app'
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
def tda_configure_app():

    # BaseHook is now imported via airflow.sdk
    def get_base_url():
        # Fetch the TDA API URL from the Airflow Connection we created earlier
        return BaseHook.get_connection(CONN_ID).host

    @task()
    def send_configuration():
        # 1. Fetch all configuration parameters from Airflow Variables
        # We use default_var=None so we can detect if critical ones are missing
        provider = Variable.get("tda_provider", default_var=None)
        model = Variable.get("tda_model", default_var=None)
        api_key = Variable.get("tda_api_key", default_var=None)
        
        mcp_name = Variable.get("tda_mcp_name", default_var="default_mcp")
        mcp_host = Variable.get("tda_mcp_host", default_var="localhost")
        mcp_port = Variable.get("tda_mcp_port", default_var="8000")
        mcp_path = Variable.get("tda_mcp_path", default_var="/mcp")

        # 2. Validate critical variables exist
        if not all([provider, model, api_key]):
             missing = []
             if not provider: missing.append("tda_provider")
             if not model: missing.append("tda_model")
             if not api_key: missing.append("tda_api_key")
             raise AirflowException(f"Missing required Airflow Variables: {', '.join(missing)}")

        # 3. Construct the JSON payload dynamically
        # This matches the structure required by the /v1/configure endpoint
        config_payload = {
            "provider": provider,
            "model": model,
            "credentials": {
                "apiKey": api_key
            },
            "mcp_server": {
                "name": mcp_name,
                "host": mcp_host,
                "port": int(mcp_port), # Ensure port is an integer
                "path": mcp_path
            }
        }

        # 4. Send the POST request
        url = f"{get_base_url()}/api/v1/configure"
        print(f"Sending configuration to {url}...")
        # Print payload for debug, BUT mask the API key for security in logs
        debug_payload = config_payload.copy()
        debug_payload['credentials'] = {'apiKey': '******'}
        print(f"Config Payload: {json.dumps(debug_payload, indent=2)}")

        try:
            resp = requests.post(url, json=config_payload, timeout=10)
            print(f"Response Status: {resp.status_code}")
            print(f"Response Body: {resp.text}")
            resp.raise_for_status()
            print("✅ Configuration successfully applied.")
        except requests.exceptions.ConnectionError:
             raise AirflowException(f"Could not connect to TDA API at {url}. Is it running?")
        except Exception as e:
             raise AirflowException(f"Configuration failed: {e}")

    send_configuration()

configure_dag = tda_configure_app()
