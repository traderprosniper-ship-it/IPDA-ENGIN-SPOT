import ccxt
import pandas as pd
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
import threading
import requests

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION TELEGRAM ---
BOT_TOKEN = "8704495077:AAGVKBgbx6N9WI6xaZ6SPy8xsuvZfSGksuI"
CHAT_ID = "6727767271"

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Erreur Telegram: {e}")

class IFDASpotEngine:
    def __init__(self, ex_id, ak, secret, passph=None):
        config = {
            'apiKey': ak, 
            'secret': secret, 
            'enableRateLimit': True, 
            'options': {'defaultType': 'spot'} 
        }
        if passph: config['password'] = passph
        self.ex = getattr(ccxt, ex_id.lower())(config)
        self.is_running = False
        self.symbol = "BTC/USDT"
        self.amount_usdt = 10.0 # Valeur par défaut fixée à 10$
        self.logs = []

    def add_log(self, msg):
        log = f"[{time.strftime('%H:%M:%S')}] {msg}"
        self.logs.append(log)
        if len(self.logs) > 30: self.logs.pop(0)

    def run_spot_sniper(self):
        # On définit l'unité de temps sur H4 pour plus de puissance
        tf = '4h' 
        self.add_log(f"🟠 SNIPER SPOT H4 ACTIVÉ SUR {self.symbol}")
        send_telegram(f"🎯 <b>IFDA SPOT H4 DÉMARRÉ</b>\nStratégie: CRT Sniper\nMise: {self.amount_usdt} USDT\nMode: Accumulation")
        
        while self.is_running:
            try:
                # Récupération des bougies H4
                ohlcv = self.ex.fetch_ohlcv(self.symbol, timeframe=tf, limit=5)
                df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'c', 'v'])
                
                # B1: Bougie de référence (Range)
                # B2: Bougie actuelle (Sweep)
                b1_l = df['l'].iloc[-3] 
                b2_l = df['l'].iloc[-2] 
                b2_c = df['c'].iloc[-2] 

                # LOGIQUE : Sweep du Low H4 + Réintégration confirmée
                if b2_l < b1_l and b2_c > b1_l:
                    self.add_log(f"🎯 SIGNAL H4 DÉTECTÉ : Sweep de liquidité bas.")
                    
                    # ACHAT SPOT RÉEL (Mise par défaut 10$)
                    order = self.ex.create_market_buy_order(self.symbol, self.amount_usdt)
                    
                    confirm_msg = f"✅ <b>ACHAT SPOT H4 EXÉCUTÉ</b>\n\nSymbol: {self.symbol}\nMontant: {self.amount_usdt} USDT\nSignal: CRT Sweep Low H4"
                    self.add_log(f"✅ ACHAT H4 RÉUSSI : {self.amount_usdt} USDT investis.")
                    send_telegram(confirm_msg)
                    
                    # Pause longue (4 heures) pour éviter de reprendre le même signal
                    time.sleep(14400) 
                
                # Scan toutes les 5 minutes (suffisant pour du H4)
                time.sleep(300)
            except Exception as e:
                self.add_log(f"⚠️ Erreur : {str(e)}")
                time.sleep(60)

engine = None

@app.route('/toggle_bot', methods=['POST', 'OPTIONS'])
def toggle_bot():
    if request.method == 'OPTIONS': return jsonify({"status": "ok"})
    global engine
    data = request.json
    engine = IFDASpotEngine(data['exchange'], data['ak'], data['as'], data.get('passphrase'))
    
    if data.get('action') == 'start':
        # Si l'utilisateur ne précise rien, on prend 10$ par défaut
        engine.amount_usdt = float(data.get('qty')) if data.get('qty') else 10.0
        engine.is_running = True
        threading.Thread(target=engine.run_spot_sniper).start()
        return jsonify({"status": "RUNNING"})
    return jsonify({"status": "STOPPED"})

@app.route('/get_status', methods=['GET'])
def get_status():
    if engine:
        return jsonify({"logs": engine.logs, "running": engine.is_running})
    return jsonify({"logs": ["En attente de lancement H4..."]})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
  
