#include <SPI.h>
#include <MFRC522.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <Arduino.h>
#include <Adafruit_NeoPixel.h>

#define RC522_SCK  14
#define RC522_MOSI 13
#define RC522_MISO 27
#define RC522_SS   26
#define RC522_RST  33

#define RXD2 23      // RO -> RX
#define TXD2 22      // DI -> TX
#define RS485_EN 4   // RE/DE
#define RELAY1 18    // пока не используется
#define RELAY2 19    // пока не используется

#define LED_PIN    32
#define LED_COUNT  36

MFRC522 rfid(RC522_SS, RC522_RST);
Adafruit_NeoPixel strip(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);

// Animation variables
int ledIndex = 0;
int direction = 1;
unsigned long lastAnimTime = 0;
const int animDelay = 30; // ms between LED moves

// Your relay state variable
// bool relaysOn = false;

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

const unsigned long PACKET_TIMEOUT = 20;  // мс — пауза между байтами
static uint8_t packetBuffer[64];
static int packetIndex = 0;
static unsigned long lastByteTime = 0;

String lastUid = "";
unsigned long lastReadTime = 0;
const unsigned long UID_REPEAT_DELAY = 2000;  // 2 секунды защита

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

unsigned long lastRFIDReadTime = 0;
const unsigned long RFID_COOLDOWN = 1000;  // 1 сек
bool rfidReady = true;

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
    // Проверим, есть ли длительность (ON:10)
    if (message.indexOf(":") > 0) {
      duration = message.substring(message.indexOf(":") + 1).toInt() * 1000;

      setRelayState(true);
      relayOnTime = millis();  // включено с таймером
      relaysOn = true;
      Serial.print("Реле включено на ");
      Serial.print(duration / 1000);
      Serial.println(" сек.");
    } else {
      // Включение без времени — включаем без таймера
      setRelayState(true);
      relayOnTime = 0;   // обнулим таймер
      relaysOn = false;  // не отслеживаем выключение
      Serial.println("Реле включено без таймера (до OFF)");
    }

    client.publish("/relay/status", "Включено");
  }

  else if (message == "OFF") {
    setRelayState(false);
    relaysOn = false;
    relayOnTime = 0;
    client.publish("/relay/status", "Выключено принудительно");
    Serial.println("Реле выключено вручную");
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

  // Запуск SPI на альтернативных пинах
SPI.begin(RC522_SCK, RC522_MISO, RC522_MOSI, RC522_SS);
rfid.PCD_Init();
Serial.println("RC522 инициализирован");

 strip.begin();
  strip.setBrightness(50);

  // RED for 0.4 seconds
  for (int i = 0; i < LED_COUNT; i++) {
    strip.setPixelColor(i, strip.Color(255, 0, 0));
  }
  strip.show();
  delay(400);

  // GREEN for 0.4 seconds
  for (int i = 0; i < LED_COUNT; i++) {
    strip.setPixelColor(i, strip.Color(0, 255, 0));
  }
  strip.show();
  delay(400);

  // BLUE for 0.4 seconds
  for (int i = 0; i < LED_COUNT; i++) {
    strip.setPixelColor(i, strip.Color(0, 0, 255));
  }
  strip.show();
  delay(400);

  // Then turn off all LEDs
  strip.clear();
  strip.show();

}

void loop() {

  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  if (!readerReady) return;

if (relaysOn && relayOnTime > 0 && millis() - relayOnTime >= duration) {
  setRelayState(false);
  relaysOn = false;
  client.publish("/relay/status", "Выключено по таймеру");
  Serial.println("Реле выключено по истечении времени");
}

 if (relaysOn) {
    // 🔋 Relay is ON → show green
    for (int i = 0; i < LED_COUNT; i++) {
      strip.setPixelColor(i, strip.Color(0, 255, 0));
    }
    strip.show();
  } else {
    // ⏳ Waiting → run "ping-pong" animation
    unsigned long now = millis();
    if (now - lastAnimTime > animDelay) {
      strip.clear();
      strip.setPixelColor(ledIndex, strip.Color(255, 255, 255)); // white dot
      strip.show();

      ledIndex += direction;
      if (ledIndex >= LED_COUNT - 1 || ledIndex <= 0) {
        direction = -direction;  // change direction
      }
      lastAnimTime = now;
    }
  }

while (Serial2.available()) {
    uint8_t b = Serial2.read();
    if (packetIndex < sizeof(packetBuffer)) {
      packetBuffer[packetIndex++] = b;
      lastByteTime = millis();  // обновляем время последнего байта
    }
  }

  // Если с момента последнего байта прошло достаточно времени — считаем, что пакет завершён
  if (packetIndex > 0 && (millis() - lastByteTime > PACKET_TIMEOUT)) {
    Serial.print("📥 Принято: ");
    for (int i = 0; i < packetIndex; i++) {
      Serial.print("0x");
      if (packetBuffer[i] < 0x10) Serial.print("0");
      Serial.print(packetBuffer[i], HEX);
      Serial.print(" ");
    }
    Serial.println();

    if (packetIndex >= 6) {
      // байт 0 — адрес считывателя
      uint8_t readerIdByte = packetBuffer[0];
      String readerId = String(readerIdByte);

      // байты 2–5 — ID
      String id = "";
      for (int i = 5; i <= 8; i++) {
        if (packetBuffer[i] < 0x10) id += "0";
        id += String(packetBuffer[i], HEX);
      }

      Serial.print("📡 Получен ID: ");
      Serial.println(id);
      Serial.print("🔢 Номер считывателя: ");
      Serial.println(readerId);

      if (client.connected()) {
        String payload = readerId + "," + id;
        client.publish(topic_rfid, payload.c_str());
        Serial.print("📤 Отправлен ID по MQTT: ");
        Serial.println(payload);
      } else {
        Serial.println("⚠️ MQTT не подключен.");
      }
    } else {
      Serial.print("⚠️ Слишком короткий пакет (");
      Serial.print(packetIndex);
      Serial.println(" байт)");
    }

    // очистить буфер после обработки
    packetIndex = 0;
  }

 if (rfidReady && rfid.PICC_IsNewCardPresent() && rfid.PICC_ReadCardSerial()) {
  String uid = "";
  for (byte i = 0; i < rfid.uid.size; i++) {
    if (rfid.uid.uidByte[i] < 0x10) uid += "0";
    uid += String(rfid.uid.uidByte[i], HEX);
  }

  if (uid == lastUid && millis() - lastReadTime < UID_REPEAT_DELAY) {
    // Повтор — игнорируем
    return;
  }

  lastUid = uid;
  lastReadTime = millis();

  String payload = "23," + uid;
  client.publish(topic_rfid, payload.c_str());
  Serial.println("Отправлен UID: " + payload);

  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();

  // ставим таймер
  rfidReady = false;
  lastRFIDReadTime = millis();
}

// включаем повторное считывание через 1 сек
if (!rfidReady && millis() - lastRFIDReadTime > RFID_COOLDOWN) {
  rfidReady = true;
}

}
