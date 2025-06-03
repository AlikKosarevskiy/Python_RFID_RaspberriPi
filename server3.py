from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit
import paho.mqtt.client as mqtt
import threading

app = Flask(__name__)
socketio = SocketIO(app)

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC_CONTROL = "/relay/control"
MQTT_TOPIC_STATUS = "/relay/status"

relay_status = "OFF"

client = mqtt.Client()

def on_message(client, userdata, msg):
    global relay_status
    if msg.topic == MQTT_TOPIC_STATUS:
        relay_status = msg.payload.decode()
        socketio.emit('status_update', {'status': relay_status})

client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.on_message = on_message
client.subscribe(MQTT_TOPIC_STATUS)

def mqtt_loop():
    client.loop_start()

mqtt_thread = threading.Thread(target=mqtt_loop)
mqtt_thread.daemon = True
mqtt_thread.start()

@socketio.on('connect')
def handle_connect():
    # При подключении клиента отправляем текущее состояние
    emit('status_update', {'status': relay_status})

@app.route('/')
def index():
    html = f"""
    <html>
    <head>
        <title>MQTT Button</title>
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
                if (data.status == 'ON') {{
                    indicator.style.backgroundColor = 'green';
                }} else {{
                    indicator.style.backgroundColor = 'red';
                }}

                // Вывод сообщения в лог
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
                    if (response.ok && msg == 'ON') {{
                        document.getElementById("indicator").style.backgroundColor = 'green';
                    }} else if (response.ok && msg == 'OFF') {{
                        document.getElementById("indicator").style.backgroundColor = 'red';
                    }}
                }});
            }}
        </script>
    </head>
    <body>
        <h1>Control Relay</h1>
        <button onclick="sendMessage('ON')">Turn ON</button>
        <button onclick="sendMessage('OFF')">Turn OFF</button>
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
    message = data.get('message', 'ON')
    client.publish(MQTT_TOPIC_CONTROL, message)
    return '', 200

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
