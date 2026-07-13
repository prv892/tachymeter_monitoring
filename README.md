# Tachymeter Monitoring System

Dieses Repository enthält ein, in Python geschriebenes Softwaresystem für das automatisierte  Monitoring mittels Tachymeter. Das System steuert die Totalstation, führt Satzmessungen durch und transformiert die lokalen Messungen über eine 6-Parameter-Transformation in ein globales Koordinatensystem. 

Zusätzlich bietet das Projekt GUIs zur Konfiguration der Messparameter und zur Berechnung von Polarwerten aus Koordinaten, um die Installation des Systems zu erleichtern

---

## Kernfunktionen

* **Automatisierte Tachymeter-Steuerung:** Direkte serielle Anbindung der Totalstation über `pyGeoCOM`.
* **Sensorintegration (optional):** Einlesen von Temperatur- und Luftdruckdaten zur sofortigen Atmosphärenkorrektur (via USB-Thermometer DS18B20 und I2C-Drucksensor BMP388).
* **Datenverarbeitung:** Automatische Mittelwertbildung von Sätzen (`Satzmessung`) unter Berücksichtigung fester Toleranzen (z. B. 0.5 gon / 0.5 cm).
* **Gauß-Markov-Ausgleichung:** Berechnung der Transformationsparameter (3D-Translation und -Rotation) inklusive automatischer Ausreißer-Eliminierung.
* **Berichterstellung:** Generierung von CSV-Dateien für Neupunkte und Rohdaten sowie Erstellung eines PDF-Berichts nach jeder Epoche.
* **Konfigurations-GUI:** Verwaltung von Soll-Koordinaten, Zielen und Parametern.

---

## Dateistruktur 

* `main.py`  
  Das Hauptskript des Systems. Startet die Sensorabfrage, initiiert die Messung, verarbeitet die Daten, ruft die Ausgleichung auf und generiert die Berichte (CSV/PDF).
* `aufnahme_neu.py`  
  Kommunikation mit dem Tachymeter. Führt die Zielansteuerung, die Messungen in zwei Lagen und die Anwendung der Atmosphärenkorrekturen durch.
* `ausgleichung.py`  
  Beinhaltet die Transformation. Berechnet Näherungswerte, iteriert die Ausgleichung und eliminiert stochastisch Fehlmessungen.
* `Satzmessung.py`  
  Objektorientierte Abbildung der Datenstrukturen. Führt die Reduktion und Mittelung der Richtungen und Strecken durch.
* `sensor.py`  
  Schnittstellen für die externe Hardware: USB-Thermometer und I2C BMP388 Drucksensor 
* `post_processing.py`  
  Ermöglicht die nachträgliche Auswertung bereits aufgezeichneter Rohdaten, um die Ausgleichung ohne aktive Hardware-Verbindung zu testen.
* `config.py`  
  Grafischer Konfigurator zur einfachen Bearbeitung der JSON-basierten `params.txt` (Punkte, Soll-Koordinaten, Standardabweichungen).
* `visur-rechner.py`  
  Eigenständiges GUI-Tool für geodätische Polarberechnungen (Horizontalrichtungen, Zenitwinkel und 3D-Distanzen zwischen Koordinaten). Nützlich für die Einrichtung des Systems

---

## Systemanforderungen und Installation

### Voraussetzungen
* **Hardware:** Kompatibles Tachymeter (seriell verbunden), DS18B20 Thermometer, BMP388 Drucksensor. Sind Thermometer und Drucksensor nicht vorhanden, so können feste Werte übergeben werden.

### Abhängigkeiten

```bash
pip install numpy scipy pandas pyserial reportlab adafruit-circuitpython-bmp3xx