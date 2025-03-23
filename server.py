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
        </head>
        <body>
            <h1>Control Relay</h1>
            <form method="POST" action="/send_message">
                <button type="submit">Turn ON</button>
            </form>
            <div id="indicator"></div>
        </body>
    </html>
    """
    return render_template_string(html)

@app.route('/send_message', methods=['POST'])
def send_message():
    # Отправляем сообщение "ON" на MQTT топик
    client.publish(MQTT_TOPIC_CONTROL, "ON")
    return "<h1>Message sent: ON</h1>"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
