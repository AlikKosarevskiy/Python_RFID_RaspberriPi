import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)  # Используем BCM-нумерацию
GPIO.setup(17, GPIO.OUT)  # Указываем, что GPIO 17 — выход

GPIO.output(17, GPIO.HIGH)  # Включаем LED
time.sleep(3)  # Ждем 3 секунды
GPIO.output(17, GPIO.LOW)   # Выключаем LED

GPIO.cleanup()  # Очищаем настройки
