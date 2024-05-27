from flask import Flask, render_template,request,redirect,jsonify
from flask_mqtt import Mqtt
import json
import base64
from datetime import datetime
import pandas as pd
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO,emit



app = Flask(__name__)
socketIO = SocketIO(app)


@SocketIO.on('connect')
def handle_connect():
    print('Client connected')

@SocketIO.on('disconnect')
def handle_disconnect():
    print('Client disconnected')


## Nie ruszać
app.config['MQTT_BROKER_URL'] = '153.19.55.87'  # Adres brokera MQTT
app.config['MQTT_BROKER_PORT'] = 1883        # Port brokera MQTT
app.config['MQTT_KEEPALIVE'] = 60
app.config['MQTT_TLS_ENABLED'] = False

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://root:APP@153.19.55.87/database'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)




# Zostawić
mqtt = Mqtt(app)



#To git powinno byc
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
    
    



@app.route('/lora_dane/all', methods=['POST','GET'])
def lora_dane():
    data = Data.query.all()
    data_list = [{
        'id': d.id,
        'timestamp': d.timestamp,
        'latitude': d.latitude,
        'longitude': d.longitude,
        'memory_status': d.memory_status
    } for d in data]
    return jsonify(data_list)


@app.route('/5g_dane/all', methods=['POST','GET'])
def fiveg_dane():
    data = WeatherData.query.all()
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
        # Czytanie danych CSV
        df = pd.read_csv(file)

        # Konwersja danych i zapis do bazy
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



#5g musi zostać jeśli chodzi o komunikację przez MQTT, to jak przekazywane są console_messages do zmiany, obsługa formularzy też
@app.route('/check-5g', methods=['POST'])
def check_5g():
    py_dict = {'5g_check':1}
    message = base64.b64encode(json.dumps(py_dict).encode('utf-8')).decode('utf-8')
    mqtt.publish('/mqtt/downlink/2cf7f120323086aa',json.dumps({"confirmed": False, "fport": 85, "data": message}))
    # console_messages.append(f'<{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}> Checking 5G connection..')
    # check_length(console_messages)
    return redirect('/')

@app.route('/upload5g_whole_request', methods=['POST'])
def request_whole_file_5g():
    
    data = request.get_json()
    if 'delete' in data:
        try:
            delete = data['delete']

            py_dict = {'5g_send_whole':1,'delete':delete}
            message = base64.b64encode(json.dumps(py_dict).encode('utf-8')).decode('utf-8')
            mqtt.publish('/mqtt/downlink/2cf7f120323086aa',json.dumps({"confirmed": False, "fport": 85, "data": message}))

            return 200
        
        except ValueError as e:
            return 400
    else:
        return 400
    

@app.route('/upload5g_part_request', methods=['POST'])
def request_part_file_5g():
    data = request.get_json()
    if 'start_date' in data and 'end_date' in data and 'delete' in data:
        try:
            start_date = str(datetime.strptime(data['start_date'], '%Y-%m-%d'))
            end_date = str(datetime.strptime(data['end_date'], '%Y-%m-%d'))
            delete = data['delete']

            py_dict = {'5g_send_part':1,'start':start_date,'end':end_date,'delete':delete}
            message = base64.b64encode(json.dumps(py_dict).encode('utf-8')).decode('utf-8')
            mqtt.publish('/mqtt/downlink/2cf7f120323086aa',json.dumps({"confirmed": False, "fport": 85, "data": message}))
            return 200
        except ValueError as e:
            return 400
    else:
        return 400





## Nie zmieniać
@mqtt.on_connect()
def handle_connect(client, userdata, flags, rc):
    mqtt.subscribe('/mqtt/uplink') 
    mqtt.subscribe('/mqtt/join') 


@app.route('/',methods=['POST','GET'])
def index():
    return 'Hello world'


# Funkcja do zmiany interwalu - nie zmieniac
@app.route('/interval_change',methods=['POST'])
def change_interval():
    data = request.get_json()
    if 'interval' in data and isinstance(data['number'], int):
        interval = data['interval']
        py_dict = {"interval":interval}
        message = base64.b64encode(json.dumps(py_dict).encode('utf-8')).decode('utf-8')
        mqtt.publish('/mqtt/downlink/2cf7f120323086aa',json.dumps({"confirmed": False, "fport": 85, "data": message}))
        return 200
    else:
        return 400

#####
##### W tym juz lepiej nic nie ruszac powinno byc git
#####
@mqtt.on_message()
def handle_message(client, userdata, message):    
    try:
        message = json.loads(message.payload.decode())["data"]
        message = base64.b64decode(message).decode('utf-8')
        data_parts = message.split(',')
        message = message[2:]
        sign=data_parts[0]
        if sign == 'M':
            timestamp = data_parts[1]
            latitude_str = data_parts[2]
            longitude_str = data_parts[3]
            memory_status = data_parts[4]
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
                longitude=0
            

            data = Data(
                timestamp=timestamp,
                latitude=latitude,
                longitude=longitude,
                memory_status=memory_status
            )
            db.session.add(data)
            db.session.commit()
            message = f'<{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}> Data received via LoraWAN: latitude - {latitude}, longitude - {longitude}, memory status - {memory_status}'


        
        elif sign=='I':
            interval = data_parts[1]
            message = f"<{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}> Interval change confirmed - interval: {interval}"

        elif sign=='P':
            connection = data_parts[1]
            if connection == '1':
                message = f"5G connection is available"
            else:
                message = f"5G connection is no longer available"

        elif sign=='G':
            connection = data_parts[1]
            if connection == '1':
                message = f"Data was sent sucessfully"
            else:
                message = f"Cannot send data"

        elif sign=='B':
            connection = data_parts[1]
            if connection == '1':
                message = f"WiFi is now on"
            else:
                message = f"WiFi is now off"

            
    except KeyError:
        message = "Device connected succesfully"
    
    socketIO.emit('console_message',{'message':message})
    

if __name__ == '__main__':
    socketIO.run(app,host='0.0.0.0',debug=True)