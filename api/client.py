"""
동행복권 로또6/45 공식 사이트 연동 클라이언트.

- fetch_latest(): 최신 회차 결과 1건
- fetch_range(center): center 회차를 중심으로 최대 10개 회차 반환
- sync_to_latest(db): DB에 없는 회차를 전부 채워서 최신까지 동기화

주의: 이 API는 dhlottery.co.kr 웹사이트가 자체적으로 사용하는 내부 API이며
공식 문서로 공개된 것이 아니므로, 사이트 개편 시 주소나 필드명이 바뀔 수 있다.
"""
import time
from datetime import datetime

import requests

BASE = "https://www.dhlottery.co.kr"
LATEST_URL = f"{BASE}/lt645/selectPstLt645Info.do"
RANGE_URL = f"{BASE}/lt645/selectPstLt645InfoNew.do"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Referer": f"{BASE}/lt645/intro",
}


class DhLotteryError(RuntimeError):
    pass


def _get_json(url: str, params: dict | None = None) -> dict:
    resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    try:
        return resp.json()
    except ValueError as e:
        raise DhLotteryError(
            "동행복권 서버가 JSON이 아닌 응답을 반환했습니다. "
            "사이트 구조가 변경되었을 수 있습니다."
        ) from e


def _raw_to_row(item: dict) -> dict:
    ymd = item["ltRflYmd"]
    return {
        "round": item["ltEpsd"],
        "draw_date": f"{ymd[0:4]}-{ymd[4:6]}-{ymd[6:8]}",
        "n1": item["tm1WnNo"], "n2": item["tm2WnNo"], "n3": item["tm3WnNo"],
        "n4": item["tm4WnNo"], "n5": item["tm5WnNo"], "n6": item["tm6WnNo"],
        "bonus": item["bnsWnNo"],
        "first_winners": item.get("rnk1WnNope"),
        "first_prize_each": item.get("rnk1WnAmt"),
        "first_prize_total": item.get("rnk1SumWnAmt"),
        "second_winners": item.get("rnk2WnNope"),
        "second_prize_each": item.get("rnk2WnAmt"),
        "second_prize_total": item.get("rnk2SumWnAmt"),
        "total_sales": item.get("wholEpsdSumNtslAmt"),
    }


def fetch_latest() -> dict:
    """최신 1개 회차 결과. 홈페이지 위젯이 쓰는 것과 동일한 엔드포인트."""
    data = _get_json(LATEST_URL)
    items = data.get("data", {}).get("list", [])
    if not items:
        raise DhLotteryError("최신 회차 데이터를 가져오지 못했습니다.")
    return _raw_to_row(items[0])


def fetch_range(center_round: int) -> list[dict]:
    """center_round를 중심으로 최대 10개 회차."""
    data = _get_json(RANGE_URL, params={"srchDir": "center", "srchLtEpsd": center_round})
    items = data.get("data", {}).get("list", [])
    return [_raw_to_row(i) for i in items]


def sync_to_latest(db, progress_callback=None, delay_sec: float = 0.2) -> int:
    """
    DB에 저장된 마지막 회차 다음부터 최신 회차까지 전부 내려받아 저장한다.
    반환값: 새로 추가된 회차 수
    """
    latest = fetch_latest()
    latest_round = latest["round"]
    have = db.get_latest_round()

    if have >= latest_round:
        return 0

    added = 0
    k = have + 5 if have > 0 else 5
    while True:
        rows = fetch_range(min(k, latest_round))
        for row in rows:
            if row["round"] > have:
                db.insert_draw(row)
                added += 1
        if progress_callback:
            progress_callback(min(k, latest_round), latest_round)
        if k >= latest_round:
            break
        k += 10
        time.sleep(delay_sec)

    # 최신 회차가 range 응답에 없었을 경우 대비해 확실히 저장
    db.insert_draw(latest)
    return added


if __name__ == "__main__":
    print("최신 회차 조회 테스트...")
    latest = fetch_latest()
    print(latest)
