import requests
from typing import List, Optional

class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token.strip()
        self.chat_id = chat_id.strip()
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

    def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        if not self.bot_token or not self.chat_id:
            print("[Telegram] Bot Token atau Chat ID belum disetel.")
            return False

        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True
        }
        try:
            resp = requests.post(self.api_url, json=payload, timeout=10)
            if resp.status_code == 200:
                return True
            else:
                print(f"[Telegram Error] {resp.status_code}: {resp.text}")
                return False
        except Exception as e:
            print(f"[Telegram Exception] {e}")
            return False

    def notify_unfollowers(self, unfollowers: List[dict]):
        if not unfollowers:
            return

        for user in unfollowers:
            name = user.get("full_name") or "(Tanpa Nama)"
            username = user.get("username", "unknown")
            msg = (
                "🚨 <b>UNFOLLOW DETECTED!</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 <b>Nama:</b> {name}\n"
                f"🏷 <b>Username:</b> @{username}\n"
                f"🔗 <b>Profil:</b> https://instagram.com/{username}\n"
                f"🆔 <b>User ID:</b> <code>{user.get('user_id')}</code>\n"
                "━━━━━━━━━━━━━━━━━━━━"
            )
            self.send_message(msg)

    def notify_new_followers(self, new_followers: List[dict]):
        if not new_followers:
            return

        for user in new_followers:
            name = user.get("full_name") or "(Tanpa Nama)"
            username = user.get("username", "unknown")
            msg = (
                "🎉 <b>FOLLOWER BARU!</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 <b>Nama:</b> {name}\n"
                f"🏷 <b>Username:</b> @{username}\n"
                f"🔗 <b>Profil:</b> https://instagram.com/{username}\n"
                "━━━━━━━━━━━━━━━━━━━━"
            )
            self.send_message(msg)

    def notify_renamed(self, renamed_list: List[dict]):
        if not renamed_list:
            return

        for user in renamed_list:
            msg = (
                "✏️ <b>PERUBAHAN PROFIL FOLLOWER</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"🆔 <b>User ID:</b> <code>{user.get('user_id')}</code>\n"
                f"🔄 <b>Username:</b> @{user['old_username']} ➔ <b>@{user['new_username']}</b>\n"
                f"👤 <b>Nama:</b> {user['old_full_name']} ➔ <b>{user['new_full_name']}</b>\n"
                f"🔗 <b>Profil:</b> https://instagram.com/{user['new_username']}\n"
                "━━━━━━━━━━━━━━━━━━━━"
            )
            self.send_message(msg)

    def notify_summary(self, total_followers: int, unfollow_count: int, new_count: int):
        msg = (
            "📊 <b>LAPORAN MONITORING IG</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"👥 <b>Total Followers:</b> {total_followers}\n"
            f"📉 <b>Unfollow:</b> {unfollow_count}\n"
            f"📈 <b>Follower Baru:</b> {new_count}\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        self.send_message(msg)
