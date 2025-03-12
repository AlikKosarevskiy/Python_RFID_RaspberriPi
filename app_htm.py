from flask import Flask, render_template, jsonify
import RPi.GPIO as GPIO
import time  # Для задержки

# Настройки GPIO
LED_PIN = 17
GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_PIN, GPIO.OUT)

# Создание веб-приложения Flask
app = Flask(__name__)

@app.route('/')
def home():
    state = GPIO.input(LED_PIN)
    return render_template('index.html', state=state)

@app.route('/toggle', methods=['POST'])
def toggle():
    state = GPIO.input(LED_PIN)
    if not state:
        GPIO.output(LED_PIN, GPIO.HIGH)  # Включаем LED
        time.sleep(5)  # Ждем 5 секунд
        GPIO.output(LED_PIN, GPIO.LOW)  # Выключаем LED
        state = False  # Обновляем состояние после задержки
    return jsonify({'state': state})  # Отправляем новое состояние в JS

if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=5000, debug=True)
    finally:
        GPIO.cleanup()
