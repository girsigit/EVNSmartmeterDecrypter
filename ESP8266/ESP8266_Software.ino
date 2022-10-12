// # Version 1.0 - 2022-10-12

#include <ESP8266WiFi.h>
#include <PubSubClient.h>

#define SERIAL_SPEED 2400

// Loop settings
#define SEND_AT_LOOP 5
#define LOOP_DURATION_SECONDS 2
#define FREQUENCY_HZ 80000000
#define MIN_WAIT_TICKS FREQUENCY_HZ // Min wait time important for example for wifi handling
const uint32_t LOOP_DURATION_TICKS = FREQUENCY_HZ * LOOP_DURATION_SECONDS;
volatile uint8_t loopCnt = 0;

Todo : Change to real WIFI const char *ssid = "MYWIFI";
const char *password = "dontTellAnyone";

char *ESP_NAME = "Smartmeter";

Todo : Change to real MQTT const char *mqttAddress = "192.168.xxx.xxx"; // Or for example an online broker
const int mqttPort = 1883;
const char *mqttUser = "mqttUser";
const char *mqttPassword = "mqttPW";
const char *mqttPayloadTopic = "sensors/smartmeter";
const char *mqttStatusTopic = "status/smartmeter";

// Timing
volatile int32_t tick_current = 0;
volatile int32_t tick_old = 0;

// Reconnects
volatile uint32_t connectsWifi = 0;
volatile uint32_t connectsMqtt = 0;

// Serial communication
const uint16_t SERIAL_BUFFER_SIZE = 512;
const uint16_t ASCII_BUFFER_SIZE = 2 * SERIAL_BUFFER_SIZE;
char serialInBuffer[SERIAL_BUFFER_SIZE];

WiFiClient espClient;
PubSubClient mqttClient = PubSubClient(espClient);

void connectWifi()
{

  if (WiFi.status() == 7)
  {
    // connect to your local wi-fi network
    Serial.println("WiFi.begin");
    WiFi.begin(ssid, password);
  }
  else if (WiFi.status() == WL_CONNECTED)
  {
    return;
  }

  while (WiFi.status() != WL_CONNECTED)
  {
    Serial.println("Connecting to WiFi...");
    delay(2000);
  }

  connectsWifi++;

  // Send connected message
  reportConnectedCount();

  Serial.println("Connected to the WiFi network");
}

void connectMqtt()
{

  if (MQTT_CONNECTED == mqttClient.state())
    return;

  Serial.println("mqtt connection started");

  mqttClient.setBufferSize(1024);

  while (0 == mqttClient.connected())
  {
    Serial.println("Connecting to MQTT...");

    if (mqttClient.connect(ESP_NAME, mqttUser, mqttPassword))
    {
      connectsMqtt++;

      // Send connected message
      reportConnectedCount();

      Serial.println("mqtt connected");
    }
    else
    {
      Serial.print("mqtt failed with state ");
      Serial.print(mqttClient.state());
      delay(2000);
    }
  }
}

void reportConnectedCount()
{
  if (WiFi.status() == WL_CONNECTED && mqttClient.connected())
  {
    String counterString = "{\"connectsWifi\":";
    counterString += String(connectsWifi);
    counterString += ",";
    counterString += " \"connectsMQTT\":";
    counterString += String(connectsMqtt);
    counterString += "}";

    int bufferSize = counterString.length() + 1;
    char buf[bufferSize];
    counterString.toCharArray(buf, bufferSize);

    mqttClient.publish(mqttStatusTopic, buf);
  }
}

String addressToString(uint8_t *adr)
{
  String adrStr = "";
  for (int n = 0; n < 8; n++)
  {
    adrStr += String(adr[n]);
    if (n < 7)
      adrStr += ":";
  }

  return adrStr;
}

void receiveSerialData()
{
  if (Serial.available())
  {
    for (uint16_t n = 0; n < SERIAL_BUFFER_SIZE; n++)
    {
      serialInBuffer[n] = 0;
    }

    uint16_t bufferCnt = 0;

    Serial.print("\nI received: ");
    // read the incoming byte:
    while (0 < Serial.available())
    {
      char incomingByte = Serial.read();
      serialInBuffer[bufferCnt] = incomingByte;
      bufferCnt++;

      // Serial.print(incomingByte, HEX);
      // Serial.print(",");
      if (0 == Serial.available())
      {
        // Serial.println("Exiting beacause there is no data begin");
        delay(500);
        // Serial.println("Exiting beacause there is no data end");
      }
    }

    Serial.println("Finished receiving, got:");
    // for (uint16_t n=0; n < bufferCnt; n++) {
    //   //Serial.println(n);
    //   Serial.print(serialInBuffer[n], HEX);
    //   Serial.print(",");
    // }

    // Serial.print("\n");

    Serial.println("bufferCnt: ");
    Serial.println(bufferCnt);

    // Buffer in ASCII Code to enable mqtt compatibility
    char bufferASCII[ASCII_BUFFER_SIZE];
    uint16_t bufferASCIICnt = 0;

    for (uint16_t n = 0; n < ASCII_BUFFER_SIZE; n++)
    {
      bufferASCII[n] = 0x0;
    }

    for (uint16_t n = 0; n < bufferCnt; n++)
    {
      // Serial.print("serialInBuffer content: ");
      // Serial.print(serialInBuffer[n], HEX);
      // Serial.print("\n");

      char lower = serialInBuffer[n] & 0x0F;
      char upper = (serialInBuffer[n] >> 4) & 0x0F;

      // Serial.print("lower: ");
      // Serial.print(lower, HEX);
      // Serial.print(", upper: ");
      // Serial.print(upper, HEX);
      // Serial.print("\n");

      char lowerASCII;
      char upperASCII;

      if (9 >= lower)
        lowerASCII = lower + 0x30;
      else
        lowerASCII = (lower - 0x0A) + 0x41;

      if (9 >= upper)
        upperASCII = upper + 0x30;
      else
        upperASCII = (upper - 0x0A) + 0x41;

      bufferASCII[bufferASCIICnt++] = upperASCII;
      bufferASCII[bufferASCIICnt++] = lowerASCII;
    }

    mqttClient.publish(mqttPayloadTopic, bufferASCII);
  }
}

void setup()
{
  // Set up serial
  Serial.begin(SERIAL_SPEED);

  // Set up Wifi
  // Disable own Access - Point
  // https://forum.arduino.cc/index.php?topic=557669.0
  WiFi.softAPdisconnect(true);

  connectWifi();

  // Set up MQTT
  mqttClient.setServer(mqttAddress, mqttPort);
  mqttClient.setCallback(callback);
  connectMqtt();
}

void callback(char *topic, byte *payload, unsigned int length)
{
  return;
}

static inline int32_t asm_ccount(void)
{
  int32_t r;
  asm volatile("rsr %0, ccount"
               : "=r"(r));
  return r;
}

// the loop function runs over and over again forever
void loop()
{

  // Serial.println("Looping..");

  // Get the c counter on beginning
  volatile int32_t ccount_begin = asm_ccount();

  // Reconnect Wifi if not connected
  connectWifi();

  // Reconnect mqtt if not connected
  connectMqtt();

  // Receive Serial data if some is available
  receiveSerialData();

  delay(500);

  // This function should be called regularly to allow the client to process incoming messages and maintain its connection to the server [2].
  mqttClient.loop();
}
