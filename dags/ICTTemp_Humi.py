import random
from flask import Flask, jsonify
from datetime import datetime, timedelta
from flask import *

app = Flask(__name__)

@app.route('/ICTTemp_Humi', methods=['GET'])
def get_datetime_data():
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 4, 27)

    datetime_list = []

    current_date = start_date
    while current_date <= end_date:
        temp = round(random.uniform(22, 28), 2)  # สุ่มค่าอุณหภูมิในช่วง 22-28 องศาเซลเซียส 
        humidity = round(random.uniform(40, 80), 2)  # สุ่มค่าความชื้นในช่วง 10-90% ที่จริงควรอยู่ในช่วง 40%-80%
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

    return jsonify(datetime_list)

if __name__ == '__main__':
    # app.run(host='172.20.10.8', debug=True, port=2024)
    app.run(debug=True, port=2024)



# from flask import Flask, jsonify
# from datetime import datetime, timedelta
# import random

# app = Flask(__name__)

# @app.route('/ICTTemp_Humi', methods=['GET'])
# def get_datetime_data():
#     start_date = datetime(2024, 1, 1)
#     end_date = datetime(2024, 4, 27)

#     datetime_list = []

#     current_date = start_date
#     while current_date <= end_date:
#         # กำหนดค่าอุณหภูมิตามช่วงเวลา
#         hour = current_date.hour
#         if 8 <= hour < 12:
#             temp = round(random.uniform(23, 25), 2)
#         elif 13 <= hour < 17:
#             temp = round(random.uniform(26, 27), 2)
#         elif 18 <= hour < 22:
#             temp = round(random.uniform(25, 26), 2)
#         else:
#             temp = round(random.uniform(24, 25), 2)
        
#         humidity = round(random.uniform(40, 80), 2)  # สุ่มค่าความชื้นในช่วง 40-80%
#         temp_fahrenheit = (temp * 9/5) + 32
#         heat = temp_fahrenheit

#         datetime_list.append({
#             'Date': current_date.strftime('%Y-%m-%d'),
#             'Time': current_date.strftime('%H:%M:%S'),
#             'Temp': temp,
#             'Humidity': humidity,
#             'Heat': round(heat, 2)
#         })
#         current_date += timedelta(minutes=30)

#     return jsonify(datetime_list)

# if __name__ == '__main__':
#     app.run(debug=True, port=2024)



# Command Check
# # lsof -i :2024
# # lsof -ti:2024 | xargs kill
# # kill -9 1506 1507
# # netstat -an | grep 2024

# pip install pyngrok 
# https://www.youtube.com/watch?v=5ZMpbdK0uqU
# ngrok http http://localhost:8080
