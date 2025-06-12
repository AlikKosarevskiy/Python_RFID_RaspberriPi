#include <WiFi.h>
#include <PubSubClient.h>

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

// void callback(char* topic, byte* payload, unsigned int length) {
//   String message;
//   for (unsigned int i = 0; i < length; i++) {
//     message += (char)payload[i];
//   }

//   message.trim();
//   Serial.print("Получено сообщение: ");
//   Serial.println(message);

//   if (message == "ON") {
//     setRelayState(true);
//   } else if (message == "OFF") {
//     setRelayState(false);
//   }
// }

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
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  // Управление таймером и уведомлениями
  if (relaysOn) {
    unsigned long elapsed = millis() - relayOnTime;
    
    // Уведомление каждую секунду
    if (millis() - lastStatusSent >= 1000) {
      // int remaining = (RELAY_DURATION - elapsed) / 1000;
      int remaining = (duration - elapsed) / 1000;
      if (remaining >= 0) {
        char msg[32];
        snprintf(msg, sizeof(msg), "Remaining: %d", remaining);
        client.publish(topic_status, msg);
        Serial.println(msg);
        lastStatusSent = millis();
      }
    }

    // Выключение после 10 секунд
    // if (elapsed >= RELAY_DURATION) {
    if (elapsed >= duration) {
      Serial.println("Таймер истёк — выключаю реле");
      setRelayState(false);
    }
  }
}
