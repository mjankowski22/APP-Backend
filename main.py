from flask import Flask, jsonify, request
from flask_mqtt import Mqtt
import json
import base64
from datetime import datetime
import pandas as pd
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import threading
import time
from shapely.geometry import Point, Polygon

app = Flask(__name__)
socketIO = SocketIO(app, cors_allowed_origins='*')

# Global variables
coordinates = [
    [54.422, 18.675],
    [54.422, 18.448],
    [54.277, 18.448],
    [54.277, 18.675]
]
position = [54.3, 18.5]

# Message buffer with a maximum of 200 messages
MAX_MESSAGES = 200
message_buffer = []

def add_message_to_buffer(message):
    global message_buffer
    if len(message_buffer) >= MAX_MESSAGES:
        message_buffer.pop(0)  # Remove the oldest message if buffer is full
    message_buffer.append(message)

@app.route('/get_position', methods=['GET'])
def get_position():
    return jsonify(position)

@app.route('/get_coordinates', methods=['GET'])
def get_coordinates():
    return jsonify(coordinates)

@app.route('/set_coordinates', methods=['POST'])
def set_coordinates():
    global coordinates
    new_coordinates = request.json.get('coordinates')
    if new_coordinates and len(new_coordinates) == 4:
        coordinates = new_coordinates
        return jsonify({"status": "success"}), 200
    return jsonify({"status": "error", "message": "Invalid data"}), 400

@app.route('/get_console_messages', methods=['GET'])
def get_console_messages():
    return jsonify(message_buffer)

@socketIO.on('connect')
def handle_connect():
    print('Client connected')

@socketIO.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

app.config['MQTT_BROKER_URL'] = '153.19.55.87'
app.config['MQTT_BROKER_PORT'] = 1883
app.config['MQTT_KEEPALIVE'] = 60
app.config['MQTT_TLS_ENABLED'] = False

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://root:APP@153.19.55.87/database'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

mqtt = Mqtt(app)
CORS(app)

class Data(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.String(50), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    memory_status = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f'<Data {self.id}>'

class WeatherData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date_and_time = db.Column(db.DateTime, nullable=False)
    temperature_inside = db.Column(db.Float, nullable=False)
    atmospheric_pressure = db.Column(db.Float, nullable=False)
    light_intensity = db.Column(db.Float, nullable=False)
    water_temperature = db.Column(db.Float, nullable=False)
    localization_n = db.Column(db.Float, nullable=False)
    localization_e = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f"<WeatherData {self.date_and_time}>"


@app.route('/lora_dane/all', methods=['POST', 'GET'])
def lora_dane():
    data = Data.query.order_by(Data.timestamp.asc()).all()
    data_list = [{
        'id': d.id,
        'timestamp': d.timestamp,
        'latitude': d.latitude,
        'longitude': d.longitude,
        'memory_status': d.memory_status
    } for d in data]
    return jsonify(data_list)

@app.route('/5g_dane/all', methods=['POST', 'GET'])
def fiveg_dane():
    data = WeatherData.query.order_by(WeatherData.date_and_time.asc()).all()
    data_list = [{
        'id': d.id,
        'date_and_time': d.date_and_time.strftime('%Y-%m-%d %H:%M:%S'),
        'temperature_inside': d.temperature_inside,
        'atmospheric_pressure': d.atmospheric_pressure,
        'light_intensity': d.light_intensity,
        'water_temperature': d.water_temperature,
        'localization_n': d.localization_n,
        'localization_e': d.localization_e
    } for d in data]
    return jsonify(data_list)

@app.route('/upload_file', methods=['POST'])
def upload_file():
    if 'file' in request.files:
        file = request.files['file']
        df = pd.read_csv(file)
        for index, row in df.iterrows():
            record = WeatherData(
                date_and_time=datetime.strptime(row['Date and time'], '%Y-%m-%d %H:%M:%S.%f'),
                temperature_inside=row['Temperature Inside'],
                atmospheric_pressure=row['Atmospheric Pressure'],
                light_intensity=row['Light Intensity'],
                water_temperature=row['Water Temperature'],
                localization_n=row['LocalizationN'],
                localization_e=row['LocalizationE']
            )
            db.session.add(record)
        db.session.commit()
        return 'Plik został przesłany i zapisany'
    else:
        return 'Brak przesłanego pliku'

@app.route('/turn_wifi', methods=['POST'])
def turn_wifi():
    py_dict = {'turn_wifi': 1}
    message = base64.b64encode(json.dumps(py_dict).encode('utf-8')).decode('utf-8')
    mqtt.publish('/mqtt/downlink/2cf7f120323086aa', json.dumps({"confirmed": False, "fport": 85, "data": message}))
    return '', 200

@app.route('/upload5g_whole_request', methods=['POST'])
def request_whole_file_5g():
    data = request.get_json()
    if 'delete' in data:
        try:
            delete = data['delete']
            py_dict = {'5g_send_whole': 1, 'delete': delete}
            message = base64.b64encode(json.dumps(py_dict).encode('utf-8')).decode('utf-8')
            mqtt.publish('/mqtt/downlink/2cf7f120323086aa', json.dumps({"confirmed": False, "fport": 85, "data": message}))
            return '', 200
        except ValueError as e:
            return '', 400
    else:
        return '', 400

@app.route('/upload5g_part_request', methods=['POST'])
def request_part_file_5g():
    data = request.get_json()
    if 'start_date' in data and 'end_date' in data and 'delete' in data:
        try:
            start_date = str(datetime.strptime(data['start_date'], '%Y-%m-%d'))
            end_date = str(datetime.strptime(data['end_date'], '%Y-%m-%d'))
            delete = data['delete']
            py_dict = {'5g_send_part': 1, 'start': start_date, 'end': end_date, 'delete': delete}
            message = base64.b64encode(json.dumps(py_dict).encode('utf-8')).decode('utf-8')
            mqtt.publish('/mqtt/downlink/2cf7f120323086aa', json.dumps({"confirmed": False, "fport": 85, "data": message}))
            return '', 200
        except ValueError as e:
            return '', 400
    else:
        return '', 400

@mqtt.on_connect()
def handle_connect(client, userdata, flags, rc):
    mqtt.subscribe('/mqtt/uplink')
    mqtt.subscribe('/mqtt/join')

@app.route('/', methods=['POST', 'GET'])
def index():
    return 'Hello world'

@app.route('/interval_change', methods=['POST'])
def change_interval():
    data = request.get_json()
    if 'interval' in data and isinstance(data['interval'], int):
        interval = data['interval']
        py_dict = {"interval": interval}
        message = base64.b64encode(json.dumps(py_dict).encode('utf-8')).decode('utf-8')
        mqtt.publish('/mqtt/downlink/2cf7f120323086aa', json.dumps({"confirmed": False, "fport": 85, "data": message}))
        return '', 200
    else:
        return '', 400

@mqtt.on_message()
def handle_message(client, userdata, message):
    with app.app_context():
        try:
            message = json.loads(message.payload.decode())["data"]
            message = base64.b64decode(message).decode('utf-8')
            data_parts = message.split(',')
            message = message[2:]
            print(message)
            sign = data_parts[0]
            if sign == 'M':
                timestamp = data_parts[1]
                latitude_str = data_parts[2]
                longitude_str = data_parts[3]
                memory_status = data_parts[4]
                fiveg_status = data_parts[5]
                if latitude_str.startswith("N"):
                    latitude = float(latitude_str[1:])
                elif latitude_str.startswith("S"):
                    latitude = -float(latitude_str[1:])
                else:
                    latitude = 0
                if longitude_str.startswith("E"):
                    longitude = float(longitude_str[1:])
                elif longitude_str.startswith("W"):
                    longitude = -float(longitude_str[1:])
                else:
                    longitude = 0

                if fiveg_status == '1':
                    socketIO.emit('fiveg', {'status': 1})
                else:
                    socketIO.emit('fiveg', {'status': 0})

                data = Data(
                    timestamp=timestamp,
                    latitude=latitude,
                    longitude=longitude,
                    memory_status=memory_status
                )
                db.session.add(data)
                db.session.commit()
                message = f'<{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}> Data received via LoraWAN: latitude - {latitude}, longitude - {longitude}, memory status - {memory_status}'
            
            elif sign == 'I':
                interval = data_parts[1]
                message = f"<{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}> Interval change confirmed - interval: {interval}"

            elif sign == 'G':
                connection = data_parts[1]
                if connection == '1':
                    message = f"<{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}> Data was sent successfully"
                else:
                    message = f"<{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}> Cannot send data"

            elif sign == 'B':
                connection = data_parts[1]
                addr = data_parts[2]
                if connection == '1':
                    message = f"<{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}> WiFi is now on - IP address {addr}"
                    socketIO.emit('wifi', {'status': 1})
                else:
                    message = f"<{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}> WiFi is now off"
                    socketIO.emit('wifi', {'status': 0})
                
        except KeyError:
            message = f"<{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}> Device connected successfully"
        except:
            print('Something went wrong')
        
        add_message_to_buffer(message)
        socketIO.emit('console_message', {'message': message})

def check_point():
    global coordinates
    global position
    while True:
        if not is_point_in_polygon(coordinates, position):
            message = f"<{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}> Device out of bounds"
            add_message_to_buffer(message)
            socketIO.emit('console_message', {'message': message})
        time.sleep(10)

def is_point_in_polygon(polygon_coords, point_coord):
    polygon_coords_tuples = [tuple(coord) for coord in polygon_coords]
    point_coord_tuple = tuple(point_coord)
    polygon = Polygon(polygon_coords_tuples)
    point = Point(point_coord_tuple)
    return polygon.contains(point)

if __name__ == '__main__':
    threading.Thread(target=check_point, daemon=True).start()
    socketIO.run(app, host='0.0.0.0', debug=True, allow_unsafe_werkzeug=True)
