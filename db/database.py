"""로또 히스토리 DB 접근 레이어"""
import os
import shutil
import sqlite3
import sys
from collections import Counter
from typing import Optional


def _find_bundled_db() -> str:
    """python-for-android(APK) 빌드 시 앱 리소스로 함께 패키징된 원본 DB 위치."""
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, "lotto.db")


def _resolve_db_path() -> str:
    """
    개발 환경(PC): 프로젝트 내 db/lotto.db 그대로 사용.
    안드로이드(APK): 앱 설치 패키지 안의 DB는 읽기 전용이라, 최초 실행 시
    앱 전용 쓰기 가능 저장소(App.user_data_dir, 보통
    /data/data/<package>/files)로 1회 복사한 뒤 그 경로를 사용한다.
    (앱 패키지 내부에 직접 쓰면 업데이트/재설치 때 사라지거나 쓰기 자체가
    막혀있을 수 있음)
    """
    try:
        # 안드로이드 환경에서만 android 모듈이 존재 (python-for-android 런타임)
        from android.storage import app_storage_path  # type: ignore

        user_dir = app_storage_path()
        os.makedirs(user_dir, exist_ok=True)
        user_db = os.path.join(user_dir, "lotto.db")
        if not os.path.exists(user_db):
            bundled_db = _find_bundled_db()
            if os.path.exists(bundled_db):
                shutil.copy(bundled_db, user_db)
        return user_db
    except ImportError:
        pass

    if getattr(sys, "frozen", False):
        # PyInstaller로 데스크톱 exe를 만드는 경우를 대비한 폴백 (모바일 앱에서는 미사용)
        base = os.environ.get("APPDATA") or os.path.expanduser("~/.lotto_coffee")
        user_dir = os.path.join(base, "LottoCoffee")
        os.makedirs(user_dir, exist_ok=True)
        user_db = os.path.join(user_dir, "lotto.db")
        if not os.path.exists(user_db):
            bundled_db = os.path.join(getattr(sys, "_MEIPASS", "."), "db", "lotto.db")
            if os.path.exists(bundled_db):
                shutil.copy(bundled_db, user_db)
        return user_db

    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "lotto.db")


DB_PATH = _resolve_db_path()


class LottoDB:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._ensure_schema()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self):
        conn = self._connect()
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS draws (
                round INTEGER PRIMARY KEY,
                draw_date TEXT NOT NULL,
                n1 INTEGER NOT NULL, n2 INTEGER NOT NULL, n3 INTEGER NOT NULL,
                n4 INTEGER NOT NULL, n5 INTEGER NOT NULL, n6 INTEGER NOT NULL,
                bonus INTEGER NOT NULL,
                first_winners INTEGER, first_prize_each INTEGER, first_prize_total INTEGER,
                second_winners INTEGER, second_prize_each INTEGER, second_prize_total INTEGER,
                total_sales INTEGER
            );
            CREATE TABLE IF NOT EXISTS saved_combinations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                source TEXT,               -- 자동/수동/선택 + 엔진 이름
                n1 INTEGER, n2 INTEGER, n3 INTEGER, n4 INTEGER, n5 INTEGER, n6 INTEGER,
                checked_round INTEGER,
                result TEXT                -- 낙첨/5등/4등/3등/2등/1등
            );
            """
        )
        conn.commit()
        conn.close()

    # ---------- 조회 ----------
    def get_latest_round(self) -> int:
        conn = self._connect()
        row = conn.execute("SELECT MAX(round) AS m FROM draws").fetchone()
        conn.close()
        return row["m"] or 0

    def get_draw(self, round_no: int) -> Optional[sqlite3.Row]:
        conn = self._connect()
        row = conn.execute("SELECT * FROM draws WHERE round=?", (round_no,)).fetchone()
        conn.close()
        return row

    def get_all_draws(self, order="ASC"):
        conn = self._connect()
        rows = conn.execute(f"SELECT * FROM draws ORDER BY round {order}").fetchall()
        conn.close()
        return rows

    def get_recent_draws(self, n: int = 50):
        conn = self._connect()
        rows = conn.execute(
            "SELECT * FROM draws ORDER BY round DESC LIMIT ?", (n,)
        ).fetchall()
        conn.close()
        return list(reversed(rows))

    # ---------- 통계 ----------
    def number_frequency(self) -> Counter:
        """1~45 각 숫자가 1등 당첨번호(보너스 제외)로 나온 횟수"""
        counter = Counter({i: 0 for i in range(1, 46)})
        for row in self.get_all_draws():
            for col in ("n1", "n2", "n3", "n4", "n5", "n6"):
                counter[row[col]] += 1
        return counter

    def bonus_frequency(self) -> Counter:
        counter = Counter({i: 0 for i in range(1, 46)})
        for row in self.get_all_draws():
            counter[row["bonus"]] += 1
        return counter

    def pair_cooccurrence(self) -> dict:
        """두 숫자가 같은 회차에 함께 나온 횟수 (궁합수 분석용)"""
        from itertools import combinations
        pair_counter = Counter()
        for row in self.get_all_draws():
            nums = sorted([row["n1"], row["n2"], row["n3"], row["n4"], row["n5"], row["n6"]])
            for a, b in combinations(nums, 2):
                pair_counter[(a, b)] += 1
        return pair_counter

    def last_seen_round(self) -> dict:
        """각 숫자가 마지막으로 나온 회차 (미출현 기간 계산용 - 이월수 분석)"""
        last_seen = {i: 0 for i in range(1, 46)}
        for row in self.get_all_draws():
            for col in ("n1", "n2", "n3", "n4", "n5", "n6"):
                last_seen[row[col]] = row["round"]
        return last_seen

    # ---------- 저장 ----------
    def insert_draw(self, row: dict):
        conn = self._connect()
        conn.execute(
            """INSERT OR REPLACE INTO draws
            (round, draw_date, n1,n2,n3,n4,n5,n6, bonus,
             first_winners, first_prize_each, first_prize_total,
             second_winners, second_prize_each, second_prize_total, total_sales)
            VALUES (:round,:draw_date,:n1,:n2,:n3,:n4,:n5,:n6,:bonus,
             :first_winners,:first_prize_each,:first_prize_total,
             :second_winners,:second_prize_each,:second_prize_total,:total_sales)""",
            row,
        )
        conn.commit()
        conn.close()

    def save_combination(self, numbers: list[int], source: str) -> int:
        conn = self._connect()
        cur = conn.execute(
            """INSERT INTO saved_combinations (source, n1,n2,n3,n4,n5,n6)
               VALUES (?,?,?,?,?,?,?)""",
            (source, *sorted(numbers)),
        )
        conn.commit()
        new_id = cur.lastrowid
        conn.close()
        return new_id

    def get_saved_combinations(self):
        conn = self._connect()
        rows = conn.execute(
            "SELECT * FROM saved_combinations ORDER BY id DESC"
        ).fetchall()
        conn.close()
        return rows

    def update_combination_result(self, comb_id: int, checked_round: int, result: str):
        conn = self._connect()
        conn.execute(
            "UPDATE saved_combinations SET checked_round=?, result=? WHERE id=?",
            (checked_round, result, comb_id),
        )
        conn.commit()
        conn.close()

    def delete_combination(self, comb_id: int):
        conn = self._connect()
        conn.execute("DELETE FROM saved_combinations WHERE id=?", (comb_id,))
        conn.commit()
        conn.close()

    def delete_all_combinations(self):
        conn = self._connect()
        conn.execute("DELETE FROM saved_combinations")
        conn.commit()
        conn.close()
