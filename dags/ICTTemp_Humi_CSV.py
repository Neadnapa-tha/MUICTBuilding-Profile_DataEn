from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.utils.dates import days_ago
from datetime import datetime, timedelta
import pandas as pd

default_args = {
    'owner': 'Group4',
    'depends_on_past': False,
    'start_date': datetime(2024, 5, 15),
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}

def fetch_and_process_data(**kwargs):
    csv_file_path = 'dags/generate_data/ICTTemp_Humi.csv'
    data = pd.read_csv(csv_file_path)
    records = data.to_dict(orient='records')
    kwargs['ti'].xcom_push(key='temp_humi_data', value=records)

def create_table_database():
    try:
        pg_hook = PostgresHook(postgres_conn_id='postgres_conn')
        pg_hook.run("""
                CREATE TABLE IF NOT EXISTS test_temp_and_humi (
                date DATE NOT NULL,
                time TIME NOT NULL,
                temperature DECIMAL(5,2) NOT NULL,
                humidity DECIMAL(5,2) NOT NULL,
                heat DECIMAL(5,2) NOT NULL,
                PRIMARY KEY (date, time)
                );
        """)
        print("Table 'test_temp_and_humi' created successfully or already exists.")
    except Exception as e:
        print(f"Error: {str(e)}")

def save_data_into_db(**kwargs):
    try:
        data = kwargs['ti'].xcom_pull(key='temp_humi_data', task_ids='fetch_data_from_csv')
        
        pg_hook = PostgresHook(postgres_conn_id='postgres_conn')
        
        for record in data:
            date = record['Date']
            time = record['Time']
            temperature = record['Temp']
            humidity = record['Humidity']
            heat = record['Heat']
            
            pg_hook.run(
                sql="""
                INSERT INTO test_temp_and_humi (date, time, temperature, humidity, heat)
                VALUES (%s, %s, %s, %s, %s);
                """,
                parameters=(date, time, temperature, humidity, heat)
            )
        print("Data inserted successfully into PostgreSQL.")
    except Exception as e:
        print(f"Error: {e}")

def delete_data(**kwargs):
    try:
        pg_hook = PostgresHook(postgres_conn_id='postgres_conn')
        pg_hook.run("DELETE FROM test_temp_and_humi;")
        print("Delete table successfully from PostgreSQL.")
    except Exception as e:
        print(f"Error: {e}")

dag = DAG(
    'temp_humi_dag_csv',
    default_args=default_args,
    description='Read ICT Temperature and Humidity Data from CSV and Save to DB',
    schedule_interval='@daily',
)

fetch_data_from_csv = PythonOperator(
    task_id='fetch_data_from_csv',
    python_callable=fetch_and_process_data,
    provide_context=True,
    dag=dag,
)

database_api = PythonOperator(
    task_id='save_data_into_db',
    python_callable=save_data_into_db,
    provide_context=True,
    dag=dag
)

delete_data_task = PythonOperator(
    task_id='delete_data',
    python_callable=delete_data,
    dag=dag
)

create_table_task = PythonOperator(
    task_id='create_table_database',
    python_callable=create_table_database,
    dag=dag
)

delete_data_task >> create_table_task >> fetch_data_from_csv >> database_api
