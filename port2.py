from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit
import paho.mqtt.client as mqtt

app = Flask(__name__)
socketio = SocketIO(app)

# Настройки MQTT
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

import threading
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
            <title>MQTT Button</title>
            <style>
                #indicator {{
                    width: 50px;
                    height: 50px;
                    border-radius: 50%;
                    background-color: {indicator_color};
                    margin-top: 20px;
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
                }});

                function sendMessage(command) {{
                    fetch('/send_message', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json',
                        }},
                        body: JSON.stringify({{ message: command }})
                    }});
                }}
            </script>
        </head>
        <body>
            <h1>Control Relay</h1>
            <button onclick="sendMessage('ON')">Turn ON</button>
            <button onclick="sendMessage('OFF')">Turn OFF</button>
            <div id="indicator"></div>
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
    app.run(host='0.0.0.0', port=5000)
