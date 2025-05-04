import telebot
from flask import Flask, render_template
import threading
import requests
import os
import re
import time
import datetime

API_TOKEN = '8037879919:AAEu8x9pGqzcVCZGPWYN5N9hR74zW-2IJ7U'
bot = telebot.TeleBot(API_TOKEN)
BOT_USERNAME = bot.get_me().username  # Ambil username bot
DEV_USERNAME = 'Nathanaeru'  # Username dev
app = Flask(__name__)

def escape_markdown(text):
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', str(text))

def format_size(bytes_size):
    for unit in ['B', 'KB', 'MB', 'GB']:
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
        return f"{h:02d}:{m:02d}:{s:02d}"
    else:
        return f"{m:02d}:{s:02d}"

@app.route('/')
def index():
    return render_template('status.html')

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Kirimkan link PoopHD dan saya akan mendownload")

@bot.message_handler(func=lambda m: m.text and m.text.startswith("http"))
def handle_url(message):
    target_url = message.text.strip()
    api_url = "https://poopdl-api.dapuntaratya.com/get_file"
    payload = {"url": [target_url]}

    try:
        result = requests.post(api_url, json=payload).json()
        if result.get("status") != "success":
            return bot.reply_to(message, f"Gagal") #: {result.get('message', 'Terjadi kesalahan.')}

        info = result['data'][0]
        filename = info.get('filename', 'video.mp4').replace('/', '_')
        download_url = info.get('video_url')
        total_size = int(requests.head(download_url).headers.get('content-length', 0))
        if not download_url or total_size == 0:
            return bot.reply_to(message, "Gagal mendapatkan URL video atau ukuran file tidak valid.")

        # Parsing duration raw 'MM:SS' atau 'HH:MM:SS'
        duration_raw = info.get('duration', '0:00')
        try:
            parts = list(map(int, duration_raw.split(':')))
            if len(parts) == 2:
                duration_secs = parts[0] * 60 + parts[1]
            elif len(parts) == 3:
                duration_secs = parts[0] * 3600 + parts[1] * 60 + parts[2]
            else:
                duration_secs = 0
        except:
            duration_secs = 0

        # Kirim pesan progress awal
        progress_msg = bot.send_message(message.chat.id, "Mulai mengunduh video...")

        local_path = filename
        done = 0
        start_time = time.time()
        last_update = start_time
        chunk_size = 8192

        with requests.get(download_url, stream=True) as r, open(local_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=chunk_size):
                if not chunk:
                    continue
                f.write(chunk)
                done += len(chunk)

                now = time.time()
                if now - last_update >= 2 or done == total_size:
                    percent = done / total_size * 100
                    filled = int(percent // 10)
                    empty = 10 - filled
                    bar = '█' * filled + '░' * empty
                    elapsed = now - start_time
                    speed = done / (elapsed + 1e-6)
                    eta = (total_size - done) / (speed + 1e-6)

                    progress_text = (
                        f"┏ 𝙁𝙄𝙇𝙀𝙉𝘼𝙈𝙀 : {filename}\n"
                        f"┠ [{bar}] {percent:.2f}%\n"
                        f"┠ ᴘʀᴏᴄᴇssᴇᴅ : {format_size(done)} ᴏғ {format_size(total_size)}\n"
                        f"┠ ʀᴇᴍᴀɪɴɪɴɢ : {format_time(eta)}\n"
                        f"┠ sᴘᴇᴇᴅ : {format_size(speed)}/s\n"
                        f"┠ ᴇʟᴀᴘsᴇᴅ : {format_time(elapsed)}\n"
                        f"┠ sᴛᴀᴛᴜs : Downloading...\n"
                        f"┗ ʟᴇᴇᴄʜᴇᴅ : @{BOT_USERNAME} ({message.from_user.id})"
                    )
                    try:
                        bot.edit_message_text(
                            progress_text,
                            chat_id=message.chat.id,
                            message_id=progress_msg.message_id,
                        )
                    except:
                        pass
                    last_update = now

        # Format tanggal upload
        upload_date = info.get('upload_date', 'Unknown')
        try:
            dt = datetime.datetime.strptime(upload_date, '%Y-%m-%d')
            upload_date = dt.strftime('%d %B %Y')
        except:
            pass

        # Caption info
        caption = (
            "━━━━━━━━━━━━━━━━━━\n"
            f"📁 ID : {info.get('id')}\n"
            f"📝 Name : {filename}\n"
            f"⏱️ Duration : {duration_raw}\n"
            f"📦 Size : {format_size(total_size)}\n"
            f"📅 Upload Date : {upload_date}\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"Bot : @{BOT_USERNAME}\n"
            f"Dev : @{DEV_USERNAME}"
        )

        # Kirim video atau dokumen sesuai size
        with open(local_path, 'rb') as vid:
            if total_size <= 50 * 1024 * 1024:
                bot.send_video(message.chat.id, video=vid, caption=caption, duration=duration_secs)
            else:
                bot.send_document(message.chat.id, document=vid, caption=caption)

        # Kirim ucapan terima kasih
        bot.send_message(message.chat.id, "Jangan Di Spam karena server gratisan jika berkenan bisa sumbang vps atau donasi boleh 🦊")

        # Cleanup
        os.remove(local_path)

    except Exception as e:
        bot.reply_to(message, f"Terjadi error") #: {e}


def run_bot():
    bot.infinity_polling()

threading.Thread(target=run_bot).start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))