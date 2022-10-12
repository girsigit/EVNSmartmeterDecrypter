# EVNSmartmeterDecrypter

## Überblick

Dies ist eine kleine Anwendung zum Auslesen eines Smartmeters der EVN. Im Einsatz ist es für einen **Sagemcom Drehstromzähler T210-D**, laut dem Dokument unter [Link](https://www.netz-noe.at/Download-(1)/Smart-Meter/218_9_SmartMeter_Kundenschnittstelle_lektoriert_14.aspx) ist es auch für den **Sagemcom Wechselstromzähler S210**, den **Kaifa Wechselstromzähler M110** und den **Kaifa Drehstromzähler MA309** geeignet, dies ist aber nicht getestet!

Sie kann auf einem Server, auch in der Cloud, laufen, oder aber z.B. auf einem Raspberry PI im Heimnetzwerk.

Bevor der Zähler ausgelesen werden kann, muss ein Key bei der EVN angefordert werden. Dies ist in "Wie kann ich die Kundenschnittstelle nutzen?" in [Link](https://www.netz-noe.at/Download-(1)/Smart-Meter/218_9_SmartMeter_Kundenschnittstelle_lektoriert_14.aspx) beschrieben.

## Voraussetzungen

- Einer der oben genannten Smartmeter
- WLAN beim Zähler verfügbar
- Ein Server auf den die Anwendnung laufen kann (kann auch in der Cloud oder ein alter Laptop sein, idealerweise mit Linux)
- Eine MQSQL-Datenbank (kann auch in der Cloud sein)
- Ein MQTT-Broker (kann auch in der Cloud sein)

## Hardware

Das hardwareseitige Auslesen erfolgt mittels eines MBus-TTL-Konverters und eines ESP8266-Microcontrollers. Für Bastler gibt es auch die (günstigere) Variante, den Konverter selbst zu bauen, der Schaltplan ist unter [Schematics.pdf](ESP8266/Schematics.pdf) zu finden.

Der Microcontroller ist mit dem Heim-WLAN verbunden, liest den Rohdatenstrom vom Zähler ein und sendet ihn als MQTT-Message hinaus. Diese wird vom Decrypter empfangen und entschlüsselt, siehe dazu Abschnitt "Decoder-Software".

## Software am Microcontroller

Die Software für den Microcontroller ist unter [ESP8266_Software.ino](ESP8266/ESP8266_Software.ino) zu finden. Hier wird ein **[Wemos D1 mini](https://www.az-delivery.de/products/d1-mini)** mit ESP8266-Chip verwendet, da er günstig und WLAN-fähig ist. **Wichtig**: im µC-Programm müssen noch der WLAN-Name und Passwort sowie die MQTT-Zugangsdaten angepasst werden, die geht nicht automatisch über die .env-Datei.

## Decoder-Software

Die Decoder-Software unter [decoder](decoder) dient dazu, den Rohdatenstrom, der vom µC ausgegeben wird, in die Werte für Energie, Leistung, Spannung, Strom und Leistungsfaktor umzuwandeln. Der Einstigespunkt in das Programm ist [ProcessSmartmeter.py](decoder/ProcessSmartmeter.py), dies startet eine endlose Schleife die alle eintreffenden Messages verarbeitet und wieder hinausschickt.

Das Modul [DecodeData.py](decoder/DecodeData.py) basiert auf dem GIT-Repo [https://github.com/ric-geek/DLMS-APDU-Encrypter-Decrypter](https://github.com/ric-geek/DLMS-APDU-Encrypter-Decrypter), das hat die Decodierung sehr vereinfacht!

Der Zähler sendet alle 5 Sekunden die aktuellen Werte, diese werden entschlüsselt und mittels [SaveToDB.py](decoder/SaveToDB.py) in die Datenbank gepseichert. In der Tabelle *SMARTMETER_DB_TABLE*, standardmäßig "history", wird jeder Wert gespeichert. Dies kann z.B. verwendet werden um in Echtzeit die Leistung einer Autoladestation so zu steuern, dass nur PV-Strom verwendet wird.

Für Visualisierungsanwendungen ist die Dichte zu hoch, deshalb werden in "historyDebounced" nur alle 5 Minuten die Werte gespeichert.

## Nötige Konfigurationen

Um das Programm starten zu können sind einige Einstellungen nötig in der Enviroment-Datei [envTemplate.tempenv](envTemplate.tempenv) nötig.

- Umbenennen auf "server.env", der Name ist in der .gitignore-Datei, dadurch werden keine Passwörter synchronisiert
- Unter Database und MQTT die User, Passwörter, Server und Ports eintragen (Eine all-in-one-Lösung die das automatisch mitbringt ist in Arbeit)
- Bei *SMARTMETER_KEY* den Key eintragen, den die EVN bereitstellt. [Link](https://www.netz-noe.at/Download-(1)/Smart-Meter/218_9_SmartMeter_Kundenschnittstelle_lektoriert_14.aspx)


## Programm starten

Möglichkeit 1, direkt als Python-App:

    python3 decoder/ProcessSmartmeter.py

Möglichkeit 2, als Docker-Container (unter Linux, für Windows wären geringfügige Anpassungen wie z.B. Pfade nötig):

    ./start.sh 



## Datenformat

Die Anwendung nimmt Daten am MQTT-Topic definiert in *SMARTMETER_RAWDATA_MQTT_TOPIC* entgegen, standardmäßig eingestellt auf **sensors/smartmeter**. Ein Datenframe sieht so aus:

    6801016853FF000167DB085341475905E6DBE281F820003986B8E7AC20CB8A3AD2886192BBEEFE4CE64B339F23497BE7EF7DC6748D8967C0569D2C1C5A0B4EF8274362F607474A4966E0CE8784A4B9699C71396DFE7E0299FA5767DF99C8E0DC98A8227EB231D09BE6CD140C686E3DF8652D07EE8AAB0DE1A5ACA4656F5F1862C3F880F8F163EFB56420AFAFB9C6A2422A8DDC2178719AE30419F91B6E40B84329CC48DADA48F9ECC46163D9B73EE57BE2110A410499A5B7643ACF067C21BB2DA39BFA78B6B4238FCDE673732CDE16C743DC580E617F02F4019BAE06AC30EC5ABF1AABA75CBFC3EB780153B6108208E8BC7EF31CC01CF0844F661CCE243A642E9719D42953A316680D0D6853FF110167B2F678E644E82687AA16

Die entschlüsselten Daten werden im MQTT-Topic *SMARTMETER_VALUES_MQTT_TOPIC*, standardmäßig **sensors/smartmeter/values**, ausgegeben. Das Format ist wie folgt:
```json
{
   "WIn":{
      "value":10069016,
      "unit":"Wh"
   },
   "WOut":{
      "value":219,
      "unit":"Wh"
   },
   "PIn":{
      "value":366,
      "unit":"W"
   },
   "POut":{
      "value":0,
      "unit":"W"
   },
   "U1":{
      "value":233.8,
      "unit":"V"
   },
   "U3":{
      "value":234.8,
      "unit":"V"
   },
   "I1":{
      "value":0.33,
      "unit":"A"
   },
   "I2":{
      "value":0.46,
      "unit":"A"
   },
   "I3":{
      "value":1.41,
      "unit":"A"
   },
   "PF":{
      "value":0.943,
      "unit":"1"
   },
   "timestamp":{
      "value":1665581631,
      "unit":"s"
   }
}
```