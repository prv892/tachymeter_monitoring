import sys
import os
import json
import ftplib

def lade_ftp_config(config_path="ftp_config.json"):
    """Lädt die FTP-Zugangsdaten aus einer JSON-Datei."""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Konfigurationsdatei nicht gefunden: {config_path}")
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
        
    return config

def lade_hoch(dateipfad):
    if not os.path.exists(dateipfad):
        print(f"[Upload] Fehler: Die Datei {dateipfad} existiert nicht.")
        return

    try:
        # 1. Konfiguration laden
        # Da upload.py aus dem Hauptverzeichnis aufgerufen wird, reicht "ftp_config.json"
        # Falls es in einen Unterordner soll, den Pfad hier anpassen.
        config_pfad = os.path.join(os.path.dirname(__file__), "ftp_config.json")
        config = lade_ftp_config(config_pfad)
        
        host = config.get("FTP_HOST")
        user = config.get("FTP_USER")
        password = config.get("FTP_PASS")
        remote_dir = config.get("FTP_DIR", "/")
        
        dateiname = os.path.basename(dateipfad)

        # 2. FTP-Verbindung aufbauen
        print(f"[Upload] Verbinde mit FTP-Server {host}...")
        # WICHTIG: Wenn der Server FTPS (FTP over TLS) erfordert, nutze ftplib.FTP_TLS(host)
        ftp = ftplib.FTP(host)
        ftp.login(user=user, passwd=password)
        
        # 3. In das Zielverzeichnis wechseln
        try:
            ftp.cwd(remote_dir)
        except ftplib.error_perm:
            print(f"[Upload] Warnung: Verzeichnis {remote_dir} existiert nicht, versuche es im Root.")

        # 4. Datei hochladen (im Binärmodus)
        print(f"[Upload] Lade Datei {dateiname} hoch...")
        with open(dateipfad, 'rb') as f:
            ftp.storbinary(f'STOR {dateiname}', f)
            
        print(f"[Upload] Erfolgreich hochgeladen: {dateiname}")
        
        # 5. Verbindung schließen
        ftp.quit()

    except ftplib.all_errors as e:
        print(f"[Upload] FTP-Fehler beim Upload: {e}")
    except Exception as e:
        import traceback
        print(f"[Upload] Allgemeiner Fehler beim Upload: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    # Prüfen, ob ein Dateipfad als Argument übergeben wurde
    if len(sys.argv) < 2:
        print("Verwendung: python upload.py <pfad_zur_datei>")
        sys.exit(1)
        
    ziel_datei = sys.argv[1]
    lade_hoch(ziel_datei)