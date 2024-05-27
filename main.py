from flask import Flask, render_template,request,redirect
from flask_mqtt import Mqtt
import json
import base64
from datetime import datetime
import pandas as pd
from flask_sqlalchemy import SQLAlchemy




app = Flask(__name__)


## Nie ruszać
app.config['MQTT_BROKER_URL'] = 'localhost'  # Adres brokera MQTT
app.config['MQTT_BROKER_PORT'] = 1883        # Port brokera MQTT
app.config['MQTT_KEEPALIVE'] = 60
app.config['MQTT_TLS_ENABLED'] = False

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://root:APP@153.19.55.87/database'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)




# Zostawić
mqtt = Mqtt(app)



## Modele do zmiany na format dla PostgreSQL
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
    
    





#Nie zmieniać nazwy endpointu, zmienić zapisywanie danych na PostrgreSQL
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
    py_dict = {'5g_send_whole':1}
    message = base64.b64encode(json.dumps(py_dict).encode('utf-8')).decode('utf-8')
    mqtt.publish('/mqtt/downlink/2cf7f120323086aa',json.dumps({"confirmed": False, "fport": 85, "data": message}))
    #console_messages.append(f'<{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}> Requesting 5G send whole file')

    return redirect('/')

@app.route('/upload5g_part_request', methods=['POST'])
def request_part_file_5g():
    start_date = request.form['start_date']
    end_date = request.form['end_date']

    start_datetime = str(datetime.strptime(start_date, "%Y-%m-%d"))
    end_datetime = str(datetime.strptime(end_date, "%Y-%m-%d"))

    py_dict = {'5g_send_part':1,'start':start_datetime,'end':end_datetime}
    message = base64.b64encode(json.dumps(py_dict).encode('utf-8')).decode('utf-8')
    mqtt.publish('/mqtt/downlink/2cf7f120323086aa',json.dumps({"confirmed": False, "fport": 85, "data": message}))
    #console_messages.append(f'<{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}> Requesting 5G send part file {start_datetime}-{end_datetime}')
    
    return redirect('/')



### Cała logika z wifi do wywalenia - będzie nowa
@app.route('/check-wifi', methods=['POST'])
def check_wifi():
    py_dict = {'wifi_check':1}
    message = base64.b64encode(json.dumps(py_dict).encode('utf-8')).decode('utf-8')
    mqtt.publish('/mqtt/downlink/2cf7f120323086aa',json.dumps({"confirmed": False, "fport": 85, "data": message}))
    #console_messages.append(f'<{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}> Checking WiFi connection..')

    return redirect('/')

@app.route('/uploadwifi_whole_request', methods=['POST'])
def request_whole_file_wifi():
    py_dict = {'wifi_send_whole':1}
    message = base64.b64encode(json.dumps(py_dict).encode('utf-8')).decode('utf-8')
    mqtt.publish('/mqtt/downlink/2cf7f120323086aa',json.dumps({"confirmed": False, "fport": 85, "data": message}))
    #console_messages.append(f'<{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}> Requesting WiFi send whole file')

    return redirect('/')


@app.route('/uploadwifi_part_request', methods=['POST'])
def request_part_file_wifi():
    start_date = request.form['start_date']
    end_date = request.form['end_date']

    start_datetime = str(datetime.strptime(start_date, "%Y-%m-%d"))
    end_datetime = str(datetime.strptime(end_date, "%Y-%m-%d"))

    py_dict = {'wifi_send_part':1,'start':start_datetime,'end':end_datetime}
    message = base64.b64encode(json.dumps(py_dict).encode('utf-8')).decode('utf-8')
    mqtt.publish('/mqtt/downlink/2cf7f120323086aa',json.dumps({"confirmed": False, "fport": 85, "data": message}))
    #console_messages.append(f'<{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}> Requesting WiFi send part file {start_datetime}-{end_datetime}')
   
    return redirect('/')

    
### Całe do wywalenia, główna strona będzie po stronie frontendu, zostanie tylko wiadomosc do plawy do zmiany interwału wiec na razie nie usuwac zeby sie nie zgubilo 
# @app.route('/',methods=['POST','GET'])
# def index():
#     global queued_message
#     if request.method=="POST":
#         interval = float(request.form.get('interval'))
#         py_dict = {"interval":interval}
#         message = base64.b64encode(json.dumps(py_dict).encode('utf-8')).decode('utf-8')
#         mqtt.publish('/mqtt/downlink/2cf7f120323086aa',json.dumps({"confirmed": False, "fport": 85, "data": message}))
#         queued_message = request.form.get("interval")
#         console_messages.append(f'<{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}> Queued message: {request.form.get("interval")}')
#         check_length(console_messages)
#         return render_template('index.html',messages = console_messages, queued_message = queued_message)
#     return render_template('index.html',messages = console_messages,queued_message = queued_message)



## Nie zmieniać
@mqtt.on_connect()
def handle_connect(client, userdata, flags, rc):
    mqtt.subscribe('/mqtt/uplink') 
    mqtt.subscribe('/mqtt/join') 



#####
##### W tym wazne zeby nie ruszac nic poza fragmentami gdzie jest napisane ze mozna
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
            

            #Zapisywanie danych z LoraWan do bazy danych - trzeba zmienic na PostgreSQL
            data = Data(
                timestamp=timestamp,
                latitude=latitude,
                longitude=longitude,
                memory_status=memory_status
            )
            db.session.add(data)
            db.session.commit()
            ####


        ### W tych ifach do zmiany jest logika z message, tutaj trzeba bedzie dawac znac frontendowi ze cos przyszlo - do ustalenia jak to zrobic i co z tym bedzie sie dzialo po stronie frontendu
        elif sign=='I':
            interval = data_parts[1]
            message = f"Interval changed confirmed - interval: {interval}"

        elif sign=='P':
            connection = data_parts[1]
            if connection == '1':
                message = f"5G connection confirmed"
            else:
                message = f"5G connection refused"

        elif sign=='G':
            connection = data_parts[1]
            if connection == '1':
                message = f"Whole file sent (5G)"
            else:
                message = f"Cannot send file"
        
        elif sign=='A':
            connection = data_parts[1]
            if connection == '1':
                message = f"Part of file sent (5G)"
            else:
                message = f"Cannot send file"

        elif sign=='B':
            connection = data_parts[1]
            if connection == '1':
                message = f"WiFi connection confirmed"
            else:
                message = f"Wifi connection refused"

        elif sign=='C':
            connection = data_parts[1]
            if connection == '1':
                message = f"Whole file sent (Wifi)"
            else:
                message = f"Cannot send file"
        
        elif sign=='D':
            connection = data_parts[1]
            if connection == '1':
                message = f"Part of file sent (WiFi)"
            else:
                message = f"Cannot send file"

            
    except KeyError:
        message = "Device connected succesfully"
    

    

if __name__ == '__main__':
    app.run(host='0.0.0.0',debug=True)