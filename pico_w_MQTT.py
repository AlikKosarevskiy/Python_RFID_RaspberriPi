import network
import time
import machine
from umqtt.simple import MQTTClient

# Настройки WiFi
SSID = "YOUR_WIFI_SSID"
PASSWORD = "YOUR_WIFI_PASSWORD"

# MQTT брокер (можно использовать локальный Mosquitto или cloud-брокеры)
MQTT_BROKER = "192.168.1.100"  # IP твоего MQTT брокера
TOPIC_CONTROL = "led_control"
TOPIC_STATUS = "led_status"

# Настройки WiFi
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(SSID, PASSWORD)

while not wlan.isconnected():
    time.sleep(0.5)

print("Connected to WiFi")

# Настройки MQTT
client = MQTTClient("pico", MQTT_BROKER)
led = machine.Pin(15, machine.Pin.OUT)

def sub_cb(topic, msg):
    if topic == b"led_control":
        if msg == b"on":
            led.value(1)
            client.publish(TOPIC_STATUS, "ON")
        elif msg == b"off":
            led.value(0)
            client.publish(TOPIC_STATUS, "OFF")

client.set_callback(sub_cb)
client.connect()
client.subscribe(TOPIC_CONTROL)

print("Connected to MQTT Broker")

while True:
    client.check_msg()  # Ожидаем сообщения
    time.sleep(0.1)  # Минимальная задержка
