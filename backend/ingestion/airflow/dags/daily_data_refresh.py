import os
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator

# Define default arguments for the DAG
default_args = {
    'owner': 'supply_chain_os',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# The backend directory path for executing standalone scripts
# Adjust this depending on the final Docker / Airflow worker container structure
BACKEND_DIR = "/opt/airflow/backend"

with DAG(
    'daily_data_refresh',
    default_args=default_args,
    description='Orchestrates batch ingestion connectors (Flights & Geopolitical data)',
    schedule_interval=timedelta(hours=6),
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=['ingestion', 'batch'],
) as dag:

    start_ingestion = EmptyOperator(
        task_id='start_ingestion'
    )

    # Trigger Flight Data OpenSky polling
    # Note: ais_stream runs continuously as a background process so it's not managed here
    poll_flights_task = BashOperator(
        task_id='poll_opensky_flights',
        bash_command=f"cd {BACKEND_DIR} && python -m app.services.opensky_ingest",
        # In a real Airflow deployment, this script would either exit after one run or
        # Airflow would trigger an API endpoint via SimpleHttpOperator instead.
        # This bash structure assumes the script is modified to exit after one loop if run by Airflow.
    )

    # Trigger Geopolitical GDELT & RapidAPI polling
    poll_geo_events_task = BashOperator(
        task_id='poll_geo_events',
        bash_command=f"cd {BACKEND_DIR} && python -m app.services.geo_ingest"
    )

    complete_ingestion = EmptyOperator(
        task_id='complete_ingestion'
    )

    # DAG Flow: Start -> (Flights, Geo) -> Complete
    start_ingestion >> [poll_flights_task, poll_geo_events_task] >> complete_ingestion
