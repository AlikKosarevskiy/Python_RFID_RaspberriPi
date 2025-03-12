from flask import Flask, render_template, jsonify
import RPi.GPIO as GPIO
import time
import threading  # Для выполнения функции с задержкой в отдельном потоке

# Настройки GPIO
LED_PIN = 17
GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_PIN, GPIO.OUT)

# Создание веб-приложения Flask
app = Flask(__name__)

# Функция для задержки 5 секунд и выключения LED
def turn_off_after_delay():
    time.sleep(5)
    GPIO.output(LED_PIN, GPIO.LOW)

@app.route('/')
def home():
    state = GPIO.input(LED_PIN)
    return render_template('index.html', state=state)

@app.route('/toggle', methods=['POST'])
def toggle():
    state = GPIO.input(LED_PIN)
    if not state:
        # Включаем LED
        GPIO.output(LED_PIN, GPIO.HIGH)
        state = True
        # Запускаем функцию для выключения через 5 секунд
        threading.Thread(target=turn_off_after_delay).start()
        return jsonify({'state': state})
    else:
        # Выключаем LED, если он уже включен
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
