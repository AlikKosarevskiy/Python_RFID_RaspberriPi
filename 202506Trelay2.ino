#include <WiFi.h>
#include <PubSubClient.h>

// Настройки Wi-Fi
const char* ssid = "Retro-Link";
const char* password = "69134883";

// Настройки MQTT
const char* mqtt_server = "192.168.0.100";
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

// Переменные для управления таймером
bool relaysOn = false;
unsigned long relayOnTime = 0;
const unsigned long RELAY_DURATION = 10000; // 10 секунд

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
    relayOnTime = millis(); // Сохраняем время включения
  }
  publishStatus(state);
}

void callback(char* topic, byte* payload, unsigned int length) {
  String message;
  for (unsigned int i = 0; i < length; i++) {
    message += (char)payload[i];
  }

  message.trim();
  Serial.print("Получено сообщение: ");
  Serial.println(message);

  if (message == "ON") {
    setRelayState(true); // включаем реле
  } else if (message == "OFF") {
    setRelayState(false); // выключаем досрочно
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

  // Автоматическое выключение через 10 сек
  if (relaysOn && (millis() - relayOnTime >= RELAY_DURATION)) {
    Serial.println("Таймер истёк — выключаю реле");
    setRelayState(false);
  }
}
