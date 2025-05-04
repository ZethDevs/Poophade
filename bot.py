import telebot
from flask import Flask, render_template
import threading
import requests
import os
import re
import time

API_TOKEN = '8037879919:AAEu8x9pGqzcVCZGPWYN5N9hR74zW-2IJ7U'
bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# Escape MarkdownV2 reserved characters
def escape_markdown(text):
    escape_chars = r'_*[]()~`>#+\-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', str(text))

# Format file size
def format_size(bytes_size):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.2f} TB"

# Format time duration
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

# Build a text-based progress bar
def build_progress_bar(percent, length=10):
    filled_len = int(length * percent // 100)
    bar = '█' * filled_len + '░' * (length - filled_len)
    return bar

@app.route('/')
def index():
    return render_template('status.html')

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Kirimkan link Doodstream dan saya akan proses untukmu!")

@bot.message_handler(func=lambda message: message.text.startswith("http"))
def handle_url(message):
    chat_id = message.chat.id
    target_url = message.text.strip()
    api_url = "https://poopdl-api.dapuntaratya.com/get_file"
    headers = {"Content-Type": "application/json"}
    payload = {"url": [target_url]}

    try:
        resp = requests.post(api_url, headers=headers, json=payload)
        result = resp.json()
        if result.get("status") != "success":
            return bot.reply_to(message, f"Gagal: {result.get('message', 'Terjadi kesalahan.')}")

        data = result.get('data', [{}])[0]
        filename = data.get('filename', 'video.mp4').replace('/', '_')
        download_url = data.get('video_url')
        total_size_str = data.get('size', '0')
        total_size = int(data.get('size_bytes', 0))
        duration = data.get('duration', 'No Duration')
        upload_date = data.get('upload_date', 'No Upload Date')
        idfile = data.get('id', '')

        # Initial progress message
        raw_initial = (
            f"┏ 𝙁𝙄𝙇𝙀𝙉𝘼𝙈𝙀 : {filename}\n"
            f"┗ [░░░░░░░░░░] 0.00%"
        )
        initial_text = escape_markdown(raw_initial)
        prog_msg = bot.send_message(chat_id, initial_text, parse_mode="MarkdownV2")

        # Download
        r = requests.get(download_url, headers={"User-Agent": "Mozilla/5.0"}, stream=True)
        if total_size == 0:
            total_size = int(r.headers.get('content-length', 0))
        chunk_size = 1024 * 8
        done = 0
        start_time = time.time()
        last_update_time = start_time
        local_path = filename

        with open(local_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=chunk_size):
                if not chunk:
                    continue
                f.write(chunk)
                done += len(chunk)

                now = time.time()
                if now - last_update_time >= 3:  # update setiap 3 detik
                    percent = done / total_size * 100 if total_size else 0
                    bar = build_progress_bar(percent)
                    elapsed = now - start_time
                    speed = done / elapsed if elapsed > 0 else 0
                    remaining = (total_size - done) / speed if speed > 0 else 0

                    raw_text = (
                        f"┏ ғɪʟᴇɴᴀᴍᴇ : {filename}\n"
                        f"┠ [{bar}] {percent:.2f}%\n"
                        f"┠ ᴘʀᴏᴄᴇssᴇᴅ : {format_size(done)} ᴏғ {format_size(total_size)}\n"
                        f"┠ ʀᴇᴍᴀɪɴɪɴɢ : {format_time(remaining)}\n"
                        f"┠ sᴘᴇᴇᴅ : {format_size(speed)}/s\n"
                        f"┠ ᴇʟᴀᴘsᴇᴅ : {format_time(elapsed)}\n"
                        f"┠ sᴛᴀᴛᴜs : Downloading...\n"
                        f"┗ ʟᴇᴇᴄʜᴇᴅ : @{message.from_user.username or 'User'} ({message.from_user.id})"
                    )
                    safe_text = escape_markdown(raw_text)
                    try:
                        bot.edit_message_text(safe_text, chat_id, prog_msg.message_id, parse_mode="MarkdownV2")
                    except Exception:
                        pass

                    last_update_time = now

        # Send final video
        with open(local_path, 'rb') as video_file:
            caption = (
                f"*━━━━━━━━━━━━━━━━━━*\n"
                f"📁 *ID :* `{escape_markdown(idfile)}`\n"
                f"📝 *Name :* `{escape_markdown(filename)}`\n"
                f"⏱️ *Duration :* `{escape_markdown(duration)}`\n"
                f"📦 *Size :* `{escape_markdown(total_size_str)}`\n"
                f"📅 *Upload Date :* `{escape_markdown(upload_date)}`\n"
                f"*━━━━━━━━━━━━━━━━━━*\n"
                f"*Bot :* @YourBotName\n*Dev :* @Nathanaeru"
            )
            bot.send_video(chat_id, video=video_file, caption=caption, parse_mode="MarkdownV2")

        os.remove(local_path)
    except Exception as e:
        err = escape_markdown(str(e))
        bot.reply_to(message, f"Terjadi error: {err}")


def run_bot():
    print("Bot is running...")
    bot.infinity_polling()

if __name__ == '__main__':
    threading.Thread(target=run_bot).start()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
