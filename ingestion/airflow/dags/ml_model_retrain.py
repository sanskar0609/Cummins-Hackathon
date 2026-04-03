import os
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.bash import BashOperator

# Basic standard arguments for DAG
default_args = {
    'owner': 'supply_chain_os_ml',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=10),
}

with DAG(
    'ml_model_retrain',
    default_args=default_args,
    description='Weekly re-training orchestration of Chokepoint & Demand/Supply LSTM Models',
    schedule_interval='@weekly',
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=['ml', 'training'],
) as dag:

    # 1. Trigger the job
    start_retraining = EmptyOperator(
        task_id='start_retraining'
    )

    # 2. Extract Data from Data Warehouse (S3 / Local processed folder / PostgreSQL)
    extract_latest_data = BashOperator(
        task_id='extract_latest_data',
        bash_command='echo "Extracting historical ais-feed and flight-feed data... Placeholder for Phase 4"'
    )

    # 3. Trigger LSTM retrain script
    chokepoint_lstm_train = BashOperator(
        task_id='train_chokepoint_lstm',
        bash_command='echo "Running PyTorch LSTM model... Placeholder for Phase 4"'
    )

    # 4. Push newly minted model artifact parameters to MLflow
    register_model_mlflow = BashOperator(
        task_id='register_model_mlflow',
        bash_command='echo "Logging metrics & artifacts to local MLFlow container... Placeholder for Phase 4"'
    )
    
    # 5. Success
    complete_retraining = EmptyOperator(
        task_id='complete_retraining'
    )

    # Define execution graph sequence flow
    start_retraining >> extract_latest_data >> chokepoint_lstm_train >> register_model_mlflow >> complete_retraining
