import csv
import random
from datetime import datetime, timedelta

def generate_csv(filename):
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 4, 27)

    datetime_list = []

    current_date = start_date
    while current_date <= end_date:
        temp = round(random.uniform(22, 28), 2)
        humidity = round(random.uniform(40, 80), 2)
        temp_fahrenheit = (temp * 9/5) + 32
        heat = temp_fahrenheit

        datetime_list.append({
            'Date': current_date.strftime('%Y-%m-%d'),
            'Time': current_date.strftime('%H:%M:%S'),
            'Temp': temp,
            'Humidity': humidity,
            'Heat': round(heat, 2)
        })
        current_date += timedelta(minutes=30)

    with open(filename, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=['Date', 'Time', 'Temp', 'Humidity', 'Heat'])
        writer.writeheader()
        writer.writerows(datetime_list)

generate_csv('ICTTemp_Humi.csv')
