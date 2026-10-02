"""
트렌드 가중치 계산 시스템
최근 회차일수록 더 큰 가중치를 주는 지수감쇠(exponential decay) 방식으로
'요즘 자주 나오는 번호(상승세)'를 수치화한다.

trend_score(번호) = Σ decay^i   (i = 0: 가장 최근 회차, 1: 그 전 회차, ...)
번호가 최근 window회차 안에서 나온 각 회차마다 decay^i 만큼 점수를 더한다.
decay가 1에 가까울수록 과거도 비슷하게 반영, 0에 가까울수록 최근 회차에 극단적으로 집중.
"""
from db.database import LottoDB


def trend_scores(db: LottoDB, window: int = 20, decay: float = 0.9) -> dict[int, float]:
    draws = db.get_recent_draws(window)  # 오래된 -> 최신 순
    draws = list(reversed(draws))        # 최신 -> 오래된 순으로 변경
    scores = {n: 0.0 for n in range(1, 46)}
    for i, row in enumerate(draws):
        w = decay ** i
        for col in ("n1", "n2", "n3", "n4", "n5", "n6"):
            scores[row[col]] += w
    return scores


def trend_ranking(db: LottoDB, window: int = 20, decay: float = 0.9, top: int = 10):
    scores = trend_scores(db, window, decay)
    ranked = sorted(scores.items(), key=lambda x: -x[1])
    return [(n, round(s, 3)) for n, s in ranked[:top]]


class TrendAI:
    id = "trend"
    name = "AI 엔진 #6 · 트렌드 가중치"
    description = "최근 회차일수록 더 큰 가중치를 주는 지수감쇠 방식으로 '요즘 상승세인 번호'에 집중해 조합을 뽑습니다."

    def __init__(self, window: int = 20, decay: float = 0.9):
        self.window = window
        self.decay = decay

    def generate(self, db: LottoDB) -> list[int]:
        import random
        scores = trend_scores(db, self.window, self.decay)
        pool = list(scores.keys())
        weights = [max(scores[n], 0.01) for n in pool]
        picked = []
        while len(picked) < 6:
            n = random.choices(pool, weights=weights, k=1)[0]
            idx = pool.index(n)
            pool.pop(idx)
            weights.pop(idx)
            picked.append(n)
        return sorted(picked)
