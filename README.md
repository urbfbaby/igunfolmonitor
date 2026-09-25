# 📸 Instagram Unfollow Monitor Bot (with Telegram Alerts)

Bot otomatis untuk memantau siapa yang *unfollow* akun Instagram kamu, lengkap dengan **Nama Lengkap / Display Name**, **Username**, dan **User ID**. Bot ini akan mengirimkan notifikasi instan langsung ke Telegram setiap kali ada perubahan.

---

## 🌟 Fitur Utama
- 🚨 **Notifikasi Unfollow ke Telegram:** Menampilkan Nama, @Username, User ID, dan Link Profil.
- 🆔 **User ID Tracker (Anti-Salah Deteksi):** Jika seseorang hanya mengganti username atau display name, bot mendeteksinya sebagai perubahan nama, **bukan unfollow**.
- 🗄️ **Database Lokal (SQLite):** Data followers tersimpan aman di komputer kamu sendiri (`followers.db`).
- 🔐 **Session File:** Login cukup sekali di awal, session tersimpan secara lokal tanpa perlu memasukkan password berulang-ulang.
- ⏱️ **Mode Sekali Jalan vs Mode Otomatis (Loop):** Bisa dijalankan manual, dijadwalkan lewat Windows Task Scheduler, atau dibiarkan jalan di background.

---

## 🚀 Panduan Setup Singkat

### Langkah 1: Buat Bot Telegram & Ambil ID
1. Buka aplikasi Telegram, cari akun **`@BotFather`**.
2. Ketik `/newbot`, lalu ikuti petunjuk untuk menentukan nama dan username bot.
3. Kamu akan mendapatkan **API Token** (contoh: `7123456789:AAFx...`). Simpan token ini.
4. Buka bot baru kamu di Telegram, lalu klik tombol **Start** / kirim pesan apa saja ke bot tersebut.
5. Cari bot **`@userinfobot`** di Telegram, klik Start. Bot ini akan menampilkan `Id` kamu (contoh: `123456789`). Simpan angka ini sebagai **Chat ID**.

---

### Langkah 2: Install Dependensi Python
Buka Terminal / Command Prompt di folder ini:
```bash
pip install -r requirements.txt
```

---

### Langkah 3: Konfigurasi File `.env`
Salin file `.env.example` menjadi `.env`, lalu isi:
```env
IG_USERNAME=username_ig_kamu
TELEGRAM_BOT_TOKEN=token_dari_botfather
TELEGRAM_CHAT_ID=id_dari_userinfobot

# Opsional
NOTIFY_NEW_FOLLOWERS=false
NOTIFY_RENAMED=true
CHECK_INTERVAL_MINUTES=180
```

---

### Langkah 4: Uji Koneksi Telegram
Jalankan perintah ini untuk memastikan notifikasi Telegram bekerja:
```bash
python bot.py --test-tele
```
Jika berhasil, akan ada pesan masuk ke bot Telegram kamu.

---

### Langkah 5: Jalankan Bot
1. **Pengecekan Pertama / Manual (Disarankan):**
   ```bash
   python bot.py --once
   ```
   *Pada penjalanan pertama, kamu akan diminta password IG untuk membuat file session lokal.*
   *Data followers awal akan disimpan ke database sebagai snapshot dasar.*

2. **Mode Otomatis (Background Loop):**
   ```bash
   python bot.py --loop
   ```
   Bot akan otomatis mengecek setiap interval yang ditentukan (default: tiap 3 jam).

---

## 🛡️ Tips Keamanan Instagram
- **Jangan set interval terlalu cepat** (disarankan minimal 2 - 4 jam sekali / 120-240 menit) agar tidak memicu deteksi aktivitas tidak wajar dari sistem keamanan Instagram.
- Disarankan akun IG sudah terpasang autentikasi 2 faktor (2FA) resmi di aplikasi HP kamu.
