from datetime import datetime, timedelta

# The DAG object; we'll need this to instantiate a DAG
from airflow import DAG

# Operators; we need this to operate!
from airflow.operators.bash import BashOperator

# Dictionary to set the default arguments for each operator
# There are lots more options, please read the Airflow Documents
default_args = {
    'owner': 'Your Name',  # Change this to be your name
    'retries': 5,
    'retry_delay': timedelta(minutes=2)
}

# Start defining DAG
with DAG(
    dag_id='first_dag',  # Unique ID
    default_args=default_args,  # Default Arguments
    description='This is our first dag',  # Description
    start_date=datetime(2024, 1, 23, 2),  # When to start this workflow (DAG)
    schedule_interval='@daily'            # Repeat the workflow every day
) as dag:

		# This is the first task inside the DAG workflow
    task1 = BashOperator(
        task_id='first_task',
        bash_command="echo Hello World - This is the first task"
    )

		# Workflow dependency
		# Since there is only one task, you simply add the task1 object here
task1