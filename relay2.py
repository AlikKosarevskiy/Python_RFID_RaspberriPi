from machine import Pin
import network
import socket
import time

relay = Pin(16, Pin.OUT)
relay.value(1)
relayState = "Relay is OFF"
ledState = "LED is OFF"

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
      <style>
         html { font-family: Arial; display: inline-block; margin: 0px auto; text-align: center; }
         h1 { font-family: Arial; color: #2551cc; }
         .button1 { border-radius: 28px; font-family: Arial; color: #ffffff; font-size: 30px; background: #2ba615; padding: 10px 20px; text-decoration: none; }
         .button2 { border-radius: 28px; font-family: Arial; color: #ffffff; font-size: 30px; background: #f52e45; padding: 10px 20px; text-decoration: none; }
      </style>
   </head>
   <body>
      <h1>Pico Relay Control Web Server</h1>
      <p>%s</p>
      <p>%s</p>
      <p><a href="/relay/on"><button class="button1">ON</button></a></p>
      <p><a href="/relay/off"><button class="button2">OFF</button></a></p>
   </body>
</html>
"""

# Wait for connection or fail
max_wait = 10
while max_wait > 0:
    if wlan.status() < 0 or wlan.status() >= 3:
        break
    max_wait -= 1
    print('waiting for connection...')
    time.sleep(1)

# Handle connection error
if wlan.status() != 3:
    raise RuntimeError('network connection failed')
else:
    print('connected')
    status = wlan.ifconfig()
    print('ip = ' + status[0])
    for i in range(6):
        led.toggle()
        time.sleep_ms(200)

addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
s = socket.socket()
s.bind(addr)
s.listen(1)
print('listening on', addr)

while True:
    try:
        cl, addr = s.accept()
        print('client connected from', addr)
        request = cl.recv(1024)
        print(request)

        request = str(request)
        relay_on = request.find('/relay/on')
        relay_off = request.find('/relay/off')
        print('relay on = ' + str(relay_on))
        print('relay off = ' + str(relay_off))

        if relay_on == 6:
            print("relay on")
            relay.value(0)
            led.value(1)
            relayState = "Relay is ON"
            ledState = "LED is ON"
            response = html % (relayState, ledState)
            cl.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
            cl.send(response)
            cl.close()
            time.sleep(3)  # Держим LED включенным 3 секунды
            led.value(0)  # Выключаем LED
            ledState = "LED is OFF"

        if relay_off == 6:
            print("relay off")
            relay.value(1)
            led.value(0)
            relayState = "Relay is OFF"
            ledState = "LED is OFF"
        
        response = html % (relayState, ledState)
        cl.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
        cl.send(response)
        cl.close()

    except OSError as e:
        cl.close()
        print('connection closed')
