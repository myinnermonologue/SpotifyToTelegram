import os
import requests
import webbrowser
import time
import threading
from flask import Flask, request
from pyrogram import Client
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

# Читаем переменные
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")
TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID")
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH")
TELEGRAM_SESSION_NAME = os.getenv("TELEGRAM_SESSION_NAME")

# Flask-приложение
app_flask = Flask(__name__)

# Глобальная переменная для хранения refresh_token
refresh_token = None

# Telegram-клиент
tg_client = Client(TELEGRAM_SESSION_NAME, api_id=TELEGRAM_API_ID, api_hash=TELEGRAM_API_HASH)

@app_flask.route('/callback/', methods=['GET'])
def callback():
    """Обработчик авторизации Spotify"""
    global refresh_token

    code = request.args.get("code")
    if not code:
        return "❌ Ошибка: Код авторизации не найден", 400

    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": SPOTIFY_REDIRECT_URI,
        "client_id": SPOTIFY_CLIENT_ID,
        "client_secret": SPOTIFY_CLIENT_SECRET
    }

    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = requests.post("https://accounts.spotify.com/api/token", data=payload, headers=headers)

    if response.status_code == 200:
        data = response.json()
        refresh_token = data.get("refresh_token")
        if not refresh_token:
            return "❌ Ошибка: Spotify не дал refresh_token.", 400
        return "✅ Авторизация успешна!"
    else:
        return f"❌ Ошибка: {response.text}", 400


def get_access_token():
    """Запрашивает новый access_token при необходимости"""
    global refresh_token

    if not refresh_token:
        return None

    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": SPOTIFY_CLIENT_ID,
        "client_secret": SPOTIFY_CLIENT_SECRET
    }

    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = requests.post("https://accounts.spotify.com/api/token", data=payload, headers=headers)

    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        return None


def get_current_track():
    """Запрашивает текущий трек у Spotify API"""
    access_token = get_access_token()
    if not access_token:
        return "🔇 Нет данных о треке"

    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get("https://api.spotify.com/v1/me/player/currently-playing", headers=headers)

    if response.status_code == 200:
        data = response.json()
        track_name = data["item"]["name"]
        artist_name = data["item"]["artists"][0]["name"].split(',')[0]
        album_name = data["item"]["album"]["name"]
        return f"""Listening to: 💿 {track_name} - {artist_name} 💿  [{album_name}]"""
    else:
        return "Please insert a 💿 or 📀 format disc"


def update_telegram_bio():
    """Обновляет био в Telegram с текущим треком Spotify"""
    while True:
        try:
            status = get_current_track()
            max_bio_length = 70
            short_status = status if len(status) <= max_bio_length else status[:max_bio_length - 1] + "…"
            tg_client.update_profile(bio=short_status)
            print(f"✅ Обновлено био: {status}")
        except Exception as e:
            print(f"❌ Ошибка обновления био: {e}")
        time.sleep(30)  # Обновляем раз в 30 секунд


if __name__ == '__main__':
    threading.Thread(target=lambda: app_flask.run(port=8888, debug=False, use_reloader=False)).start()

    auth_url = (
        f"https://accounts.spotify.com/authorize"
        f"?client_id={SPOTIFY_CLIENT_ID}"
        f"&response_type=code"
        f"&redirect_uri={SPOTIFY_REDIRECT_URI}"
        f"&scope=user-read-currently-playing"
    )
    webbrowser.open(auth_url)
    print("🌐 Ожидание авторизации в браузере...")

    while not refresh_token:
        time.sleep(5)
    print("✅ Refresh Token загружен, теперь создаем Access Token по необходимости!")

    tg_client.start()
    update_telegram_bio()
