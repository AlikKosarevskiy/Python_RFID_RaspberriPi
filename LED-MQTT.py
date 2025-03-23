from machine import Pin
import network
import time
from umqtt.simple import MQTTClient

# Настройки Wi-Fi
SSID = "YII2"
PASSWORD = "69134883"

# Настройки MQTT
MQTT_BROKER = "192.168.1.100"  # IP брокера
MQTT_CLIENT_ID = "pico_relay"
TOPIC_CONTROL = b"/relay/control"
TOPIC_STATUS = b"/relay/status"

# Инициализация Wi-Fi
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(SSID, PASSWORD)

while not wlan.isconnected():
    print("Connecting to WiFi...")
    time.sleep(1)
print("Connected! IP:", wlan.ifconfig()[0])

# Инициализация пинов
relay = Pin(16, Pin.OUT)
relay.value(1)
led = Pin("LED", Pin.OUT)

# Функция для обработки сообщений MQTT
def mqtt_callback(topic, msg):
    global relay, led
    if msg == b"ON":
        relay.value(0)
        led.value(1)
        client.publish(TOPIC_STATUS, "Relay is ON, LED is ON")
        time.sleep(3)
        led.value(0)
        client.publish(TOPIC_STATUS, "Relay is ON, LED is OFF")
    elif msg == b"OFF":
        relay.value(1)
        led.value(0)
        client.publish(TOPIC_STATUS, "Relay is OFF, LED is OFF")

# Подключение к MQTT
client = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER)
client.set_callback(mqtt_callback)
client.connect()
client.subscribe(TOPIC_CONTROL)
print("Connected to MQTT Broker")

while True:
    try:
        client.check_msg()
        time.sleep(1)
    except Exception as e:
        print("Error:", e)
        time.sleep(5)
