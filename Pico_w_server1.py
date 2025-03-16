import network
import socket
from machine import Pin

# Wi-Fi credentials
SSID = "YOUR_WIFI_SSID"
PASSWORD = "YOUR_WIFI_PASSWORD"

# Connect to Wi-Fi
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(SSID, PASSWORD)

print("Connecting to WiFi...", end="")
while not wlan.isconnected():
    pass  # Wait for connection
print(" Connected!")

# Get IP address
ip = wlan.ifconfig()[0]
print(f"Web server running on http://{ip}")

# Set up LED (for Pico W, "LED" is the correct pin name)
led = Pin("LED", Pin.OUT)

# HTML page
html = """<!DOCTYPE html>
<html>
<head>
    <title>Pico W LED Control</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; margin: 50px; }
        button { font-size: 20px; padding: 10px 20px; margin: 10px; cursor: pointer; }
    </style>
</head>
<body>
    <h1>Raspberry Pi Pico W Web Server</h1>
    <p>Click the button to toggle the LED.</p>
    <button onclick="fetch('/on')">Turn ON</button>
    <button onclick="fetch('/off')">Turn OFF</button>
</body>
</html>
"""

# Create a simple web server
def web_server():
    addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
    s = socket.socket()
    s.bind(addr)
    s.listen(5)
    print("Waiting for connections...")

    while True:
        conn, addr = s.accept()
        print("Client connected from", addr)
        request = conn.recv(1024).decode()

        # Control LED based on request
        if "GET /on" in request:
            led.value(1)
        elif "GET /off" in request:
            led.value(0)

        # Send response
        conn.send("HTTP/1.1 200 OK\nContent-Type: text/html\n\n")
        conn.send(html)
        conn.close()

# Run the server
web_server()
