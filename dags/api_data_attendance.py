import logging
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
    'retries': 5,
    'retry_delay': timedelta(minutes=10),
}

dag = DAG(
    'api_data_attendance_test_naja',
    default_args=default_args,
    description='Pipeline to fetch data from API and insert into PostgreSQL',
    # schedule_interval='@daily',
    schedule_interval='0 3 * * *' 
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



def extract_classInfo_att_data_from_api(**kwargs):
    postgres_hook = PostgresHook(postgres_conn_id='postgres_conn')
    api_data = []
    pattern = r'^\d+\|[A-Z]+[0-9]+\|\d+$'

    try:
        query = "SELECT DISTINCT remarks FROM booking;"
        booking = postgres_hook.get_records(query)

        if booking:
            jwt_token = get_jwt_token()

            for result in booking:
                if re.match(pattern, result[0]):
                    data = result[0].split("|")
                    semester = data[0]
                    subject_code = data[1]
                    section = data[2]

                    if jwt_token:
                        api_url = "https://de.ict.mahidol.ac.th/data-service/v1/ClassInfo/AttendaceSummary"
                        headers = {"Authorization": f"Bearer {jwt_token}"}
                        params = {
                            "semester": semester,
                            "subjectCode": subject_code,
                            "section": section,
                            "version": "1"
                        }

                        try:
                            response = requests.get(api_url, params=params, headers=headers)
                            response.raise_for_status()
                            remarks = result[0] 
                            data = response.json()
                            if data.get('success') and data.get('data'):
                                combined_data = { "remarks": remarks, "data": data['data']}  # รวมข้อมูล JSON และข้อมูลจากฐานข้อมูล
                                api_data.append(combined_data)
                            logging.info(combined_data)
                        except requests.exceptions.RequestException as e:
                            logging.error(f"Error fetching ClassInfo Att data from API: {e}")
                            raise

                else:
                    logging.warning(f"Invalid data format: {result[0]}")

        return api_data

    except Exception as e:
        logging.error(f"Error in extract_classInfo_att_data_from_api: {e}")
        raise


def save_data_to_postgresql(**kwargs):
    postgres_hook = PostgresHook(postgres_conn_id='postgres_conn')
    ti = kwargs['ti']
    api_data = ti.xcom_pull(task_ids='extract_classInfo_att_data_from_api')

    if api_data:
        try:
            for item in api_data:
                remarks = item['remarks']
                subject_code = item['data']['subjectCode']
                subject_name = item['data']['subjectName']

                for attendance in item['data']['sections']:
                    section = attendance['sec']

                    # Check if remarks exists in the database
                    remarks_check_query = """
                        SELECT COUNT(*) 
                        FROM class_info 
                        WHERE remarks = %s;
                    """
                    remarks_count = postgres_hook.get_first(remarks_check_query, parameters=(remarks,))[0]

                    # If remarks doesn't exist, insert data into class_info table
                    if remarks_count == 0:
                        insert_class_info_query = """
                            INSERT INTO class_info (
                                remarks,
                                subject_code,
                                subject_name,
                                section
                            )
                            VALUES (%s, %s, %s, %s);
                        """
                        postgres_hook.run(
                            insert_class_info_query,
                            parameters=(remarks, subject_code, subject_name, section)
                        )
                        logging.info(f"Successfully inserted data into class_info table for remarks: {remarks}")
                    else:
                        logging.info(f"Remarks {remarks} already exists in class_info table. Skipping insertion.")

                    for record in attendance['attendances']:
                        num_enrolledStd = record['numEnrolledStd']
                        num_present = record['numPresent']
                        percent_present = record['percentPresent']
                        num_absent = record['numAbsent']
                        percent_absent = record['percentAbsent']
                        num_leave = record['numLeave']
                        percent_leave = record['percentLeave']
                        class_date = record['classDate']
                        class_start = record['classStart']
                        class_end = record['classEnd']

                        # Check booking and get booking_id
                        booking_id = None
                        booking_check_query = """
                            SELECT booking_id 
                            FROM booking 
                            WHERE remarks = %s 
                                AND booking_start_date = %s 
                                AND booking_start_time <= %s 
                                AND booking_end_time >= %s;
                        """
                        booking_check_result = postgres_hook.get_first(
                            booking_check_query,
                            parameters=(
                                remarks,
                                class_date,
                                class_start,
                                class_end
                            )
                        )
                        if booking_check_result:
                            booking_id = booking_check_result[0]

                        # Insert data into attendance table
                        insert_attendance_query = """
                            INSERT INTO attendance (
                                booking_id,
                                remarks,
                                num_enrolledStd,
                                num_present,
                                percent_present,
                                num_absent,
                                percent_absent,
                                num_leave,
                                percent_leave,
                                class_date,
                                class_start,
                                class_end
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                        """

                        postgres_hook.run(
                            insert_attendance_query,
                            parameters=(
                                booking_id,
                                remarks,
                                num_enrolledStd,
                                num_present,
                                percent_present,
                                num_absent,
                                percent_absent,
                                num_leave,
                                percent_leave,
                                class_date,
                                class_start,
                                class_end
                            )
                        )
                        logging.info("Successfully inserted data into attendance table.")
                        
        except Exception as e:
            logging.error(f"Error inserting data to PostgreSQL: {e}")
            raise e


def create_att_data_into_db():
    postgres_hook = PostgresHook(postgres_conn_id='postgres_conn')
    conn = postgres_hook.get_conn()
    CREATE = """
        CREATE TABLE IF NOT EXISTS attendance (
            id SERIAL PRIMARY KEY,
            booking_id INT,
            remarks VARCHAR(255),
            num_enrolledStd INT,
            num_present INT,
            percent_present DECIMAL(5,2),
            num_absent INT,
            percent_absent DECIMAL(5,2),
            num_leave INT,
            percent_leave DECIMAL(5,2),
            class_date DATE,
            class_start TIME,
            class_end TIME
        );
        """
    postgres_hook.run(CREATE)

def create_classinfo_into_db():
    postgres_hook = PostgresHook(postgres_conn_id='postgres_conn')
    conn = postgres_hook.get_conn()
    CREATE = """
        CREATE TABLE IF NOT EXISTS class_info (
            remarks VARCHAR(255) PRIMARY KEY ,
            subject_code VARCHAR(10),
            subject_name VARCHAR(255),
            section VARCHAR(10)
        );
        """
    postgres_hook.run(CREATE)



def delete_att_data_into_db():
    postgres_hook = PostgresHook(postgres_conn_id='postgres_conn')
    conn = postgres_hook.get_conn()
    DELETE = """
        DELETE FROM attendance;
        """
    postgres_hook.run(DELETE)


def delete_class_info_into_db():
    postgres_hook = PostgresHook(postgres_conn_id='postgres_conn')
    conn = postgres_hook.get_conn()
    DELETE = """
        DELETE FROM class_info;
        """
    postgres_hook.run(DELETE)







get_jwt_token_task = PythonOperator(
    task_id='get_jwt_token',
    python_callable=get_jwt_token,
    dag=dag,
)

extract_classInfo_att_data_from_api_task = PythonOperator(
    task_id='extract_classInfo_att_data_from_api',
    python_callable=extract_classInfo_att_data_from_api,
    provide_context=True,
    dag=dag,
)


# save

# save_att_data_to_postgresql_task = PythonOperator(
#     task_id='save_att_data_to_postgresql',
#     python_callable=save_att_data_to_postgresql,
#     provide_context=True,
#     dag=dag,
# )


# save_classinfo_data_to_postgresql_task = PythonOperator(
#     task_id='save_classinfo_data_to_postgresql',
#     python_callable=save_classinfo_data_to_postgresql,
#     provide_context=True,
#     dag=dag,
# )



save_data_to_postgresql_task = PythonOperator(
    task_id='save_data_to_postgresql',
    python_callable=save_data_to_postgresql,
    provide_context=True,
    dag=dag,
)



# delete


delete_att_data_into_db_task = PythonOperator(
    task_id='delete_att_data_into_db',
    python_callable=delete_att_data_into_db,
    provide_context=True,
    dag=dag,
)

delete_class_info_into_db_task = PythonOperator(
    task_id='delete_class_info_into_db',
    python_callable=delete_class_info_into_db,
    provide_context=True,
    dag=dag,
)



# create

create_att_data_into_db_task = PythonOperator(
    task_id='create_att_data_into_db',
    python_callable=create_att_data_into_db,
    provide_context=True,
    dag=dag,
)


create_classinfo_into_db_task = PythonOperator(
    task_id='create_classinfo_into_db',
    python_callable=create_classinfo_into_db,
    provide_context=True,
    dag=dag,
)




# get_jwt_token_task >> create_att_data_into_db_task >> delete_att_data_into_db_task >> extract_classInfo_att_data_from_api_task >> save_att_data_to_postgresql_task
# get_jwt_token_task >> create_classinfo_into_db_task >> delete_class_info_into_db_task >> extract_classInfo_att_data_from_api_task >> save_classinfo_data_to_postgresql_task


get_jwt_token_task >> create_att_data_into_db_task >> create_classinfo_into_db_task >> delete_att_data_into_db_task >> delete_class_info_into_db_task >> extract_classInfo_att_data_from_api_task >> save_data_to_postgresql_task
