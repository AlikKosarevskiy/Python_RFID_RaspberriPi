from flask import Flask, render_template_string
import paho.mqtt.client as mqtt

app = Flask(__name__)

# Настройки MQTT
MQTT_BROKER = "localhost"  # Адрес MQTT брокера
MQTT_PORT = 1883           # Порт MQTT
MQTT_TOPIC = "/relay/control"  # Тема для отправки сообщений

# Создаем MQTT клиента
client = mqtt.Client()

# Подключение к MQTT брокеру
client.connect(MQTT_BROKER, MQTT_PORT, 60)

@app.route('/')
def index():
    # HTML-страница с кнопкой
    html = """
    <html>
        <head>
            <title>MQTT Button</title>
        </head>
        <body>
            <h1>Control Relay</h1>
            <form method="POST" action="/send_message">
                <button type="submit">Turn ON</button>
            </form>
        </body>
    </html>
    """
    return render_template_string(html)

@app.route('/send_message', methods=['POST'])
def send_message():
    # Отправляем сообщение "ON" на MQTT топик
    client.publish(MQTT_TOPIC, "ON")
    return "<h1>Message sent: ON</h1>"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
