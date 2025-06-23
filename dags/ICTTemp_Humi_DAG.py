# Start Service: docker compose up -d
# Shutdown Docker: docker compose down -v
# pip install apache-airflow-providers-http
# https://github.com/nndd91/handle-api-with-airflow-example/blob/master/airflow/dags/simple_api_dag_example.py

from airflow import DAG
# from airflow.operators.http_operator import SimpleHttpOperatordocker 
from airflow.operators.python_operator import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.providers.http.operators.http import SimpleHttpOperator
from airflow.utils.dates import days_ago
from datetime import datetime, timedelta
import requests
import json

default_args = {
    'owner': 'Group4',
    'depends_on_past': False,
    'start_date': datetime(2024, 5, 15),
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}

def fetch_and_process_data(**kwargs):
    url = 'https://26b5-2001-44c8-44c9-57f6-748c-c488-46cb-4b93.ngrok-free.app/ICTTemp_Humi'
    response = requests.get(url)
    data = response.json()
    kwargs['ti'].xcom_push(key='temp_humi_data', value=data)

def create_table_database():
    try:
        pg_hook = PostgresHook(postgres_conn_id='postgres_conn')

        pg_hook.run("""
                CREATE TABLE IF NOT EXISTS temp_and_humi (
                date DATE NOT NULL,
                time TIME NOT NULL,
                temperature DECIMAL(5,2) NOT NULL,
                humidity DECIMAL(5,2) NOT NULL,
                heat DECIMAL(5,2) NOT NULL,
                PRIMARY KEY (date, time)
                );
        """)
        print("Table 'booking' created successfully or already exists.")
    except Exception as e:
        print(f"Error: {str(e)}")


def save_data_into_db(**kwargs):
    try:
        data = kwargs['ti'].xcom_pull(key='temp_humi_data', task_ids='fetch_data_from_api')
        
        pg_hook = PostgresHook(postgres_conn_id='postgres_conn')
        
        for record in data:
            date = record['Date']
            time = record['Time']
            temperature = record['Temp']
            humidity = record['Humidity']
            heat = record['Heat']
            
            pg_hook.run(
                sql="""
                INSERT INTO temp_and_humi (date, time, temperature, humidity, heat)
                VALUES (%s, %s, %s, %s, %s);
                """,
                parameters=(date, time, temperature, humidity, heat)
            )
        print("Data inserted successfully into PostgreSQL.")
    except FileNotFoundError:
        print("Error: Data file not found.")
    except json.JSONDecodeError:
        print("Error: JSON decoding failed.")
    except Exception as e:
        print(f"Error: {e}")

def delete_data(**kwargs): 
    # try:
    #     with open('dags/temp_humi.json', 'w') as f:
    #         f.truncate(0)  # ลบข้อมูลทั้งหมดใน file
    #     print("JSON data deleted successfully.")
    # except FileNotFoundError:
    #     print("Error: JSON file not found.")
    try:
        pg_hook = PostgresHook(postgres_conn_id='postgres_conn')
        # pg_hook.run("DROP TABLE IF EXISTS temp_and_humi;")
        pg_hook.run("DELETE FROM temp_and_humi;")
        print("Delete table successfully from PostgreSQL.")
    except Exception as e:
        print(f"Error: {e}")

dag = DAG(
    'temp_humi_dag',
    default_args=default_args,
    description='Run ICT Temperature and Humidity Flask API',
    # schedule_interval='@daily',
    schedule_interval='0 1 * * *' 
)

call_flask_api = SimpleHttpOperator(
    task_id='call_flask_api',
    http_conn_id='http_flask_connection', 
    endpoint='/ICTTemp_Humi',
    method='GET',
    dag=dag,
)

fetch_data_from_api = PythonOperator(
    task_id='fetch_data_from_api',
    python_callable=fetch_and_process_data,
    provide_context=True,
    dag=dag,
)

database_api = PythonOperator(
    task_id='save_data_into_db',
    python_callable=save_data_into_db,
    dag=dag
)

delete_data_task = PythonOperator(
    task_id='delete_data',
    python_callable=delete_data,
    dag=dag
)

createe_table_task = PythonOperator(
    task_id='create_table_database',
    python_callable=create_table_database,
    dag=dag
)

delete_data_task >> createe_table_task >> call_flask_api >> fetch_data_from_api >> database_api



