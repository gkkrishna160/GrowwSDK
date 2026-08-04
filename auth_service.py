from flask import Flask, jsonify
from growwapi import GrowwAPI
import pyotp
import time
from threading import Lock
import os
from dotenv import load_dotenv

load_dotenv()

GROWW_API_KEY = os.getenv("GROWW_API_KEY")
GROWW_SECRET = os.getenv("GROWW_SECRET")
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_SECRET = os.getenv("BINANCE_SECRET")

app = Flask(__name__)

# ===================== TOKEN STATE =====================

access_token = None
token_created_at = 0

TOKEN_TTL_SECONDS = 30 * 60
token_lock = Lock()

# ===================== HELPERS =====================

def is_token_valid():
    if access_token is None:
        return False
    return (time.time() - token_created_at) < TOKEN_TTL_SECONDS


def generate_new_token():
    global access_token, token_created_at

    if not GROWW_API_KEY or not GROWW_SECRET:
        raise RuntimeError("Missing GROWW_API_KEY or GROWW_SECRET")

    totp = pyotp.TOTP(GROWW_SECRET).now()
    access_token = GrowwAPI.get_access_token(
        api_key=GROWW_API_KEY,
        totp=totp
    )
    token_created_at = time.time()
    print(f"[AUTH] New token generated at {time.ctime(token_created_at)}")
    return access_token

# ===================== ROUTES =====================

@app.route("/token")
def get_token():
    global access_token, token_created_at

    with token_lock:
        if is_token_valid():
            age = int(time.time() - token_created_at)
            print(f"[AUTH] Serving cached token (age={age}s)")
            return jsonify({"access_token": access_token})

        try:
            token = generate_new_token()
            return jsonify({"access_token": token})

        except Exception as e:
            access_token = None
            token_created_at = 0
            print("[AUTH] Token generation failed:", str(e))
            return jsonify({"error": str(e)}), 503


@app.route("/invalidate-token")
def invalidate_token():
    global access_token, token_created_at

    with token_lock:
        access_token = None
        token_created_at = 0
        print("[AUTH] Token invalidated manually")

    return jsonify({"status": "ok"})

# ===================== MAIN =====================

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)