from machine import Pin
import network
import socket
import time

relay = Pin(16, Pin.OUT)
relay.value(1)

led = Pin("LED", Pin.OUT)

ssid = 'YII2'
password = '69134883'

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(ssid, password)

html = """<!DOCTYPE html>
<html>
   <head>
      <title>Pico Relay Control Web Server</title>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <script>
         function updateStatus() {
            var xhr = new XMLHttpRequest();
            xhr.onreadystatechange = function() {
               if (xhr.readyState == 4 && xhr.status == 200) {
                  document.getElementById("status").innerHTML = xhr.responseText;
               }
            };
            xhr.open("GET", "/status", true);
            xhr.send();
         }
         setInterval(updateStatus, 1000);
      </script>
      <style>
         html { font-family: Arial; text-align: center; }
         h1 { color: #2551cc; }
         .button1 { border-radius: 28px; color: #ffffff; font-size: 30px; background: #2ba615; padding: 10px 20px; text-decoration: none; }
         .button2 { border-radius: 28px; color: #ffffff; font-size: 30px; background: #f52e45; padding: 10px 20px; text-decoration: none; }
      </style>
   </head>
   <body>
      <h1>Pico Relay Control Web Server</h1>
      <p id="status">Loading...</p>
      <p><a href="/relay/on"><button class="button1">ON</button></a></p>
      <p><a href="/relay/off"><button class="button2">OFF</button></a></p>
   </body>
</html>
"""

ledState = "LED is OFF"
relayState = "Relay is OFF"

# Ожидание подключения
max_wait = 10
while max_wait > 0:
    if wlan.status() < 0 or wlan.status() >= 3:
        break
    max_wait -= 1
    print('waiting for connection...')
    time.sleep(1)

if wlan.status() != 3:
    raise RuntimeError('network connection failed')
else:
    print('connected')
    print('IP =', wlan.ifconfig()[0])

addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
s = socket.socket()
s.bind(addr)
s.listen(1)
print('Listening on', addr)

while True:
    try:
        cl, addr = s.accept()
        request = cl.recv(1024).decode()
        
        if "/relay/on" in request:
            relay.value(0)
            led.value(1)
            relayState = "Relay is ON"
            ledState = "LED is ON"
            cl.send('HTTP/1.0 303 See Other\r\nLocation: /\r\n\r\n')
            cl.close()
            time.sleep(3)
            led.value(0)
            ledState = "LED is OFF"
        
        elif "/relay/off" in request:
            relay.value(1)
            led.value(0)
            relayState = "Relay is OFF"
            ledState = "LED is OFF"
            cl.send('HTTP/1.0 303 See Other\r\nLocation: /\r\n\r\n')
        
        elif "/status" in request:
            cl.send('HTTP/1.0 200 OK\r\nContent-type: text/plain\r\n\r\n')
            cl.send(f"{relayState}<br>{ledState}")
        
        else:
            cl.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
            cl.send(html)
        
        cl.close()

    except OSError as e:
        cl.close()
        print('connection closed')
