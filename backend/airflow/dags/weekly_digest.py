import sys
import os
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

# Map backend directory dynamically so Airflow can resolve app.services
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# Must import AFTER sys.path mapping
from app.services.reports.digest_generator import generate_weekly_digest

default_args = {
    'owner': 'supply_chain_os',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'generate_weekly_digest',
    default_args=default_args,
    description='Generates a weekly PDF digest of top risks and metrics',
    schedule_interval='0 8 * * 1', # Every Monday at 8 AM UTC
    start_date=datetime(2023, 1, 1),
    catchup=False,
    tags=['reporting', 'executive-digest'],
) as dag:

    def run_digest():
        filepath = generate_weekly_digest()
        print(f"Successfully generated digest at {filepath}")
        return filepath

    generate_task = PythonOperator(
        task_id='export_pdf',
        python_callable=run_digest,
    )

    generate_task
