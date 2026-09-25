import os
import sys
import time
import argparse
from datetime import datetime
from dotenv import load_dotenv

import instaloader
from database import init_db, process_follower_update, get_current_stored_followers
from telegram_notifier import TelegramNotifier

# Load configuration from .env file
load_dotenv()

IG_USERNAME = os.getenv("IG_USERNAME", "").strip()
TARGET_ACCOUNT = os.getenv("TARGET_ACCOUNT", "").strip() or IG_USERNAME
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
NOTIFY_NEW_FOLLOWERS = os.getenv("NOTIFY_NEW_FOLLOWERS", "false").lower() in ("true", "1", "yes")
NOTIFY_RENAMED = os.getenv("NOTIFY_RENAMED", "true").lower() in ("true", "1", "yes")
CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", "180")) # Default 3 hours

SESSION_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sessions")
os.makedirs(SESSION_DIR, exist_ok=True)
SESSION_FILE = os.path.join(SESSION_DIR, f"session-{IG_USERNAME}")

def get_loader() -> instaloader.Instaloader:
    """Initializes instaloader and loads saved session."""
    L = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_comments=False,
        save_metadata=False,
        compress_json=False
    )

    if not IG_USERNAME:
        print("[Error] IG_USERNAME belum diatur di file .env!")
        sys.exit(1)

    # Cek apakah session file sudah ada
    if os.path.exists(SESSION_FILE):
        try:
            print(f"[Info] Memuat session Instagram dari {SESSION_FILE}...")
            L.load_session_from_file(IG_USERNAME, filename=SESSION_FILE)
            print("[Info] Berhasil login menggunakan session file.")
            return L
        except Exception as e:
            print(f"[Warning] Gagal memuat session file ({e}). Perlu login ulang.")

    # Jika session file belum ada, minta login interaktif
    print(f"\n--- LOGIN INSTAGRAM DIPERLUKAN UNTUK @{IG_USERNAME} ---")
    print("Sesi login akan disimpan secara lokal sehingga tidak perlu login berulang kali.")
    try:
        L.interactive_login(IG_USERNAME)
        L.save_session_to_file(filename=SESSION_FILE)
        print(f"[Info] Session berhasil disimpan ke {SESSION_FILE}")
        return L
    except Exception as e:
        print(f"[Error] Gagal login Instagram: {e}")
        sys.exit(1)

def fetch_current_followers(L: instaloader.Instaloader, target: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Mengambil data followers untuk @{target}...")
    try:
        profile = instaloader.Profile.from_username(L.context, target)
        followers_dict = {}

        # Loop followers
        count = 0
        for follower in profile.get_followers():
            count += 1
            followers_dict[follower.userid] = {
                "username": follower.username,
                "full_name": follower.full_name or ""
            }
            if count % 100 == 0:
                print(f"   Sudah memuat {count} followers...")

        print(f"[Info] Total {len(followers_dict)} followers berhasil diambil.")
        return followers_dict
    except Exception as e:
        print(f"[Error] Gagal mengambil followers: {e}")
        return None

def run_monitoring_cycle(L: instaloader.Instaloader, notifier: TelegramNotifier, target: str):
    current_followers = fetch_current_followers(L, target)
    if current_followers is None:
        return

    unfollowers, new_followers, renamed, is_first_run = process_follower_update(
        current_followers, 
        db_path="followers.db"
    )

    if is_first_run:
        msg = (
            f"✅ <b>Database Berhasil Diinisialisasi!</b>\n"
            f"Berhasil menyimpan <b>{len(current_followers)}</b> followers awal.\n"
            f"Monitoring unfollow untuk @{target} sekarang aktif!"
        )
        print(f"[Info] Snapshot awal tersimpan ({len(current_followers)} followers).")
        notifier.send_message(msg)
        return

    # Kirim notifikasi jika ada unfollow
    if unfollowers:
        print(f"[Alert] Terdeteksi {len(unfollowers)} unfollow!")
        notifier.notify_unfollowers(unfollowers)
    else:
        print("[Info] Tidak ada unfollow terdeteksi.")

    # Kirim notifikasi jika ada perubahan nama/username
    if renamed and NOTIFY_RENAMED:
        print(f"[Info] Terdeteksi {len(renamed)} akun berganti profil.")
        notifier.notify_renamed(renamed)

    # Kirim notifikasi jika ada follower baru (jika diaktifkan)
    if new_followers and NOTIFY_NEW_FOLLOWERS:
        print(f"[Info] Terdeteksi {len(new_followers)} follower baru.")
        notifier.notify_new_followers(new_followers)

def main():
    parser = argparse.ArgumentParser(description="Instagram Unfollow Monitor Bot with Telegram Alerts")
    parser.add_argument("--test-tele", action="store_true", help="Kirim pesan uji coba ke Telegram")
    parser.add_argument("--once", action="store_true", help="Jalankan pengecekan sekali saja")
    parser.add_argument("--loop", action="store_true", help="Jalankan otomatis secara berkala (daemon)")
    args = parser.parse_args()

    # Inisialisasi DB
    init_db("followers.db")

    notifier = TelegramNotifier(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)

    # Test Telegram connection
    if args.test_tele:
        print("[Test] Mengirim pesan tes ke Telegram...")
        success = notifier.send_message("👋 <b>Halo!</b> Bot Instagram Unfollow Monitor siap digunakan.")
        if success:
            print("✅ Berhasil mengirim pesan ke Telegram! Cek bot Telegram kamu.")
        else:
            print("❌ Gagal mengirim pesan. Periksa TELEGRAM_BOT_TOKEN dan TELEGRAM_CHAT_ID di .env.")
        return

    target = TARGET_ACCOUNT or IG_USERNAME
    if not target:
        print("[Error] Harap tentukan IG_USERNAME di file .env!")
        return

    L = get_loader()

    if args.loop:
        print(f"[*] Menjalankan bot dalam mode loop (interval setiap {CHECK_INTERVAL_MINUTES} menit)...")
        print("    Tekan Ctrl+C untuk menghentikan bot.")
        while True:
            try:
                run_monitoring_cycle(L, notifier, target)
            except Exception as e:
                print(f"[Exception] Terjadi kesalahan dalam cycle: {e}")
            
            print(f"[*] Menunggu {CHECK_INTERVAL_MINUTES} menit untuk pengecekan berikutnya...")
            time.sleep(CHECK_INTERVAL_MINUTES * 60)
    else:
        # Default: jalankan sekali
        run_monitoring_cycle(L, notifier, target)

if __name__ == "__main__":
    main()
