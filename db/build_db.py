"""
1회차 ~ 최신회차 로또 당첨 히스토리를 JSON 청크에서 읽어 SQLite DB로 빌드한다.
최초 1회만 실행하면 되고, 이후 갱신은 api/client.py의 sync_latest()가 담당한다.
"""
import json
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(BASE_DIR, "db", "lotto.db")

SCHEMA = """
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
CREATE INDEX IF NOT EXISTS idx_draws_date ON draws(draw_date);
"""


def raw_to_row(item: dict) -> tuple:
    ymd = item["ltRflYmd"]
    draw_date = f"{ymd[0:4]}-{ymd[4:6]}-{ymd[6:8]}"
    return (
        item["ltEpsd"], draw_date,
        item["tm1WnNo"], item["tm2WnNo"], item["tm3WnNo"],
        item["tm4WnNo"], item["tm5WnNo"], item["tm6WnNo"],
        item["bnsWnNo"],
        item.get("rnk1WnNope"), item.get("rnk1WnAmt"), item.get("rnk1SumWnAmt"),
        item.get("rnk2WnNope"), item.get("rnk2WnAmt"), item.get("rnk2SumWnAmt"),
        item.get("wholEpsdSumNtslAmt"),
    )


def build():
    merged = {}
    for fname in sorted(os.listdir(DATA_DIR)):
        if fname.startswith("chunk") and fname.endswith(".json"):
            with open(os.path.join(DATA_DIR, fname), encoding="utf-8") as f:
                for item in json.load(f):
                    merged[item["ltEpsd"]] = item

    rounds = sorted(merged.keys())
    print(f"불러온 회차 수: {len(rounds)} ({rounds[0]}회 ~ {rounds[-1]}회)")

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    rows = [raw_to_row(merged[r]) for r in rounds]
    conn.executemany(
        """INSERT OR REPLACE INTO draws
        (round, draw_date, n1,n2,n3,n4,n5,n6, bonus,
         first_winners, first_prize_each, first_prize_total,
         second_winners, second_prize_each, second_prize_total,
         total_sales)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        rows,
    )
    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM draws").fetchone()[0]
    print(f"DB 저장 완료: {DB_PATH} (총 {count}건)")
    conn.close()


if __name__ == "__main__":
    build()
