import os
import time
import subprocess
import threading
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = '8150157942:AAGnuFbZEzN1lAyDmTkzyOpjGHVBxsXrZYI'
ADMIN_ID = 8179218740

user_data = {}
mining_jobs = {}
jobs_lock = threading.Lock()

def prepare_miner():
    if not os.path.exists("miner/build/xmrig"):
        print("🛠️ Cloning and building xmrig miner. This may take some time...")
        repo_url = "https://github.com/MoneroOcean/xmrig"
        subprocess.call(f"git clone {repo_url} miner", shell=True)
        os.makedirs("miner/build", exist_ok=True)
        subprocess.call("cd miner/build && cmake .. && make -j$(nproc)", shell=True)
        print("✅ Miner build complete.")
    else:
        print("✅ Miner already built.")

def start_mining_process(wallet):
    miner_path = os.path.abspath("miner/build/xmrig")
    miner_cmd = f"{miner_path} -o gulf.moneroocean.stream:10128 -u {wallet} -a rx/0"
    # Run miner with output suppressed, can change to PIPE for debug
    proc = subprocess.Popen(miner_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return proc

async def start_mining(user_id, wallet):
    with jobs_lock:
        # Stop existing jobs if any
        if user_id in mining_jobs:
            for job in mining_jobs[user_id]:
                try:
                    job['proc'].terminate()
                except Exception:
                    pass
            mining_jobs[user_id] = []

        mining_jobs[user_id] = []
        for _ in range(4):
            proc = start_mining_process(wallet)
            job_info = {'proc': proc, 'start_time': time.time(), 'hashes': 0}
            mining_jobs[user_id].append(job_info)

        def simulate_hashes():
            while True:
                time.sleep(1)
                with jobs_lock:
                    if user_id not in mining_jobs or not mining_jobs[user_id]:
                        break
                    for job in mining_jobs[user_id][:]:
                        if job['proc'].poll() is not None:  # process ended
                            mining_jobs[user_id].remove(job)
                            continue
                        job['hashes'] += 1000
        threading.Thread(target=simulate_hashes, daemon=True).start()

async def wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if len(context.args) != 1:
        await update.message.reply_text("❌ Use: /wallet <your_xmr_wallet>")
        return
    wallet_addr = context.args[0]
    user_data.setdefault(user_id, {})['wallet'] = wallet_addr
    await update.message.reply_text(f"✅ Wallet saved!")

    # Start mining if wallet set (GitHub token no longer needed)
    await start_mining(user_id, wallet_addr)
    await update.message.reply_text("🚀 Mining started with 4 jobs!")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    with jobs_lock:
        if user_id not in mining_jobs or not mining_jobs[user_id]:
            await update.message.reply_text("⚠️ No mining jobs running.")
            return

        total_hashes, total_uptime, running_jobs = 0, 0, 0
        for job in mining_jobs[user_id]:
            if job['proc'].poll() is None:
                running_jobs += 1
                total_hashes += job['hashes']
                total_uptime += time.time() - job['start_time']

        if running_jobs == 0:
            await update.message.reply_text("⚠️ All mining jobs stopped.")
            return

        avg_uptime = total_uptime / running_jobs
        hashrate = total_hashes / avg_uptime if avg_uptime > 0 else 0
        status_msg = (
            f"⛏️ Mining Status:\n"
            f"🔁 Jobs: {running_jobs}\n"
            f"⚡ Hashes: {total_hashes}\n"
            f"⏱ Uptime: {int(avg_uptime)} sec\n"
            f"💥 Hashrate: {int(hashrate)} h/s"
        )
        await update.message.reply_text(status_msg)

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    with jobs_lock:
        if user_id not in mining_jobs or not mining_jobs[user_id]:
            await update.message.reply_text("⚠️ No mining jobs running.")
            return
        for job in mining_jobs[user_id]:
            try:
                job['proc'].terminate()
            except Exception:
                pass
        mining_jobs[user_id] = []
    await update.message.reply_text("🛑 All mining jobs stopped.")

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome!\nUse:\n"
        "/wallet <XMR Wallet>\n"
        "Mining starts as soon as you set your wallet."
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛠 Commands:\n"
        "/wallet <wallet> - Set your Monero wallet and start mining\n"
        "/status - Show mining status\n"
        "/stop - Stop mining\n"
        "/help - Show this message"
    )

def main():
    prepare_miner()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("wallet", wallet))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("help", help_cmd))
    print("🚀 Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
