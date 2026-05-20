"""
=======================================================
  SCRIPT PRINCIPAL — Système de tri des déchets
  A exécuter sur le Raspberry Pi
  Commande : python3 /home/azza/tri_dechets.py
=======================================================
"""

import cv2
import numpy as np
import onnxruntime as ort
from PIL import Image
from collections import deque
import sqlite3
import datetime
import time
import sys

# ─── Tentative chargement GPIO ────────────────────────
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    print("⚠️  GPIO non disponible — mode simulation")

# ─── Configuration ────────────────────────────────────
CLASSES    = ['cardboard', 'glass', 'metal', 'paper', 'plastic', 'trash']
MODEL_PATH = "/home/azza/waste_model.onnx"
DB_PATH    = "/home/azza/tri_dechets.db"

# LEDs : 1 pin par catégorie (modifie si tu changes le câblage)
LED_PINS = {
    'cardboard': 17,
    'glass':     27,
    'metal':     22,
    'paper':     10,
    'plastic':    9,
    'trash':     11,
}

# Capteur ultrasonique
TRIG_PIN = 23
ECHO_PIN = 24

# Seuils de confiance (identiques à ton notebook)
SEUILS = {
    'cardboard': 60.0,
    'glass':     55.0,
    'metal':     65.0,
    'paper':     70.0,
    'plastic':   65.0,
    'trash':     55.0,
}

# ─── Init GPIO ────────────────────────────────────────
if GPIO_AVAILABLE:
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    for pin in LED_PINS.values():
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, False)
    GPIO.setup(TRIG_PIN, GPIO.OUT)
    GPIO.setup(ECHO_PIN, GPIO.IN)
    print("✅ GPIO initialisé")

# ─── Charger modèle ONNX ──────────────────────────────
print("⏳ Chargement du modèle IA...")
if not __import__('os').path.exists(MODEL_PATH):
    print(f"❌ Modèle introuvable : {MODEL_PATH}")
    print("   Transfère d'abord waste_model.onnx sur le Pi")
    sys.exit(1)

session = ort.InferenceSession(MODEL_PATH)
print("✅ Modèle IA chargé !")

# ─── Transform (identique entraînement) ───────────────
def preprocess(roi_bgr):
    img = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2RGB)
    img = cv2.resize(img, (160, 160))
    img = img.astype(np.float32) / 255.0
    mean = np.array([0.485, 0.456, 0.406])
    std  = np.array([0.229, 0.224, 0.225])
    img  = (img - mean) / std
    img  = np.transpose(img, (2, 0, 1))        # HWC → CHW
    img  = np.expand_dims(img, axis=0).astype(np.float32)
    return img

# ─── Softmax ──────────────────────────────────────────
def softmax(x):
    e = np.exp(x - x.max())
    return e / e.sum()

# ─── Mesure distance ultrasonique ─────────────────────
def mesure_distance():
    if not GPIO_AVAILABLE:
        return 10.0   # simulation : toujours "déchet présent"
    GPIO.output(TRIG_PIN, True)
    time.sleep(0.00001)
    GPIO.output(TRIG_PIN, False)
    t0 = t1 = time.time()
    timeout = time.time() + 0.1
    while GPIO.input(ECHO_PIN) == 0:
        t0 = time.time()
        if time.time() > timeout:
            return 999
    timeout = time.time() + 0.1
    while GPIO.input(ECHO_PIN) == 1:
        t1 = time.time()
        if time.time() > timeout:
            return 999
    return (t1 - t0) * 34300 / 2

# ─── Contrôle LEDs ────────────────────────────────────
def allumer_led(categorie):
    if not GPIO_AVAILABLE:
        return
    for cls, pin in LED_PINS.items():
        GPIO.output(pin, GPIO.HIGH if cls == categorie else GPIO.LOW)

def eteindre_leds():
    if not GPIO_AVAILABLE:
        return
    for pin in LED_PINS.values():
        GPIO.output(pin, GPIO.LOW)

# ─── Sauvegarde en base ───────────────────────────────
def sauvegarder(categorie, confiance):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT INTO tris (timestamp, categorie, confiance) VALUES (?,?,?)",
            (datetime.datetime.now().isoformat(), categorie, confiance)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"⚠️  DB erreur : {e}")

# ─── Boucle principale ────────────────────────────────
def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Caméra introuvable — vérifie le branchement USB")
        sys.exit(1)
    print("✅ Caméra ouverte !")
    print("")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  Système prêt — Présente un déchet !")
    print("  Ctrl+C pour arrêter")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    historique = deque(maxlen=12)
    votes      = deque(maxlen=10)

    try:
        while True:
            # Vérifier présence déchet
            distance = mesure_distance()
            if distance > 20:
                eteindre_leds()
                time.sleep(0.2)
                continue

            # Capturer image
            ret, frame = cap.read()
            if not ret:
                continue

            # Extraire ROI centre 80%
            h, w = frame.shape[:2]
            s  = int(min(h, w) * 0.8)
            cx, cy = w // 2, h // 2
            y1, y2 = cy - s//2, cy + s//2
            x1, x2 = cx - s//2, cx + s//2
            roi = frame[y1:y2, x1:x2]

            # Prédiction
            inp = preprocess(roi)
            out = session.run(None, {"input": inp})[0][0]
            probas = softmax(out)

            # Lissage temporel
            historique.append(probas)
            probas_lissees = np.mean(historique, axis=0)
            idx = int(np.argmax(probas_lissees))
            cat = CLASSES[idx]
            pct = float(probas_lissees[idx]) * 100

            # Système de votes
            if pct >= SEUILS[cat]:
                votes.append(cat)
            else:
                votes.append('inconnu')

            # Vérification majorité
            if len(votes) == 10:
                compteur = {}
                for v in votes:
                    compteur[v] = compteur.get(v, 0) + 1
                classe_maj = max(compteur, key=compteur.get)

                if classe_maj != 'inconnu' and compteur[classe_maj] >= 7:
                    print(f"")
                    print(f"┌─────────────────────────────┐")
                    print(f"│  ✅ DÉTECTÉ : {classe_maj.upper():<14} │")
                    print(f"│  Confiance  : {pct:.1f}%{' '*(12-len(f'{pct:.1f}'))}│")
                    print(f"└─────────────────────────────┘")

                    # Allumer LED correspondante
                    allumer_led(classe_maj)

                    # Sauvegarder en base
                    sauvegarder(classe_maj, pct)

                    # Attendre que l'utilisateur dépose le déchet
                    time.sleep(3)
                    eteindre_leds()

                    # Reset
                    votes.clear()
                    historique.clear()
                else:
                    print(f"  🔍 Analyse... {cat} ({pct:.1f}%)", end='\r')

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\n\n🛑 Arrêt du système.")
        cap.release()
        eteindre_leds()
        if GPIO_AVAILABLE:
            GPIO.cleanup()
        print("✅ Arrêt propre.")

if __name__ == "__main__":
    main()
