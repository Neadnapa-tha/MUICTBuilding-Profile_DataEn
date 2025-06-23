import logging
from datetime import datetime, timedelta
import requests
from airflow.models import Variable
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook


default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 5, 19),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=10),
}

dag = DAG(
    'create_transection_data',
    default_args=default_args,
    description='create_transection_data',
    # schedule_interval='@daily',
    schedule_interval='0 4 * * *' 
)


def get_jwt_token():
    api_key = "7YTzkxTT8n7i2FEMX7eS67Ba+BnN2PtUZTSazeiUFX4="
    version = "1.0"
    api_url = "https://de.ict.mahidol.ac.th/data-service/v1/Authen/apikey"

    try:
        params = {"apiKey": api_key, "version": version}
        response = requests.post(api_url, params=params)
        response.raise_for_status()
        token = response.json().get("data").get("token")
        return token
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching JWT token: {e}")
        return None



def create_api_data():
    try:
        postgres_hook = PostgresHook(postgres_conn_id='postgres_conn')
        create_table_query = """
        CREATE TABLE IF NOT EXISTS api_data AS
        SELECT 
            booking.booking_id, 
            booking.activity_id, 
            booking.booking_request_date, 
            booking.booking_start_time, 
            booking.booking_end_time, 
            booking.duration_in_minute, 
            booking.remarks AS booking_remarks, 
            booking.booking_end_date, 
            booking.booking_start_date, 
            booking.requester_name, 
            booking.room, 
            booking.floor,
            participant.participant_type_id, 
            participant.participant_type, 
            participant.amount_exact, 
            participant.amount,
            activity.activity_name,
            attendance.id AS attendance_id, 
            attendance.remarks AS attendance_remarks, 
            attendance.num_enrolledStd, 
            attendance.num_present, 
            attendance.percent_present, 
            attendance.num_absent, 
            attendance.percent_absent, 
            attendance.num_leave, 
            attendance.percent_leave, 
            attendance.class_date, 
            attendance.class_start, 
            attendance.class_end,
            class_info.subject_code, 
            class_info.subject_name, 
            class_info.section
        FROM 
            booking
        LEFT JOIN 
            participant ON booking.booking_id = participant.booking_id
        LEFT JOIN 
            activity ON booking.activity_id = activity.activity_id
        LEFT JOIN 
            attendance ON booking.booking_id = attendance.booking_id
        LEFT JOIN 
            class_info ON attendance.remarks = class_info.remarks;

        """
        postgres_hook.run(create_table_query)
        logging.info("Successfully created api_data table.")
    except Exception as e:
        logging.error(f"Error creating api_data table: {e}")
        raise

def create_transection_data():
    try:
        postgres_hook = PostgresHook(postgres_conn_id='postgres_conn')
        create_table_query = """
        CREATE TABLE IF NOT EXISTS transsection AS
        SELECT 
            th.date,
            th.time,
            th.temperature,
            th.humidity,
            th.heat,
            td.booking_id,
            td.activity_id,
            td.booking_request_date,
            td.booking_start_date,
            td.booking_end_date,
            td.booking_start_time,
            td.booking_end_time,
            td.duration_in_minute,
            td.booking_remarks,
            td.subject_code,
            td.requester_name,
            td.room,
            td.floor,
            td.participant_type_id,
            td.participant_type,
            td.amount_exact,
            td.amount,
            td.activity_name,
            td.section,
            td.subject_name,
            td.class_date,
            td.class_start,
            td.class_end,
            td.num_enrolledStd,
            td.num_present,
            td.percent_present,
            td.num_absent,
            td.percent_absent,
            td.num_leave,
            td.percent_leave
        FROM 
            temp_and_humi AS th
        LEFT JOIN 
            api_data AS td ON 
            th.date = td.booking_start_date 
            AND CAST(th.time AS time) >= CAST(td.booking_start_time AS time) 
            AND CAST(th.time AS time) < CAST(td.booking_end_time AS time);
  
        """
        postgres_hook.run(create_table_query)
        logging.info("Successfully created transsection table.")
    except Exception as e:
        logging.error(f"Error creating transsection table: {e}")
        raise



def delete_api_data():
    try:
        postgres_hook = PostgresHook(postgres_conn_id='postgres_conn')
        delete_query = "DROP TABLE IF EXISTS api_data;"
        postgres_hook.run(delete_query)
        logging.info("Successfully deleted data from api_data table.")
    except Exception as e:
        logging.error(f"Error deleting data from api_data table: {e}")
        raise

def delete_transection_data():
    try:
        postgres_hook = PostgresHook(postgres_conn_id='postgres_conn')
        delete_query = "DROP TABLE IF EXISTS transsection;"
        postgres_hook.run(delete_query)
        logging.info("Successfully deleted data from transsection table.")
    except Exception as e:
        logging.error(f"Error deleting data from transsection table: {e}")
        raise


get_jwt_token_task = PythonOperator(
    task_id='get_jwt_token',
    python_callable=get_jwt_token,
    dag=dag,
)

delete_api_data_task = PythonOperator(
    task_id='delete_api_data',
    python_callable=delete_api_data,
    dag=dag,
)

create_api_data_task = PythonOperator(
    task_id='create_api_data',
    python_callable=create_api_data,
    dag=dag,
)

delete_transection_data_task = PythonOperator(
    task_id='delete_transection_data',
    python_callable=delete_transection_data,
    dag=dag,
)

create_transection_data_task = PythonOperator(
    task_id='create_transection_data',
    python_callable=create_transection_data,
    dag=dag,
)



get_jwt_token_task >> delete_api_data_task >> create_api_data_task >> delete_transection_data_task >> create_transection_data_task 



