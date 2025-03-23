from flask import Flask, render_template_string
import paho.mqtt.client as mqtt

app = Flask(__name__)

# Настройки MQTT
MQTT_BROKER = "localhost"  # Адрес MQTT брокера
MQTT_PORT = 1883           # Порт MQTT
MQTT_TOPIC_CONTROL = "/relay/control"  # Тема для отправки сообщений
MQTT_TOPIC_STATUS = "/relay/status"    # Тема для получения статуса реле

# Переменная для хранения статуса реле
relay_status = "OFF"

# Создаем MQTT клиента
client = mqtt.Client()

# Функция для обработки сообщений MQTT
def on_message(client, userdata, msg):
    global relay_status
    if msg.topic == MQTT_TOPIC_STATUS:
        relay_status = msg.payload.decode()

# Подключение к MQTT брокеру
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.on_message = on_message
client.subscribe(MQTT_TOPIC_STATUS)

# Запускаем MQTT клиент в отдельном потоке
import threading
def mqtt_loop():
    client.loop_start()

mqtt_thread = threading.Thread(target=mqtt_loop)
mqtt_thread.daemon = True
mqtt_thread.start()

@app.route('/')
def index():
    # HTML-страница с кнопкой и индикатором
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
            <script>
                function sendMessage() {{
                    fetch('/send_message', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json',
                        }},
                        body: JSON.stringify({{ message: 'ON' }})
                    }}).then(response => {{
                        if (response.ok) {{
                            document.getElementById("indicator").style.backgroundColor = 'green'; // Обновить индикатор
                        }}
                    }});
                }}
            </script>
        </head>
        <body>
            <h1>Control Relay</h1>
            <button onclick="sendMessage()">Turn ON</button>
            <div id="indicator"></div>
        </body>
    </html>
    """
    return render_template_string(html)

@app.route('/send_message', methods=['POST'])
def send_message():
    # Получаем сообщение из тела запроса (для дальнейшей обработки можно использовать)
    client.publish(MQTT_TOPIC_CONTROL, "ON")
    return '', 200  # Возвращаем пустой ответ, чтобы избежать перехода

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
