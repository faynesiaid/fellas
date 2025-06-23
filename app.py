from flask import Flask, render_template, jsonify, request, redirect, url_for
import requests
import pytchat
import threading
import time
import random

app = Flask(__name__)

# Ganti dengan URL Firebase Anda
FIREBASE_URL = "https://gamecube-f70c7-default-rtdb.firebaseio.com"

### 🔧 FUNGSI FIREBASE ###

def add_name(name):
    requests.post(f"{FIREBASE_URL}/names.json", json=name)

def get_names():
    res = requests.get(f"{FIREBASE_URL}/names.json")
    data = res.json()
    return list(data.values()) if data else []

def remove_name(name_to_remove):
    res = requests.get(f"{FIREBASE_URL}/names.json")
    data = res.json()
    if not data:
        return
    for key, value in data.items():
        if value == name_to_remove:
            requests.delete(f"{FIREBASE_URL}/names/{key}.json")
            break

def get_random_names():
    res = requests.get(f"{FIREBASE_URL}/random_names.json")
    return res.json() or []

def get_video_id():
    res = requests.get(f"{FIREBASE_URL}/config/video_id.json")
    return res.json()

def set_video_id(video_id):
    requests.put(f"{FIREBASE_URL}/config/video_id.json", json=video_id)

### 🔧 FLASK ROUTES ###

@app.route('/')
def input_page():
    return render_template("input.html")  # form masukkan video ID

@app.route('/set_video_id', methods=['POST'])
def set_video_id_route():
    new_id = request.form.get("video_id")
    if not new_id:
        return "No video ID provided", 400
    set_video_id(new_id)
    return redirect(url_for('index_game'))

@app.route('/game')
def index_game():
    return render_template('index.html')

@app.route('/names')
def get_names_route():
    return jsonify(get_names())

@app.route('/remove_name', methods=['POST'])
def remove_name_route():
    name = request.json.get("name")
    if name:
        remove_name(name.strip())
        return jsonify({"status": "removed"})
    return jsonify({"status": "no name provided"}), 400

### 🔄 POLLING CHAT YOUTUBE ###
def polling_chat():
    video_id = get_video_id()
    if not video_id:
        print("❌ Video ID belum diatur.")
        return

    print(f"▶️ Mulai polling chat untuk video: {video_id}")

    try:
        chat = pytchat.create(video_id=video_id)

        if not chat.is_alive():
            print("❌ Chat tidak aktif (mungkin video tidak live atau ID salah).")
            return

        last_message_time = time.time()

        while chat.is_alive():
            try:
                found_chat = False
                print("💤 Polling aktif... menunggu pesan...")
                for c in chat.get().sync_items():
                    message = c.message.strip()
                    if len(message.split()) == 1 and len(message) <= 8:
                        print(f"✅ Simpan dari chat: {message}")
                        add_name(message)
                        found_chat = True
                        last_message_time = time.time()
                        time.sleep(10)
                    else:
                        print(f"❌ Diabaikan: {message}")

                # fallback: tidak ada chat selama 15 detik
                if not found_chat and time.time() - last_message_time >= 15:
                    random_names = get_random_names()
                    if random_names:
                        random_name = random.choice(random_names)
                        print(f"🔄 Pakai nama random: {random_name}")
                        add_name(random_name)
                        last_message_time = time.time()
                    time.sleep(10)

            except Exception as e:
                print("❌ Error saat polling chat:", e)
                time.sleep(5)

    except Exception as e:
        print("❌ Gagal membuat objek chat:", e)

    print("🔚 polling_chat selesai. Program berhenti.")

### 🚀 INISIASI SAAT RUN ###
if __name__ == '__main__':
    def run_flask():
        app.run(host='0.0.0.0', port=5000)

    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Tunggu video_id sebelum mulai polling
    while not get_video_id():
        print("⏳ Menunggu video ID diatur melalui /set_video_id ...")
        time.sleep(2)

    polling_chat()
