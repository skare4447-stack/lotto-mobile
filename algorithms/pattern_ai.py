"""패턴 계산 AI: 전체 회차 데이터를 훑어 핫/콜드 번호, 구간 분포, 최근 트렌드 등을 요약한다."""
from db.database import LottoDB


class PatternAI:
    id = "pattern"
    name = "패턴 계산 AI"
    description = "1회차부터 최신 회차까지 전체 데이터의 패턴(핫/콜드 번호, 구간 분포, 트렌드)을 분석합니다."

    def summary(self, db: LottoDB) -> dict:
        freq = db.number_frequency()
        latest_round = db.get_latest_round()
        last_seen = db.last_seen_round()

        hot = sorted(freq.items(), key=lambda x: -x[1])[:10]
        cold = sorted(freq.items(), key=lambda x: x[1])[:10]
        overdue = sorted(
            ((n, latest_round - r) for n, r in last_seen.items()),
            key=lambda x: -x[1],
        )[:10]

        recent = db.get_recent_draws(20)
        recent_freq = {}
        for row in recent:
            for col in ("n1", "n2", "n3", "n4", "n5", "n6"):
                recent_freq[row[col]] = recent_freq.get(row[col], 0) + 1
        trending = sorted(recent_freq.items(), key=lambda x: -x[1])[:10]

        return {
            "latest_round": latest_round,
            "hot_numbers": hot,
            "cold_numbers": cold,
            "overdue_numbers": overdue,
            "trending_recent20": trending,
        }
