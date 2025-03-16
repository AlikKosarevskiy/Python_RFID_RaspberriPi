import network
import socket
from machine import Pin
import time

# Wi-Fi credentials
SSID = "YOUR_WIFI_SSID"
PASSWORD = "YOUR_WIFI_PASSWORD"

# Connect to Wi-Fi
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(SSID, PASSWORD)

print("Connecting to WiFi...", end="")
timeout = 10
while not wlan.isconnected() and timeout > 0:
    print(".", end="")
    time.sleep(1)
    timeout -= 1

if wlan.isconnected():
    print("\nConnected! IP:", wlan.ifconfig()[0])
else:
    print("\n❌ Failed to connect. Check your WiFi settings.")
    raise SystemExit()

# Get IP address
ip = wlan.ifconfig()[0]
print(f"Web server running on http://{ip}")

# Set up LED
led = Pin("LED", Pin.OUT)

# HTML page with LED status
html = """<!DOCTYPE html>
<html>
<head>
    <title>Pico W LED Control</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; margin: 50px; }
        button { font-size: 20px; padding: 10px 20px; margin: 10px; cursor: pointer; }
        #status { font-size: 24px; font-weight: bold; margin-top: 20px; }
        .on { color: green; }
        .off { color: red; }
    </style>
    <script>
        function toggleLED(state) {
            fetch('/' + state);
            updateStatus();
        }
        function updateStatus() {
            fetch('/status').then(response => response.text()).then(status => {
                let statusElement = document.getElementById("status");
                statusElement.innerText = "LED is " + (status === "1" ? "ON" : "OFF");
                statusElement.className = status === "1" ? "on" : "off";
            });
        }
        setInterval(updateStatus, 1000);  // Refresh LED status every second
    </script>
</head>
<body onload="updateStatus()">
    <h1>Raspberry Pi Pico W Web Server</h1>
    <p>Click the button to toggle the LED.</p>
    <button onclick="toggleLED('on')">Turn ON</button>
    <button onclick="toggleLED('off')">Turn OFF</button>
    <p id="status" class="off">LED is OFF</p>
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

        # Handle LED control requests
        if "GET /on" in request:
            led.value(1)
        elif "GET /off" in request:
            led.value(0)

        # Handle LED status request
        if "GET /status" in request:
            response = "1" if led.value() else "0"
            conn.send("HTTP/1.1 200 OK\nContent-Type: text/plain\n\n" + response)
            conn.close()
            continue

        # Send main HTML page
        conn.send("HTTP/1.1 200 OK\nContent-Type: text/html\n\n")
        conn.send(html)
        conn.close()

# Run the server
web_server()
