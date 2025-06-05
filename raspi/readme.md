Create ne folder /raspi
# T-Relay Project

Управление ESP32 реле через Flask + MQTT (Raspberry Pi).

## 📂 Структура
- `raspi/` — код Flask сервера на Raspberry Pi
- `esp32/` — прошивка реле на ESP32
- `config/` — конфигурации (например Mosquitto)
- `archive/` — старые версии файлов

## 📡 MQTT
- Контроль: `/relay/control/` — принимает `ON` или `OFF`
- Статус: `/relay/status` — получает `ON` или `OFF`

## 🔧 Запуск Flask
```bash
cd raspi
pip install -r requirements.txt
python app.py
