import logging
import telebot
import requests
import tempfile
import os
import time
import threading
from flask import Flask, render_template_string
from poop_download import PoopDownload  # Ensure PoopDownload is in poop_download.py or adjust import accordingly

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# Telegram bot token (replace with your actual bot token)
BOT_TOKEN = "8037879919:AAG8QzbX8SiE4qwpTugXoAlYZm4eNw6Ruw8"
if BOT_TOKEN.startswith("YOUR_BOT_TOKEN"):  # simple check to remind
    raise RuntimeError("Please replace BOT_TOKEN with your actual Telegram BOT_TOKEN.")

# Initialize Telebot
bot = telebot.TeleBot(BOT_TOKEN)

# Flask app for status
app = Flask(__name__)
start_time = time.time()

STATUS_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Telegram Bot Status</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; margin-top: 50px; }
        .status { font-size: 2em; color: green; }
        .uptime { margin-top: 20px; font-size: 1.2em; }
    </style>
</head>
<body>
    <h1>Telegram Bot Status</h1>
    <div class="status">Active &#10004;</div>
    <div class="uptime">Uptime: {{ uptime }}</div>
</body>
</html>
'''

def format_uptime(seconds: float) -> str:
    mins, secs = divmod(int(seconds), 60)
    hours, mins = divmod(mins, 60)
    return f"{hours}h {mins}m {secs}s"

@app.route('/')
def status():
    uptime = time.time() - start_time
    return render_template_string(STATUS_TEMPLATE, uptime=format_uptime(uptime))

# Helper functions from original bot
def escape_markdown(text):
    escape_chars = r'\_*[]()~`>#+-=|{}.!'
    return ''.join('\\' + c if c in escape_chars else c for c in text)

def format_time(seconds: float) -> str:
    mins, secs = divmod(int(seconds), 60)
    return f"{mins:02d}:{secs:02d}"

# Bot command handlers from original code
@bot.message_handler(commands=["start"])
def handle_start(message):
    bot.reply_to(
        message,
        "Halo! Kirimkan saya URL video atau folder PoopHD, dan saya akan mengambil video untuk Anda.\n"
        "Gunakan perintah /download <url1> [url2 ...] untuk memulai."
    )

@bot.message_handler(commands=["download"])
def handle_download(message):
    parts = message.text.strip().split()
    urls = parts[1:]
    if not urls:
        return bot.reply_to(message, "Mohon sertakan setidaknya satu URL PoopHD setelah perintah /download.")

    downloader = PoopDownload()
    # status message placeholder
    status_msg = bot.reply_to(message, "Memproses...")

    downloader.execute(urls if len(urls) > 1 else urls[0])
    result = downloader.result

    if result['status'] != 'success' or not result['data']:
        bot.delete_message(chat_id=status_msg.chat.id, message_id=status_msg.message_id)
        return bot.send_message(
            chat_id=message.chat.id,
            text="Maaf, saya tidak dapat mengunduh video dari URL yang diberikan."
        )

    # Process each video with progress
    for item in result['data']:
        filename = item.get('filename', 'Unknown')
        url = item.get('video_url')
        if not url:
            continue

        # request headers to get total size
        resp_head = requests.head(url)
        total = int(resp_head.headers.get('Content-Length', 0))

        # start download
        response = requests.get(url, stream=True)
        response.raise_for_status()

        processed = 0
        start_dl = time.time()
        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")

        try:
            for chunk in response.iter_content(chunk_size=1024*1024):  # 1MB chunks
                if not chunk:
                    break
                tmp_file.write(chunk)
                processed += len(chunk)

                # compute progress
                percent = (processed / total * 100) if total else 0
                bar_len = 10
                filled = int(bar_len * percent / 100)
                bar = '█' * filled + '─' * (bar_len - filled)
                elapsed = time.time() - start_dl
                speed = processed / elapsed if elapsed > 0 else 0
                remaining = (total - processed) / speed if speed > 0 else 0

                text = (
                    f"┏ 𝙁𝙄𝙇𝙀𝙉𝘼𝙈𝙀 : {filename}\n"
                    f"┠ [{bar}] {percent:6.2f}%\n"
                    f"┠ ᴘʀᴏᴄᴇssᴇᴅ : {processed/1024/1024:5.2f} MB ᴏғ {total/1024/1024:5.2f} MB\n"
                    f"┠ ʀᴇᴍᴀɪɴɪɴɢ : {format_time(remaining)}\n"
                    f"┠ sᴘᴇᴇᴅ : {speed/1024/1024:5.2f} MB/s\n"
                    f"┠ ᴇʟᴀᴘsᴇᴅ : {format_time(elapsed)}\n"
                    f"┗  sᴛᴀᴛᴜs : Downloading..."
                )
                bot.edit_message_text(
                    text,
                    chat_id=status_msg.chat.id,
                    message_id=status_msg.message_id
                )

            tmp_file.close()
            # send video
            with open(tmp_file.name, 'rb') as video_file:
                bot.send_video(
                    chat_id=message.chat.id,
                    video=video_file,
                    caption = (
        "*━━━━━━━━━━━━━━━━━━*\n"
        f"*Judul :* `{escape_markdown(item['filename'])}`\n"
        f"*Ukuran :* `{escape_markdown(item['size'])}`\n"
        f"*Durasi :* `{escape_markdown(item['duration'])}`\n"
        f"*Diunggah :* `{escape_markdown(item['upload_date'])}`\n"
        "*━━━━━━━━━━━━━━━━━━*\n"
        "*Bot :* @NathanPoopHD_bot\n*Dev :* @Nathanaeru"
                    ),
                    parse_mode="MarkdownV2"
                )

                bot.send_message(
                    chat_id=message.chat.id,
                    text="Jangan di spam vps gratisan ntar mati, kalo suka dgn bot nya bisa sumbang vps / donasi 😸"
                )

        except Exception as e:
            logging.warning(f"Error during download/send: {e}")
            bot.send_message(
                chat_id=message.chat.id,
                text=f"Error: {e}"
            )
        finally:
            try:
                os.remove(tmp_file.name)
            except:
                pass

    # delete status message when done
    bot.delete_message(chat_id=status_msg.chat.id, message_id=status_msg.message_id)

@bot.message_handler(commands=["help"])
def handle_help(message):
    bot.reply_to(
        message,
        "Penggunaan:\n"
        "/download <url1> [url2 ...] - Unduh video dengan progress bar dan kirim ke Telegram.\n"
        "/help - Tampilkan pesan bantuan."
    )

if __name__ == '__main__':
    # Run bot polling in a separate thread
    bot_thread = threading.Thread(target=lambda: bot.polling(none_stop=True), daemon=True)
    bot_thread.start()
    # Run Flask app
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))