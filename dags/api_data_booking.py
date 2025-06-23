import logging
import json
from datetime import datetime, timedelta
import requests
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
import re


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
    'api_data_booking_test',
    default_args=default_args,
    description='Pipeline to fetch data from API and insert into PostgreSQL',
    # schedule_interval='@daily',
    schedule_interval='0 2 * * *' 
)

def get_jwt_token():
    api_key = "7YTzkxTT8n7i2FEMX7eS67Ba+BnN2PtUZTSazeiUFX4="
    version = "1"
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


def extract_booking_data_from_api(**kwargs):
    postgres_hook = PostgresHook(postgres_conn_id='postgres_conn')
    jwt_token = get_jwt_token()
    if not jwt_token:
        logging.error("Failed to retrieve JWT token. Exiting task.")
        return
    start_date = datetime(2024, 1, 1)
    end_date = datetime.now()
    api_url = "https://de.ict.mahidol.ac.th/data-service/v1/Booking/FetchData"
    api_data = []
    try:
        headers = {"Authorization": f"Bearer {jwt_token}"}
        current_date = start_date
        while current_date <= end_date:
            params = {
                "startDate": current_date.strftime('%Y-%m-%d'),
                "endDate": current_date.strftime('%Y-%m-%d'),
                "room": "IT 105",
                "floor": "1",
                "version": "1"
            }
            response = requests.get(api_url, params=params, headers=headers)
            response.raise_for_status()  # Raise an exception for non-200 responses
            data = response.json()
            if data.get('success') and data.get('data'):
                api_data.extend(data['data'])  # Append booking data 
            current_date += timedelta(days=1)
        logging.info(api_data)
        return api_data
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching data from API: {e}")
        return None


def save_data_to_postgresql(**kwargs):
    postgres_hook = PostgresHook(postgres_conn_id='postgres_conn')
    ti = kwargs['ti']
    api_data = ti.xcom_pull(task_ids='extract_booking_data_from_api')

    if not api_data:
        logging.warning("No API data retrieved. Exiting task.")
        return


    insert_booking_query = """
        INSERT INTO booking (
            booking_id,
            activity_id,
            booking_request_date,
            booking_start_time,
            booking_end_time,
            duration_in_minute,
            remarks,
            booking_start_date,
            booking_end_date,
            requester_name,
            room,
            floor
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
    """
    
    insert_activity_query = """
        INSERT INTO activity (activity_id, activity_name)
        VALUES (%s, %s)
        ON CONFLICT (activity_id) DO NOTHING;
    """
    
    insert_participant_query = """
        INSERT INTO participant (
            booking_id,
            participant_type_id,
            participant_type,
            amount_exact,
            amount
        ) VALUES (%s, %s, %s, %s, %s);
    """

    try:
        conn = postgres_hook.get_conn()
        cursor = conn.cursor()
        for booking in api_data:
            cursor.execute(
                insert_booking_query,
                (
                    booking['bookingId'],
                    booking['activityId'],
                    booking['bookingRequestDate'],
                    booking['bookingStartTime'],
                    booking['bookingEndTime'],
                    booking['durationInMinute'],
                    booking['remarks'],
                    booking['bookingStartDate'],
                    booking['bookingEndDate'],
                    booking['requesterName'],
                    booking['room'],
                    booking['floor']
                )
            )
            
            activity = booking['activity']
            cursor.execute(
                insert_activity_query,
                (
                    activity['activityId'],
                    activity['activityName']
                )
            )
            
            for participant in booking['participants']:
                cursor.execute(
                    insert_participant_query,
                    (
                        booking['bookingId'],
                        participant['participantTypeId'],
                        participant['participantType'],
                        participant['amountExact'],
                        participant['amount']
                    )
                )
        conn.commit()
        cursor.close()
        logging.info("Successfully inserted booking data into PostgreSQL.")
    except Exception as e:
        logging.error(f"Error inserting booking data: {e}")
        conn.rollback()




def create_booking_data_into_db():    
    try:
        postgres_hook = PostgresHook(postgres_conn_id='postgres_conn')
        create_booking = """
            CREATE TABLE IF NOT EXISTS booking(
                booking_id INT PRIMARY KEY,
                activity_id INT,
                booking_request_date TIMESTAMP,
                booking_start_time VARCHAR(255),
                booking_end_time VARCHAR(255),
                duration_in_minute INT,
                remarks VARCHAR(255),
                booking_end_date DATE,
                booking_start_date DATE,
                requester_name VARCHAR(255),
                room VARCHAR(255),
                floor INT
            );
        """
        postgres_hook.run(create_booking )
        logging.info("Successfully created table.")
    except Exception as e:
        logging.error(f"Error creating table: {e}")
        raise


def create_activity_data_into_db_():    
    try:
        postgres_hook = PostgresHook(postgres_conn_id='postgres_conn')
        create_activity = """
            CREATE TABLE IF NOT EXISTS activity (
                activity_id INT PRIMARY KEY,
                activity_name VARCHAR(255)
            );
        """
        postgres_hook.run(create_activity)
        logging.info("Successfully created table.")
    except Exception as e:
        logging.error(f"Error creating table: {e}")
        raise


def create_participant_data_into_db():    
    try:
        postgres_hook = PostgresHook(postgres_conn_id='postgres_conn')
        create_participant = """
            CREATE TABLE IF NOT EXISTS participant (
                booking_id INT,
                participant_type_id INT,
                participant_type VARCHAR(255),
                amount_exact VARCHAR(10),
                amount INT
            );
        """
        postgres_hook.run(create_participant)
        logging.info("Successfully created table.")
    except Exception as e:
        logging.error(f"Error creating table: {e}")
        raise




def delete_booking_data_into_db():
    postgres_hook = PostgresHook(postgres_conn_id='postgres_conn')
    conn = postgres_hook.get_conn()
    delete_booking = """
        DELETE FROM booking;
        """
    postgres_hook.run(delete_booking)

def delete_activity_data_into_db():
    postgres_hook = PostgresHook(postgres_conn_id='postgres_conn')
    conn = postgres_hook.get_conn()
    delete = """
        DELETE FROM activity;
        """
    postgres_hook.run(delete)

def delete_participant_data_into_db():
    postgres_hook = PostgresHook(postgres_conn_id='postgres_conn')
    conn = postgres_hook.get_conn()
    delete = """
        DELETE FROM participant;
        """
    postgres_hook.run(delete)






get_jwt_token_task = PythonOperator(
    task_id='get_jwt_token',
    python_callable=get_jwt_token,
    dag=dag,
)

extract_booking_data_from_api_task = PythonOperator(
    task_id='extract_booking_data_from_api',
    python_callable=extract_booking_data_from_api,
    provide_context=True,
    dag=dag,
)

save_data_to_postgresql_task = PythonOperator(
    task_id='save_data_to_postgresql',
    python_callable=save_data_to_postgresql,
    provide_context=True,
    dag=dag,
)


# delete 

delete_booking_data_into_db_task = PythonOperator(
    task_id='delete_booking_data_into_db',
    python_callable=delete_booking_data_into_db,
    provide_context=True,
    dag=dag,
)

delete_activity_data_into_db_task = PythonOperator(
    task_id='delete_activity_data_into_db',
    python_callable=delete_activity_data_into_db,
    provide_context=True,
    dag=dag,
)

delete_participant_data_into_db_task = PythonOperator(
    task_id='delete_participant_data_into_db',
    python_callable=delete_participant_data_into_db,
    provide_context=True,
    dag=dag,
)


# create 

create_booking_data_into_db_task = PythonOperator(
    task_id='create_booking_data_into_db',
    python_callable=create_booking_data_into_db,
    provide_context=True,
    dag=dag,
)


create_activity_data_into_db_task = PythonOperator(
    task_id='create_activity_data_into_db_',
    python_callable=create_activity_data_into_db_,
    provide_context=True,
    dag=dag,
)


create_participant_data_into_db_task = PythonOperator(
    task_id='create_participant_data_into_db',
    python_callable=create_participant_data_into_db,
    provide_context=True,
    dag=dag,
)



# get_jwt_token_task >> create_booking_data_into_db_task >> delete_booking_data_into_db_task >> extract_booking_data_from_api_task >> save_data_to_postgresql_task 
# get_jwt_token_task >> create_activity_data_into_db_task >> delete_activity_data_into_db_task >> extract_booking_data_from_api_task >> save_data_to_postgresql_task 
# get_jwt_token_task >> create_participant_data_into_db_task >> delete_participant_data_into_db_task >> extract_booking_data_from_api_task >> save_data_to_postgresql_task 



get_jwt_token_task >> create_booking_data_into_db_task >> create_activity_data_into_db_task >> create_participant_data_into_db_task >> delete_booking_data_into_db_task  >> delete_activity_data_into_db_task >> delete_participant_data_into_db_task >> extract_booking_data_from_api_task >> save_data_to_postgresql_task 











