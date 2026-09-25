import sqlite3
from datetime import datetime
from typing import Dict, List, Tuple

def get_connection(db_path: str = "followers.db") -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path: str = "followers.db"):
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS followers (
                user_id INTEGER PRIMARY KEY,
                username TEXT NOT NULL,
                full_name TEXT,
                is_active INTEGER DEFAULT 1,
                first_seen TEXT,
                last_seen TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS history_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                username TEXT,
                full_name TEXT,
                details TEXT,
                timestamp TEXT NOT NULL
            )
        """)
        conn.commit()

def get_current_stored_followers(db_path: str = "followers.db") -> Dict[int, dict]:
    """Returns a dict of currently active followers: {user_id: {'username': ..., 'full_name': ...}}"""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, username, full_name FROM followers WHERE is_active = 1")
        rows = cursor.fetchall()
        return {
            row["user_id"]: {
                "username": row["username"],
                "full_name": row["full_name"] or ""
            }
            for row in rows
        }

def process_follower_update(
    current_followers: Dict[int, dict],
    db_path: str = "followers.db"
) -> Tuple[List[dict], List[dict], List[dict], bool]:
    """
    Compares current followers against database.
    Returns:
        unfollowers: List[dict]
        new_followers: List[dict]
        renamed: List[dict]
        is_first_run: bool (True if DB was previously empty)
    """
    stored = get_current_stored_followers(db_path)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # If first run, store all and don't trigger unfollow / new follow spam
    if not stored:
        with get_connection(db_path) as conn:
            cursor = conn.cursor()
            for uid, info in current_followers.items():
                cursor.execute("""
                    INSERT OR REPLACE INTO followers (user_id, username, full_name, is_active, first_seen, last_seen)
                    VALUES (?, ?, ?, 1, ?, ?)
                """, (uid, info["username"], info.get("full_name", ""), now_str, now_str))
            conn.commit()
        return [], [], [], True

    stored_ids = set(stored.keys())
    current_ids = set(current_followers.keys())

    unfollow_ids = stored_ids - current_ids
    new_follow_ids = current_ids - stored_ids
    common_ids = stored_ids & current_ids

    unfollowers = []
    new_followers = []
    renamed = []

    with get_connection(db_path) as conn:
        cursor = conn.cursor()

        # Handle unfollowers
        for uid in unfollow_ids:
            old_info = stored[uid]
            unfollowers.append({
                "user_id": uid,
                "username": old_info["username"],
                "full_name": old_info["full_name"]
            })
            cursor.execute("""
                UPDATE followers 
                SET is_active = 0, last_seen = ? 
                WHERE user_id = ?
            """, (now_str, uid))
            cursor.execute("""
                INSERT INTO history_logs (event_type, user_id, username, full_name, details, timestamp)
                VALUES ('UNFOLLOW', ?, ?, ?, 'Berhenti mengikuti', ?)
            """, (uid, old_info["username"], old_info["full_name"], now_str))

        # Handle new followers
        for uid in new_follow_ids:
            new_info = current_followers[uid]
            new_followers.append({
                "user_id": uid,
                "username": new_info["username"],
                "full_name": new_info.get("full_name", "")
            })
            cursor.execute("""
                INSERT INTO followers (user_id, username, full_name, is_active, first_seen, last_seen)
                VALUES (?, ?, ?, 1, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    full_name = excluded.full_name,
                    is_active = 1,
                    last_seen = excluded.last_seen
            """, (uid, new_info["username"], new_info.get("full_name", ""), now_str, now_str))
            cursor.execute("""
                INSERT INTO history_logs (event_type, user_id, username, full_name, details, timestamp)
                VALUES ('NEW_FOLLOWER', ?, ?, ?, 'Mulai mengikuti', ?)
            """, (uid, new_info["username"], new_info.get("full_name", ""), now_str))

        # Check for username / name changes
        for uid in common_ids:
            old_info = stored[uid]
            curr_info = current_followers[uid]
            old_u = old_info["username"]
            new_u = curr_info["username"]
            old_n = old_info["full_name"]
            new_n = curr_info.get("full_name", "")

            if old_u != new_u or old_n != new_n:
                renamed.append({
                    "user_id": uid,
                    "old_username": old_u,
                    "new_username": new_u,
                    "old_full_name": old_n,
                    "new_full_name": new_n
                })
                cursor.execute("""
                    UPDATE followers 
                    SET username = ?, full_name = ?, last_seen = ? 
                    WHERE user_id = ?
                """, (new_u, new_n, now_str, uid))
                cursor.execute("""
                    INSERT INTO history_logs (event_type, user_id, username, full_name, details, timestamp)
                    VALUES ('RENAME', ?, ?, ?, ?, ?)
                """, (uid, new_u, new_n, f"Ubah profil: @{old_u} ({old_n}) -> @{new_u} ({new_n})", now_str))
            else:
                cursor.execute("""
                    UPDATE followers SET last_seen = ? WHERE user_id = ?
                """, (now_str, uid))

        conn.commit()

    return unfollowers, new_followers, renamed, False
