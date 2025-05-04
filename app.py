import telebot
from flask import Flask, render_template
import threading
import requests
import os
import time

API_TOKEN = '8037879919:AAFl_638ICK3peP0zs9HEJ8eMS_284eugAw'  # Ganti dengan token botmu
bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# Fungsi bantu
def format_size(bytes_size):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.2f} TB"

def format_time(seconds):
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h:
        return f"{h}h {m}m {s}s"
    elif m:
        return f"{m}m {s}s"
    else:
        return f"{s}s"

# Halaman status HTML
@app.route('/')
def index():
    return render_template('status.html')

# Bot Telegram
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Kirimkan link Doodstream dan saya akan proses untukmu!")

@bot.message_handler(func=lambda message: message.text.startswith("http"))
def handle_url(message):
    target_url = message.text.strip()
    api_url = "https://poopdl-api.dapuntaratya.com/get_file"
    headers = {"Content-Type": "application/json"}
    payload = {"url": [target_url]}

    try:
        response = requests.post(api_url, headers=headers, json=payload)
        result = response.json()

        if result.get("status") == "success":
            data = result.get("data", [{}])[0]
            filename = data.get("filename", "video.mp4").replace("/", "_")
            download_url = data.get("video_url", "")
            size = data.get("size", "No Size")
            duration = data.get("duration", "No Duration")
            upload_date = data.get("upload_date", "No Upload Date")

            caption = (
                f"📝 *Judul:* {filename}\n"
                f"⏱️ *Durasi:* {duration}\n"
                f"📦 *Ukuran:* {size}\n"
                f"📅 *Tanggal Upload:* {upload_date}"
            )

            video_response = requests.get(download_url, stream=True)
            total_size = int(video_response.headers.get('content-length', 0))
            chunk_size = 8192
            local_path = f"{filename}"
            done = 0
            start_time = time.time()

            with open(local_path, 'wb') as video_file:
                for chunk in video_response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        video_file.write(chunk)
                        done += len(chunk)

            with open(local_path, 'rb') as video_file:
                bot.send_video(message.chat.id, video=video_file, caption=caption, parse_mode="Markdown")

            os.remove(local_path)
        else:
            bot.reply_to(message, f"Gagal: {result.get('message', 'Terjadi kesalahan.')}")
    except Exception as e:
        bot.reply_to(message, f"Terjadi error: {str(e)}")

# Thread untuk menjalankan polling
def run_bot():
    print("Bot is running...")
    bot.infinity_polling()

# Jalankan bot di thread terpisah
threading.Thread(target=run_bot).start()

# Jalankan Flask app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))