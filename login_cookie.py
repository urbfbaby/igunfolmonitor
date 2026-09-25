import os
import sys
import pickle
import requests
from dotenv import load_dotenv

# Reconfigure encoding for Windows console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

load_dotenv()
IG_USERNAME = os.getenv("IG_USERNAME", "").strip() or "hi.imrizky"

def fetch_fresh_csrf():
    try:
        r = requests.get("https://www.instagram.com", timeout=10)
        return r.cookies.get("csrftoken", "")
    except Exception:
        return ""

def main():
    print("=" * 60)
    print(f"🔐 SETUP LOGIN INSTAGRAM VIA COOKIE (@{IG_USERNAME})")
    print("=" * 60)
    print("Instagram memblokir login otomatis via password untuk mencegah bot.")
    print("Solusi resmi & aman: Memakai cookie 'sessionid' dari browser kamu.\n")
    print("📌 Cara mengambil cookie sessionid:")
    print("1. Buka instagram.com di Chrome / Edge (pastikan sudah login @hi.imrizky)")
    print("2. Tekan tombol F12 (atau Klik Kanan -> Inspect)")
    print("3. Pilih tab 'Application' di menu atas (di Firefox namanya 'Storage')")
    print("4. Di menu samping kiri, klik 'Cookies' -> 'https://www.instagram.com'")
    print("5. Cari baris bernama 'sessionid', lalu double-click nilainya dan Copy.")
    print("=" * 60)

    session_id = input("\n👉 Paste cookie 'sessionid' di sini: ").strip()
    if not session_id:
        print("❌ Error: sessionid tidak boleh kosong!")
        return

    csrf_token = input("👉 Paste cookie 'csrftoken' (tekan Enter langsung jika ingin otomatis): ").strip()
    if not csrf_token:
        print("[*] Mengambil csrftoken otomatis dari server Instagram...")
        csrf_token = fetch_fresh_csrf()
        if not csrf_token:
            csrf_token = "missing"

    ds_user_id = input("👉 Paste cookie 'ds_user_id' (opsional, tekan Enter jika tidak ada): ").strip()

    cookie_dict = {
        "sessionid": session_id,
        "csrftoken": csrf_token
    }
    if ds_user_id:
        cookie_dict["ds_user_id"] = ds_user_id

    # Simpan ke folder sessions/
    session_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sessions")
    os.makedirs(session_dir, exist_ok=True)
    session_file = os.path.join(session_dir, f"session-{IG_USERNAME}")

    with open(session_file, "wb") as f:
        pickle.dump(cookie_dict, f)

    print(f"\n✅ File sesi berhasil disimpan ke:")
    print(f"   {session_file}")
    print("\nSedang menguji sesi ke Instagram...")

    import instaloader
    L = instaloader.Instaloader()
    try:
        L.load_session_from_file(IG_USERNAME, filename=session_file)
        logged_user = L.test_login()
        if logged_user:
            print(f"🎉 LOGIN BERHASIL! Terhubung sebagai: @{logged_user}")
            print("\nSekarang jalankan perintah berikut untuk mulai monitoring:")
            print("👉 python bot.py --once")
        else:
            print("⚠️ Cookie berhasil disimpan, silakan tes jalankan 'python bot.py --once'.")
    except Exception as e:
        print(f"⚠️ Catatan saat verifikasi: {e}")
        print("Sesi tetap tersimpan. Silakan coba jalankan 'python bot.py --once'.")

if __name__ == "__main__":
    main()
