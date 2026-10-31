/*
 * esp32_pir_pawos.ino - Firmware para ESP32 WROVER-IE con Sensor PIR
 *
 * Proyecto PawOS - Sistema de Monitoreo y Cuidado de Mascotas
 *
 * Descripcion:
 * Detecta movimiento en la zona de mascotas mediante un sensor PIR (HC-SR501 / SR602).
 * Al detectar movimiento, se conecta a la red Wi-Fi y envia un HTTP POST en formato JSON
 * al endpoint /api/alerta del Servidor de Monitoreo de PawOS (src/servidor_monitoreo.c).
 *
 * Mapeo de Hardware para ESP32 WROVER-IE:
 * - PIR Sensor OUT -> GPIO 13 (Pin seguro que no interfiere con PSRAM en GPIO 16/17 ni Flash)
 * - PIR VCC        -> 3.3V / 5V (segun modulo PIR)
 * - PIR GND        -> GND
 */

#include <WiFi.h>
#include <HTTPClient.h>

// =====================================================================
// CONFIGURACION DE RED Y SERVIDOR PAWOS
// =====================================================================
const char* WIFI_SSID     = "Paspi";       // Nombre de la red Wi-Fi local
const char* WIFI_PASSWORD = "PaolaLopez";    // Contraseña de la red Wi-Fi

// IP y Puerto del Servidor de Monitoreo PawOS (servidor_monitoreo.c en puerto 8080)
const char* PAWOS_SERVER_URL = "http://10.46.85.213:8080/api/alerta";

// Identificador unico del animal / collar / zona asignada
const char* ANIMAL_ID = "MASCOTA_PIR_01";

// =====================================================================
// CONFIGURACION DE PINES Y TIEMPOS
// =====================================================================
const int PIR_PIN = 13;                          // GPIO 13 para la señal digital del PIR
const unsigned long COOLDOWN_MS = 30000;         // Cooldown de 30 segundos entre alertas para evitar saturacion
const unsigned long LED_INDICATOR = 2;           // LED integrado (GPIO 2) para status

unsigned long ultimaAlertaMs = 0;

void conectarWiFi() {
    if (WiFi.status() == WL_CONNECTED) return;

    Serial.print("[ESP32 PawOS] Conectando a Wi-Fi: ");
    Serial.println(WIFI_SSID);

    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    int intentos = 0;
    while (WiFi.status() != WL_CONNECTED && intentos < 20) {
        delay(500);
        Serial.print(".");
        intentos++;
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\n[ESP32 PawOS] Wi-Fi Conectado!");
        Serial.print("[ESP32 PawOS] IP asignada: ");
        Serial.println(WiFi.localIP());
    } else {
        Serial.println("\n[ESP32 PawOS] Error: No se pudo conectar a Wi-Fi.");
    }
}

void enviarAlertaMovimiento() {
    conectarWiFi();

    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("[ESP32 PawOS] Error: Sin conexion Wi-Fi, alerta no enviada.");
        return;
    }

    HTTPClient http;
    http.begin(PAWOS_SERVER_URL);
    http.addHeader("Content-Type", "application/json");

    // Formato JSON mapeado con servidor_monitoreo.c
    // Campos esperados: animal_id (string), tipo (string), detalle (string), valor (number)
    String jsonBody = "{";
    jsonBody += "\"animal_id\":\"" + String(ANIMAL_ID) + "\",";
    jsonBody += "\"tipo\":\"movimiento\",";
    jsonBody += "\"detalle\":\"Movimiento detectado por sensor PIR en modulo ESP32 WROVER-IE\",";
    jsonBody += "\"valor\":1.0";
    jsonBody += "}";

    Serial.println("[ESP32 PawOS] Enviando HTTP POST a /api/alerta...");
    Serial.println("Payload: " + jsonBody);

    digitalWrite(LED_INDICATOR, HIGH);
    int httpResponseCode = http.POST(jsonBody);
    digitalWrite(LED_INDICATOR, LOW);

    if (httpResponseCode > 0) {
        Serial.printf("[ESP32 PawOS] Alerta enviada con exito. Codigo HTTP: %d\n", httpResponseCode);
        String response = http.getString();
        Serial.println("Respuesta del servidor: " + response);
    } else {
        Serial.printf("[ESP32 PawOS] Error al enviar HTTP POST. Error: %s\n", http.errorToString(httpResponseCode).c_str());
    }

    http.end();
}

void setup() {
    Serial.begin(115200);
    delay(1000);

    Serial.println("\n=======================================================");
    Serial.println(" PawOS - Sensor de Movimiento PIR (ESP32 WROVER-IE)");
    Serial.println("=======================================================");

    pinMode(PIR_PIN, INPUT);
    pinMode(LED_INDICATOR, OUTPUT);
    digitalWrite(LED_INDICATOR, LOW);

    conectarWiFi();
    Serial.println("[ESP32 PawOS] Modulo listo. Esperando deteccion de movimiento...");
}

void loop() {
    int estadoPIR = digitalRead(PIR_PIN);

    if (estadoPIR == HIGH) {
        unsigned long ahora = millis();
        if (ahora - ultimaAlertaMs >= COOLDOWN_MS || ultimaAlertaMs == 0) {
            Serial.println("\n[¡MOVIMIENTO DETECTADO!] Sensor PIR activado.");
            enviarAlertaMovimiento();
            ultimaAlertaMs = millis();
        } else {
            Serial.println("[ESP32 PawOS] Movimiento detectado dentro del periodo de cooldown. Omitiendo envio.");
        }
    }

    delay(200); // Pequeña pausa de muestreo
}
