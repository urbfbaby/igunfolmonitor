import os
import sys
import time
import pickle
import argparse
from datetime import datetime
from dotenv import load_dotenv

# Ensure UTF-8 output on Windows console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

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

    if os.path.exists(SESSION_FILE):
        try:
            print(f"[Info] Memuat session Instagram dari {SESSION_FILE}...")
            L.load_session_from_file(IG_USERNAME, filename=SESSION_FILE)
            print("[Info] Berhasil memuat session.")
            return L
        except Exception as e:
            print(f"[Warning] Gagal memuat session file ({e}).")

    print("\n[Error] File session tidak ditemukan atau belum valid!")
    print("Harap jalankan terlebih dahulu: python login_cookie.py")
    sys.exit(1)

def get_account_user_id(L: instaloader.Instaloader) -> str:
    """Retrieves account user_id from session cookies or session file."""
    # Cek dari cookies session
    uid = L.context._session.cookies.get("ds_user_id")
    if uid:
        return str(uid)
    
    # Cek dari file session pickle
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "rb") as f:
                data = pickle.load(f)
                if isinstance(data, dict) and data.get("ds_user_id"):
                    return str(data["ds_user_id"])
        except Exception:
            pass

    return ""

def fetch_current_followers(L: instaloader.Instaloader, target: str):
    """
    Fetches followers using Instagram's official Web API endpoint (api/v1/friendships/{id}/followers).
    This endpoint completely bypasses the HTTP 429 error caused by web_profile_info.
    """
    user_id = get_account_user_id(L)
    if not user_id:
        print("[Error] User ID akun tidak ditemukan di cookie session. Jalankan ulang python login_cookie.py.")
        return None

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Mengambil data followers untuk @{target} (User ID: {user_id})...")
    
    headers = {
        "x-ig-app-id": "936619743392459",
        "Referer": f"https://www.instagram.com/{target}/",
        "X-Requested-With": "XMLHttpRequest"
    }

    followers_dict = {}
    next_max_id = ""
    page = 1

    try:
        while True:
            url = f"https://www.instagram.com/api/v1/friendships/{user_id}/followers/?count=50"
            if next_max_id:
                url += f"&max_id={next_max_id}"

            resp = L.context._session.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                print(f"[Error] Gagal request followers (HTTP {resp.status_code}): {resp.text[:150]}")
                break

            data = resp.json()
            users = data.get("users", [])
            for u in users:
                uid = int(u.get("pk"))
                followers_dict[uid] = {
                    "username": u.get("username", ""),
                    "full_name": u.get("full_name", "")
                }

            print(f"   [Halaman {page}] Terkumpul {len(followers_dict)} followers...")

            next_max_id = data.get("next_max_id")
            if not next_max_id or not data.get("has_more", False):
                break

            page += 1
            # Jeda sopan agar tidak dicurigai server Instagram
            time.sleep(1.2)

        print(f"[Info] Sukses! Total {len(followers_dict)} followers berhasil dimuat.")
        return followers_dict

    except Exception as e:
        print(f"[Error] Terjadi kesalahan saat mengambil followers: {e}")
        return None

def run_monitoring_cycle(L: instaloader.Instaloader, notifier: TelegramNotifier, target: str):
    current_followers = fetch_current_followers(L, target)
    if current_followers is None or len(current_followers) == 0:
        print("[Warning] Data followers kosong atau gagal diambil.")
        return

    unfollowers, new_followers, renamed, is_first_run = process_follower_update(
        current_followers, 
        db_path="followers.db"
    )

    if is_first_run:
        msg = (
            f"✅ <b>Database Berhasil Diinisialisasi!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Akun:</b> @{target}\n"
            f"👥 <b>Total Followers:</b> {len(current_followers)}\n"
            f"🛡️ <b>Status:</b> Monitoring Unfollow Aktif!\n"
            f"━━━━━━━━━━━━━━━━━━━━"
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
