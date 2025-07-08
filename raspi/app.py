from flask import Flask, render_template, request, redirect, url_for, flash  # уже есть render_template
import sqlite3
import threading
import paho.mqtt.client as mqtt
import time # to check double message

# variables to check double message
last_fob = None
last_time = 0
REPEAT_TIMEOUT = 2  # секунды

app = Flask(__name__)

MQTT_BROKER = "192.168.0.110"
MQTT_TOPIC_RFID = "/rfid/id"
MQTT_TOPIC_CONTROL = "/relay/control"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/relay')
def relay():
    return render_template('relay.html')

def get_db_connection():
    conn = sqlite3.connect('rfid.db', timeout=9)  # укажи свой путь к базе
    conn.row_factory = sqlite3.Row
    return conn

# ---------------- MQTT CALLBACK -------------------
def on_connect(client, userdata, flags, rc):
    print("MQTT подключено с кодом:", rc)
    client.subscribe(MQTT_TOPIC_RFID)
    client.subscribe("reset/credits")

def on_message(client, userdata, msg):
    global last_fob, last_time # to check double message

    topic = msg.topic # for reset credit
    payload = msg.payload.decode()
    print(f"[MQTT] Получено: {payload}")

    if topic == "reset/credits" and payload.strip() == "reset":
        print("Получена команда сброса кредитов!")
        reset_all_credits()
        return  # <<< ЭТО ВАЖНО: прекращаем дальнейшую обработку

    try:
        reader_id_str, tag_hex = payload.strip().split(",")
        reader_id = int(reader_id_str)

        now = time.time()
        if payload == last_fob and now - last_time < REPEAT_TIMEOUT:
            print("⚠️ Повторное сообщение проигнорировано")
            return  # игнорируем дубликат

        last_fob = payload
        last_time = now

        conn = get_db_connection()
        
        # Поиск карты
        fob = conn.execute("SELECT * FROM fobs_credits WHERE fob_number = ?", (tag_hex,)).fetchone()
        attraction = conn.execute("SELECT * FROM attractions WHERE reader_id = ?", (reader_id,)).fetchone()

        if fob and attraction:
            cost = attraction['cost']
            duration = attraction['duration']
            current_credits = int(fob['credits'])

            if current_credits >= cost:
                new_credits = current_credits - cost
                conn.execute("UPDATE fobs_credits SET credits = ? WHERE fob_id = ?", (new_credits, fob['fob_id']))
                conn.execute(
                    "INSERT INTO credits_log (fob_id, function, attraction, credits_rest) VALUES (?, ?, ?, ?)",
                    (fob['fob_id'], 'play', f"Atr{reader_id}", new_credits)
                )
                conn.commit()

                # Отправка команды на реле
                command = f"ON:{duration}"
                client.publish(MQTT_TOPIC_CONTROL, command)
                print(f"✅ Доступ разрешен. Отправлено: {command}")
            else:
                print("❌ Недостаточно кредитов")
        else:
            print("❌ Брелок или аттракцион не найден")
        conn.close()
    except Exception as e:
        print("⚠️ Ошибка обработки:", e)

def reset_all_credits():
    #conn = sqlite3.connect("credits.db")
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE fobs_credits SET credits = 10")
    conn.commit()
    conn.close()
    print("Кредиты сброшены до 10 для всех брелков")

# ------------- MQTT Client Thread -------------------
def start_mqtt_listener():
    mqtt_client = mqtt.Client()
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect(MQTT_BROKER, 1883, 60)
    mqtt_client.loop_forever()

# Запуск MQTT клиента в отдельном потоке
threading.Thread(target=start_mqtt_listener, daemon=True).start()

# ------------- Flask Routes (как в твоём коде) --------------
# index, relay, stats, fobs, add_fob, edit_fob, delete_fob
# Оставлены без изменений

@app.route('/stats')
def stats():
    conn = get_db_connection()
    logs = conn.execute('SELECT * FROM credits_log ORDER BY datetime DESC LIMIT 100').fetchall()
    conn.close()
    return render_template('stats.html', logs=logs)

@app.route('/fobs')
def fobs():
    conn = get_db_connection()
    fobs_data = conn.execute('SELECT fob_id, fob_number, credits FROM fobs_credits').fetchall()
    conn.close()
    return render_template('fobs.html', fobs=fobs_data)

@app.route('/add_fob', methods=['GET', 'POST'])
def add_fob():
    if request.method == 'POST':
        fob_number = request.form['fob_number']
        credits = request.form['credits']

        conn = get_db_connection()
#       conn.execute('INSERT INTO fobs_credits (fob_number, credits) VALUES (?, ?)',
#                    (fob_number, credits))
        cursor = conn.execute(
            'INSERT INTO fobs_credits (fob_number, credits) VALUES (?, ?)',
            (fob_number, credits)
        )
        new_id = cursor.lastrowid

        conn.execute(
            'INSERT INTO credits_log (fob_id, function, attraction, credits_rest) VALUES (?, ?, ?, ?)',
            (new_id, 'new', 'admin', credits)
        )
        conn.commit()
        conn.close()
        return redirect(url_for('fobs'))  # Возврат в список карт

    return render_template('add_fob.html')

@app.route('/edit_fob/<int:fob_id>', methods=['GET', 'POST'])
def edit_fob(fob_id):
    conn = get_db_connection()
    fob = conn.execute('SELECT * FROM fobs_credits WHERE fob_id = ?', (fob_id,)).fetchone()

    if not fob:
        conn.close()
        return "Карта не найдена", 404

    if request.method == 'POST':
        new_credits = request.form['credits']
        conn.execute('UPDATE fobs_credits SET credits = ? WHERE fob_id = ?', (new_credits, fob_id))
        conn.execute(
            'INSERT INTO credits_log (fob_id, function, attraction, credits_rest) VALUES (?, ?, ?, ?)',
            (fob_id, 'edit', 'admin', new_credits)
        )
        conn.commit()
        conn.close()
        return redirect(url_for('fobs'))

    conn.close()
    return render_template('edit_fob.html', fob=fob)

@app.route('/delete_fob/<int:fob_id>', methods=['POST'])
def delete_fob(fob_id):
    conn = get_db_connection()
    fob = conn.execute('SELECT * FROM fobs_credits WHERE fob_id = ?', (fob_id,)).fetchone()

    if fob:
        conn.execute(
            'INSERT INTO credits_log (fob_id, function, attraction, credits_rest) VALUES (?, ?, ?, ?)',
            (fob['fob_id'], 'delete', 'admin', fob['credits'])
        )

    conn.execute('DELETE FROM fobs_credits WHERE fob_id = ?', (fob_id,))
#   conn.execute('DELETE FROM fobs_credits WHERE fob_id = ?', (fob_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('fobs'))

@app.route('/attractions', methods=['GET'])
def attractions():
    conn = get_db_connection()
    attractions = conn.execute('SELECT * FROM attractions').fetchall()
    conn.close()
    return render_template('attractions.html', attractions=attractions)


@app.route('/add_attraction', methods=['POST'])
def add_attraction():
    reader_id = request.form['reader_id']
    name = request.form['name']
    cost = request.form['cost']
    duration = request.form['duration']

    conn = get_db_connection()
    conn.execute(
        'INSERT OR REPLACE INTO attractions (reader_id, name, cost, duration) VALUES (?, ?, ?, ?)',
        (reader_id, name, cost, duration)
    )
    conn.commit()
    conn.close()
    return redirect(url_for('attractions'))

@app.route('/edit_attraction/<int:reader_id>', methods=['GET', 'POST'])
def edit_attraction(reader_id):
    conn = get_db_connection()
    if request.method == 'POST':
        name = request.form['name']
        cost = request.form['cost']
        duration = request.form['duration']
        conn.execute(
            'UPDATE attractions SET name = ?, cost = ?, duration = ? WHERE reader_id = ?',
            (name, cost, duration, reader_id)
        )
        conn.commit()
        conn.close()
        return redirect(url_for('attractions'))

    attraction = conn.execute(
        'SELECT * FROM attractions WHERE reader_id = ?', (reader_id,)
    ).fetchone()
    conn.close()
    if not attraction:
        return "Аттракцион не найден", 404
    return render_template('edit_attraction.html', attraction=attraction)

@app.route('/delete_attraction/<int:reader_id>', methods=['POST'])
def delete_attraction(reader_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM attractions WHERE reader_id = ?', (reader_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('attractions'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
