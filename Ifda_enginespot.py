import ccxt
import pandas as pd
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
import threading
import requests

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION LABO ---
BOT_TOKEN = "8704495077:AAGVKBgbx6N9WI6xaZ6SPy8xsuvZfSGksuI"
CHAT_ID = "6727767271"

# Liste des 50 actifs (IA, RWA, DePIN, Leaders)
NARRATIVES = {
    "IA": ["FET/USDT", "RENDER/USDT", "TAO/USDT", "AGIX/USDT", "OCEAN/USDT", "AKT/USDT", "NEAR/USDT", "GRT/USDT", "AIOZ/USDT", "ARKM/USDT", "WLD/USDT", "GLM/USDT", "NOS/USDT", "THETA/USDT", "RNDR/USDT"],
    "RWA": ["ONDO/USDT", "PENDLE/USDT", "OM/USDT", "MKR/USDT", "CFG/USDT", "SNX/USDT", "POLYX/USDT", "TRU/USDT", "GFI/USDT", "RIO/USDT", "CTC/USDT", "CVP/USDT", "MPL/USDT", "CHNG/USDT", "LTO/USDT"],
    "DEPIN": ["HNT/USDT", "AR/USDT", "FIL/USDT", "IOTX/USDT", "JASMY/USDT", "LPT/USDT", "POKT/USDT", "SHDW/USDT", "MOBILE/USDT", "HONEY/USDT", "DIMO/USDT", "NODL/USDT", "WIFI/USDT", "SC/USDT", "STORJ/USDT"],
    "MARKET": ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "AVAX/USDT"]
}

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
        requests.post(url, json=payload)
    except: pass

class BlackSniperSpot:
    def __init__(self, ex_id, ak, secret, passph=None):
        config = {'apiKey': ak, 'secret': secret, 'enableRateLimit': True, 'options': {'defaultType': 'spot'}}
        if passph: config['password'] = passph
        self.ex = getattr(ccxt, ex_id.lower())(config)
        self.is_running = False
        self.amount_usdt = 10.0 # Valeur par défaut
        self.logs = []

    def add_log(self, msg):
        log = f"[{time.strftime('%H:%M:%S')}] {msg}"
        self.logs.append(log)
        if len(self.logs) > 30: self.logs.pop(0)

    def check_confluence(self, df):
        """ Vérifie la présence d'un FVG ou d'un Order Block sous le prix """
        # Logique simplifiée : Un FVG existe si High[i-2] < Low[i]
        last_low = df['l'].iloc[-1]
        prev_high = df['h'].iloc[-3]
        return last_low > prev_high # Détecte un gap de prix (FVG)

    def check_crt_precision(self, symbol, tf):
        """ Stratégie Sweep + Réintégration + Rejet PD Array """
        try:
            ohlcv = self.ex.fetch_ohlcv(symbol, timeframe=tf, limit=10)
            df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'c', 'v'])
            
            b1_h, b1_l = df['h'].iloc[-3], df['l'].iloc[-3]
            b2_h, b2_l, b2_c = df['h'].iloc[-2], df['l'].iloc[-2], df['c'].iloc[-2]

            # 1. SWEEP DU LOW (Liquidité)
            sweep = b2_l < b1_l
            # 2. RÉINTÉGRATION (Clôture dans le range de B1)
            reintegration = b2_c > b1_l and b2_c < b1_h
            # 3. REJET PD ARRAY (FVG/OB)
            rejet_pd_array = self.check_confluence(df)

            return sweep and reintegration and rejet_pd_array
        except: return False

    def run_engine(self):
        self.add_log("🚀 Labo SANGMELIMA : Sniper Narratives Actif")
        send_telegram("🛰️ <b>BLACKSNIPER SPOT v3.5</b>\nScan Cascade: H4 -> H1 -> M30\nCibles: 50 Actifs (IA, RWA, DePIN)")

        while self.is_running:
            for cat, symbols in NARRATIVES.items():
                for symbol in symbols:
                    if not self.is_running: break
                    
                    # Cascade de Timeframes
                    for tf in ['4h', '1h', '30m']:
                        if self.check_crt_precision(symbol, tf):
                            self.add_log(f"🎯 SIGNAL {cat} : {symbol} ({tf})")
                            try:
                                # ACHAT SPOT
                                self.ex.create_market_buy_order(symbol, self.amount_usdt)
                                send_telegram(f"🎯 <b>SIGNAL {cat} CONFIRMÉ</b>\nActif: {symbol}\nUnité: {tf}\nStatut: Achat 10$ effectué.")
                                time.sleep(1800) # Pause de sécurité pour cet actif
                                break 
                            except Exception as e:
                                self.add_log(f"⚠️ Erreur solde sur {symbol}")
                    time.sleep(2) # Anti-ban API
            time.sleep(30)

engine = None

@app.route('/toggle_bot', methods=['POST', 'OPTIONS'])
def toggle_bot():
    if request.method == 'OPTIONS': return jsonify({"status": "ok"})
    global engine
    data = request.json
    engine = BlackSniperSpot(data['exchange'], data['ak'], data['as'], data.get('passphrase'))
    if data.get('action') == 'start':
        engine.amount_usdt = float(data.get('qty', 10))
        engine.is_running = True
        threading.Thread(target=engine.run_engine).start()
        return jsonify({"status": "RUNNING"})
    return jsonify({"status": "STOPPED"})

@app.route('/get_status', methods=['GET'])
def get_status():
    if engine: return jsonify({"logs": engine.logs, "running": engine.is_running})
    return jsonify({"logs": ["En attente..."]})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
            
