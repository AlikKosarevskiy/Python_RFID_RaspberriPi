#include <WiFi.h>
#include <PubSubClient.h>
#include <Arduino.h>

#define RXD2 23      // RO -> RX
#define TXD2 22      // DI -> TX
#define RS485_EN 4   // RE/DE
#define RELAY1 18    // пока не используется
#define RELAY2 19    // пока не используется

// Настройки Wi-Fi
const char* ssid = "Retro-Link";
const char* password = "69134883";

// Настройки MQTT
const char* mqtt_server = "192.168.0.110";
const int mqtt_port = 1883;
const char* mqtt_user = "";
const char* mqtt_password = "";

const char* topic_control = "/relay/control";
const char* topic_status  = "/relay/status";
const char* topic_rfid    = "/rfid/id";  // топик для передачи ID брелка
bool readerReady = false;



WiFiClient espClient;
PubSubClient client(espClient);

const int relayPins[] = {5, 18, 19, 21};
const int relayCount = sizeof(relayPins) / sizeof(relayPins[0]);

IPAddress local_IP(192, 168, 0, 101);
IPAddress gateway(192, 168, 0, 1);
IPAddress subnet(255, 255, 255, 0);

// Переменные для таймера
bool relaysOn = false;
unsigned long relayOnTime = 0;
const unsigned long RELAY_DURATION = 10000; // 10 секунд
int duration = 10000; // по умолчанию 10 сек

// Для периодического извещения
unsigned long lastStatusSent = 0;
// CRC16 Modbus
uint16_t calcCRC(uint8_t *data, uint8_t len) {
  uint16_t crc = 0xFFFF;
  for (int pos = 0; pos < len; pos++) {
    crc ^= (uint16_t)data[pos];
    for (int i = 0; i < 8; i++) {
      if ((crc & 0x0001) != 0) {
        crc >>= 1;
        crc ^= 0xA001;
      } else {
        crc >>= 1;
      }
    }
  }
  return crc;
}

void sendTimeRequest() {
  uint8_t payload[] = {0x17, 0x05, 0xB6, 0xFE, 0x1B};  // Запрос времени
  uint16_t crc = calcCRC(payload, sizeof(payload));

  uint8_t request[7];
  memcpy(request, payload, sizeof(payload));
  request[5] = crc & 0xFF;
  request[6] = (crc >> 8) & 0xFF;

  Serial.print("Отправка запроса времени: ");
  for (int i = 0; i < 7; i++) {
    Serial.print("0x");
    if (request[i] < 0x10) Serial.print("0");
    Serial.print(request[i], HEX);
    Serial.print(" ");
  }
  Serial.println();

  digitalWrite(RS485_EN, HIGH);
  delay(2);
  Serial2.write(request, 7);
  Serial2.flush();
  delay(2);
  digitalWrite(RS485_EN, LOW);
}


void publishStatus(bool state) {
  if (state) {
    client.publish(topic_status, "ON");
  } else {
    client.publish(topic_status, "OFF");
  }
}

void setup_wifi() {
  delay(10);
  Serial.println("Подключение к Wi-Fi...");
  WiFi.config(local_IP, gateway, subnet);
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWi-Fi подключен");
  Serial.println(WiFi.localIP());
}

void setRelayState(bool state) {
  for (int i = 0; i < relayCount; i++) {
    digitalWrite(relayPins[i], state ? HIGH : LOW);
  }
  relaysOn = state;
  if (state) {
    relayOnTime = millis();
    lastStatusSent = 0;  // сброс для начала отсчета
  }
  publishStatus(state);
}


void callback(char* topic, byte* payload, unsigned int length) {
  String message;
  for (int i = 0; i < length; i++) message += (char)payload[i];

  message.trim();
  Serial.print("Получено сообщение: ");
  Serial.println(message);

  if (message.startsWith("ON")) {
    // int duration = 10000; // по умолчанию 10 сек

    if (message.indexOf(":") > 0) {
      duration = message.substring(message.indexOf(":") + 1).toInt() * 1000;
    }

    // digitalWrite(RELAY_PIN, HIGH);
    setRelayState(true);
    client.publish("/relay/status", "Включено");
    // delay(duration);
    // // digitalWrite(RELAY_PIN, LOW);
    // setRelayState(false);
    // client.publish("/relay/status", "Выключено");
  }

  else if (message == "OFF") {
    // digitalWrite(RELAY_PIN, LOW);
    setRelayState(false);
    client.publish("/relay/status", "Выключено принудительно");
  }
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Подключение к MQTT...");
    if (client.connect("ESP32Client")) {
      Serial.println("подключено");
      client.subscribe(topic_control);
    } else {
      Serial.print("ошибка, rc=");
      Serial.print(client.state());
      Serial.println(" повтор через 5 сек");
      delay(5000);
    }
  }
}


void setup() {
  Serial.begin(115200);

  for (int i = 0; i < relayCount; i++) {
    pinMode(relayPins[i], OUTPUT);
    digitalWrite(relayPins[i], LOW);
  }
  setup_wifi();
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);



  Serial.println("🔌 Проверка подключения считывателя...");

  pinMode(RS485_EN, OUTPUT);
  digitalWrite(RS485_EN, LOW);

  Serial2.begin(9600, SERIAL_8N1, RXD2, TXD2);

  sendTimeRequest();

  unsigned long startTime = millis();
  while (millis() - startTime < 2000) {
    if (Serial2.available()) {
      Serial.println("✅ Считыватель ответил! Начинаем приём ID ключей...");
      readerReady = true;

      // Прочитаем и выведем ответ (для отладки)
      while (Serial2.available()) {
        uint8_t b = Serial2.read();
        Serial.print("0x");
        if (b < 0x10) Serial.print("0");
        Serial.print(b, HEX);
        Serial.print(" ");
      }
      Serial.println();
      break;
    }
  }

  if (!readerReady) {
    Serial.println("❌ Нет ответа от считывателя. Проверь питание/линии.");
  }
}

void loop() {

  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  if (!readerReady) return;

  if (Serial2.available()) {
    uint8_t buffer[32];
    int index = 0;

    while (Serial2.available() && index < sizeof(buffer)) {
      buffer[index++] = Serial2.read();
    }

    if (index >= 8) {
      // Формируем ID как HEX строку
      String id = "";
      for (int i = 2; i <= 5; i++) {
        if (buffer[i] < 0x10) id += "0";
        id += String(buffer[i], HEX);
      }

      Serial.print("📡 Получен ID: ");
      Serial.println(id);

      // Отправка по MQTT
      if (client.connected()) {
        client.publish(topic_rfid, id.c_str());
        Serial.println("📤 Отправлен ID по MQTT.");
      } else {
        Serial.println("⚠️ MQTT не подключен.");
      }

    } else {
      Serial.print("🔸 Неполный пакет (байтов: ");
      Serial.print(index);
      Serial.println(")");
    }
  }
}
