import network
import socket
import time
from machine import Pin

# Подключение к Wi-Fi
ssid = "YOUR_WIFI_SSID"
password = "YOUR_WIFI_PASSWORD"

led = Pin(15, Pin.OUT)  # Подключаем LED на GPIO 15

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(ssid, password)

while not wlan.isconnected():
    time.sleep(0.5)

print("Connected to WiFi:", wlan.ifconfig())

# WebSocket сервер
def start_websocket_server():
    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    s = socket.socket()
    s.bind(addr)
    s.listen(5)

    print("WebSocket server running...")
    while True:
        conn, addr = s.accept()
        print("Client connected:", addr)
        
        while True:
            try:
                data = conn.recv(1024).decode()
                if "LED_ON" in data:
                    led.value(1)
                    conn.send("LED_ON")
                elif "LED_OFF" in data:
                    led.value(0)
                    conn.send("LED_OFF")
            except:
                break
        
        conn.close()

start_websocket_server()
