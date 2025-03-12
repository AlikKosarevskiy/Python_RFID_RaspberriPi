from flask import Flask  
import RPi.GPIO as GPIO  

# Настройки GPIO  
LED_PIN = 17  
GPIO.setmode(GPIO.BCM)  
GPIO.setup(LED_PIN, GPIO.OUT)  

# Создание веб-приложения Flask  
app = Flask(__name__)  

@app.route('/')  
def home():  
    return '''  
    <h1>Управление LED на Raspberry Pi</h1>  
    <p><a href="/on"><button>Включить</button></a></p>  
    <p><a href="/off"><button>Выключить</button></a></p>  
    '''  

@app.route('/on')  
def turn_on():  
    GPIO.output(LED_PIN, GPIO.HIGH)  
    return "LED включен! <br><a href='/'>Назад</a>"  

@app.route('/off')  
def turn_off():  
    GPIO.output(LED_PIN, GPIO.LOW)  
    return "LED выключен! <br><a href='/'>Назад</a>"  

if __name__ == '__main__':  
    try:  
        app.run(host='0.0.0.0', port=5000)  
    finally:  
        GPIO.cleanup()  # Очистка GPIO при завершении работы  
