import os
import time
import subprocess
import threading
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = '7759797980:AAHV-FKBXJT10q-d1AEYf0mpHmRubdrzQwE'
ADMIN_ID = 8179218740

# To save wallet/token simply in memory for demo (you can save in file/db)
user_data = {}

# Mining jobs tracker per user:
# Structure: {user_id: [ { 'proc': Popen object, 'start_time': timestamp, 'hashes': int }, ... ]}
mining_jobs = {}

# Lock for thread safety
jobs_lock = threading.Lock()

def start_mining_process(wallet, token):
    # Replace this command with your real mining command
    # Example dummy command that runs infinite loop (simulate mining)
    # Using yes command to simulate CPU load, redirected to null
    return subprocess.Popen(['yes'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

async def start_mining(user_id, wallet, token):
    with jobs_lock:
        # If user already has mining jobs running, stop them first
        if user_id in mining_jobs:
            for job in mining_jobs[user_id]:
                try:
                    job['proc'].terminate()
                except:
                    pass
            mining_jobs[user_id] = []

        mining_jobs[user_id] = []
        for _ in range(4):  # Start 4 mining jobs
            proc = start_mining_process(wallet, token)
            job_info = {
                'proc': proc,
                'start_time': time.time(),
                'hashes': 0  # will simulate hashes
            }
            mining_jobs[user_id].append(job_info)

        # Start a thread to simulate hashes counting
        def simulate_hashes():
            while True:
                time.sleep(1)
                with jobs_lock:
                    if user_id not in mining_jobs or len(mining_jobs[user_id]) == 0:
                        break
                    for job in mining_jobs[user_id]:
                        if job['proc'].poll() is not None:
                            # Process ended, remove it
                            mining_jobs[user_id].remove(job)
                            continue
                        # Increase hashes by random approx 1000 per second
                        job['hashes'] += 1000

        threading.Thread(target=simulate_hashes, daemon=True).start()

async def wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if len(context.args) != 1:
        await update.message.reply_text("❌ Please provide your XMR wallet address:\n/wallet <your_xmr_wallet>")
        return
    wallet_addr = context.args[0]

    if user_id not in user_data:
        user_data[user_id] = {}

    user_data[user_id]['wallet'] = wallet_addr
    await update.message.reply_text(f"✅ Wallet saved: {wallet_addr}")

    # If token already set, start mining
    if 'token' in user_data[user_id]:
        await start_mining(user_id, wallet_addr, user_data[user_id]['token'])
        await update.message.reply_text("🚀 Mining started with 4 jobs!")

async def token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if len(context.args) != 1:
        await update.message.reply_text("❌ Please provide your GitHub token:\n/token <your_github_token>")
        return
    token_val = context.args[0]

    if user_id not in user_data:
        user_data[user_id] = {}

    user_data[user_id]['token'] = token_val
    await update.message.reply_text(f"✅ GitHub token saved.")

    # If wallet already set, start mining
    if 'wallet' in user_data[user_id]:
        await start_mining(user_id, user_data[user_id]['wallet'], token_val)
        await update.message.reply_text("🚀 Mining started with 4 jobs!")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    with jobs_lock:
        if user_id not in mining_jobs or len(mining_jobs[user_id]) == 0:
            await update.message.reply_text("⚠️ No mining jobs are currently running for you.")
            return

        total_hashes = 0
        total_uptime = 0
        running_jobs = 0

        for job in mining_jobs[user_id]:
            if job['proc'].poll() is None:
                running_jobs += 1
                total_hashes += job['hashes']
                total_uptime += time.time() - job['start_time']

        if running_jobs == 0:
            await update.message.reply_text("⚠️ All mining jobs have stopped.")
            return

        avg_uptime = total_uptime / running_jobs
        # Hashrate approx = total hashes / uptime in seconds
        hashrate = total_hashes / avg_uptime if avg_uptime > 0 else 0

        status_msg = (
            f"⛏️ Mining Status:\n"
            f"Running jobs: {running_jobs}\n"
            f"Total Hashes: {total_hashes}\n"
            f"Average Uptime: {int(avg_uptime)} seconds\n"
            f"Approx. Hashrate: {int(hashrate)} hashes/sec"
        )
        await update.message.reply_text(status_msg)

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    with jobs_lock:
        if user_id not in mining_jobs or len(mining_jobs[user_id]) == 0:
            await update.message.reply_text("⚠️ No mining jobs running.")
            return

        for job in mining_jobs[user_id]:
            try:
                job['proc'].terminate()
            except:
                pass
        mining_jobs[user_id] = []
    await update.message.reply_text("🛑 Mining stopped.")

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Use /wallet and /token commands to set wallet and token and start mining automatically.")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "⚙️ Commands:\n"
        "/wallet <XMR_wallet> - Save your Monero wallet address and start mining if token set\n"
        "/token <GitHub_token> - Save your GitHub token and start mining if wallet set\n"
        "/status - Check mining status (uptime, hashes, hashrate)\n"
        "/stop - Stop all mining jobs\n"
        "/help - Show this help"
    )
    await update.message.reply_text(help_text)

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("wallet", wallet))
    app.add_handler(CommandHandler("token", token))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("help", help_cmd))

    print("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
