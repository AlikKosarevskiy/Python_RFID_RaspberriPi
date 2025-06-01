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

// Пины реле
const int relayPins[] = {5, 18, 19, 20};
const int relayCount = sizeof(relayPins) / sizeof(relayPins[0]);

IPAddress local_IP(192, 168, 0, 101);
IPAddress gateway(192, 168, 0, 1);
IPAddress subnet(255, 255, 255, 0);

void publishStatus(bool state) {
  if (state) {
    client.publish(topic_status, "ON");
  } else {
    client.publish(topic_status, "OFF");
  }
}

void setup_wifi() {
  Serial.println("Подключение к Wi-Fi...");
  WiFi.config(local_IP, gateway, subnet);
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("Wi-Fi подключен, IP: ");
  Serial.println(WiFi.localIP());
}

void setRelayState(bool state) {
  for (int i = 0; i < relayCount; i++) {
    digitalWrite(relayPins[i], state ? HIGH : LOW);
  }
  publishStatus(state);
}

void callback(char* topic, byte* payload, unsigned int length) {
  String message;
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }

  Serial.print("Получено сообщение: ");
  Serial.println(message);

  if (message == "ON") {
    setRelayState(true);
  } else if (message == "OFF") {
    setRelayState(false);
  }
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Подключение к MQTT...");
    if (client.connect("ESP32Client", mqtt_user, mqtt_password)) {
      Serial.println("подключено");
      client.subscribe(topic_control);
      publishStatus(digitalRead(relayPins[0]) == HIGH); // Статус по первому пину
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
    digitalWrite(relayPins[i], LOW);  // Начальное состояние — выкл
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
}
