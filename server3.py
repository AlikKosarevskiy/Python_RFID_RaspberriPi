from flask import Flask, request, render_template_string
from flask_socketio import SocketIO, emit
import paho.mqtt.client as mqtt
import threading

app = Flask(__name__)
socketio = SocketIO(app)

# Настройки MQTT
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC_CONTROL = "/relay/control"
MQTT_TOPIC_STATUS = "/relay/status"

# Переменная для хранения статуса реле
relay_status = "OFF"

# Создаем MQTT клиента
client = mqtt.Client()

def on_message(client, userdata, msg):
    global relay_status
    if msg.topic == MQTT_TOPIC_STATUS:
        relay_status = msg.payload.decode()
        socketio.emit('status_update', {'status': relay_status})

# Подключение MQTT
client.on_message = on_message
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.subscribe(MQTT_TOPIC_STATUS)

def mqtt_loop():
    client.loop_start()

mqtt_thread = threading.Thread(target=mqtt_loop)
mqtt_thread.daemon = True
mqtt_thread.start()

@app.route('/')
def index():
    indicator_color = "green" if relay_status == "ON" else "red"
    html = f"""
    <html>
        <head>
            <title>MQTT Control</title>
            <style>
                #indicator {{
                    width: 50px;
                    height: 50px;
                    border-radius: 50%;
                    background-color: {indicator_color};
                    margin-top: 20px;
                }}
                #log {{
                    margin-top: 20px;
                    border: 1px solid #ccc;
                    padding: 10px;
                    width: 300px;
                    height: 150px;
                    overflow-y: auto;
                    background: #f9f9f9;
                    font-family: monospace;
                    font-size: 14px;
                }}
            </style>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.min.js"></script>
            <script>
                var socket = io();

                socket.on('status_update', function(data) {{
                    var indicator = document.getElementById('indicator');
                    if (data.status === 'ON') {{
                        indicator.style.backgroundColor = 'green';
                    }} else {{
                        indicator.style.backgroundColor = 'red';
                    }}

                    var log = document.getElementById('log');
                    var line = document.createElement('div');
                    line.textContent = "MQTT: " + data.status + " (" + new Date().toLocaleTimeString() + ")";
                    log.appendChild(line);
                    log.scrollTop = log.scrollHeight;
                }});

                function sendMessage(msg) {{
                    fetch('/send_message', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json',
                        }},
                        body: JSON.stringify({{ message: msg }})
                    }}).then(response => {{
                        if (response.ok && msg === 'ON') {{
                            document.getElementById("indicator").style.backgroundColor = 'green';
                        }} else if (response.ok && msg === 'OFF') {{
                            document.getElementById("indicator").style.backgroundColor = 'red';
                        }}
                    }});
                }}
            </script>
        </head>
        <body>
            <h1>Управление Реле</h1>
            <button onclick="sendMessage('ON')">Включить</button>
            <button onclick="sendMessage('OFF')">Выключить</button>
            <div id="indicator"></div>
            <h3>Последние сообщения MQTT:</h3>
            <div id="log"></div>
        </body>
    </html>
    """
    return render_template_string(html)

@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.get_json()
    msg = data.get("message")
    if msg in ["ON", "OFF"]:
        client.publish(MQTT_TOPIC_CONTROL, msg)
        return '', 200
    return 'Invalid message', 400

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
