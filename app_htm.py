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
        # Включаем LED и сразу меняем индикацию на веб-странице
        GPIO.output(LED_PIN, GPIO.HIGH)
        state = True
        # Ждем 5 секунд, затем выключаем
        time.sleep(5)
        GPIO.output(LED_PIN, GPIO.LOW)
        state = False
    return jsonify({'state': state})

@app.route('/turn_off', methods=['POST'])
def turn_off():
    # Немедленно выключаем LED и обновляем состояние
    GPIO.output(LED_PIN, GPIO.LOW)
    return jsonify({'state': False})

if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=5000, debug=True)
    finally:
        GPIO.cleanup()
