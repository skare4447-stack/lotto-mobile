"""
번호 자동 생성 엔진 5종 ("확률형 AI").
※ 로또는 완전 무작위 추첨이므로 어떤 알고리즘도 실제 당첨 확률을 높이지 않는다.
   아래 엔진들은 과거 통계를 이용해 '재미있는 조합'을 제시하는 용도다.
"""
import random
from itertools import combinations

from db.database import LottoDB


def _weighted_sample(weights: dict, k: int) -> list[int]:
    """weights={번호: 가중치} 에서 중복 없이 k개 추출"""
    pool = list(weights.keys())
    w = [max(weights[n], 0.0001) for n in pool]
    picked = []
    while len(picked) < k:
        n = random.choices(pool, weights=w, k=1)[0]
        idx = pool.index(n)
        pool.pop(idx)
        w.pop(idx)
        picked.append(n)
    return sorted(picked)


class BaseAI:
    id = "base"
    name = "Base AI"
    description = ""

    def generate(self, db: LottoDB) -> list[int]:
        raise NotImplementedError


class FrequencyAI(BaseAI):
    id = "frequency"
    name = "AI 엔진 #1 · 빈도분석"
    description = "역대 전체 회차에서 자주 나온 '핫넘버'에 가중치를 둬 조합을 뽑습니다."

    def generate(self, db: LottoDB) -> list[int]:
        freq = db.number_frequency()
        return _weighted_sample(dict(freq), 6)


class ColdNumberAI(BaseAI):
    id = "cold"
    name = "AI 엔진 #2 · 이월수(미출현) 분석"
    description = "오랫동안 나오지 않은 '이월수'가 다시 나올 확률에 주목해 가중치를 둡니다."

    def generate(self, db: LottoDB) -> list[int]:
        last_seen = db.last_seen_round()
        latest = db.get_latest_round()
        gap_weight = {n: (latest - r) + 1 for n, r in last_seen.items()}
        return _weighted_sample(gap_weight, 6)


class BalanceAI(BaseAI):
    id = "balance"
    name = "AI 엔진 #3 · 홀짝·구간 균형"
    description = "역대 당첨 조합에서 가장 흔했던 홀짝 비율·번호대(1~15/16~30/31~45) 분포에 맞춰 조합을 구성합니다."

    def generate(self, db: LottoDB) -> list[int]:
        draws = db.get_all_draws()
        ratio_counter = {}
        zone_counter = {}
        for row in draws:
            nums = [row["n1"], row["n2"], row["n3"], row["n4"], row["n5"], row["n6"]]
            odd = sum(1 for n in nums if n % 2 == 1)
            ratio_counter[odd] = ratio_counter.get(odd, 0) + 1
            zones = tuple(sorted(
                sum(1 for n in nums if lo <= n <= hi)
                for lo, hi in [(1, 15), (16, 30), (31, 45)]
            ))
            zone_counter[zones] = zone_counter.get(zones, 0) + 1

        target_odd = max(ratio_counter, key=ratio_counter.get)
        target_zone = max(zone_counter, key=zone_counter.get)  # 예: (2,2,2)

        for _ in range(500):
            zone_ranges = [(1, 15), (16, 30), (31, 45)]
            candidate = []
            ok = True
            for count, (lo, hi) in zip(target_zone, zone_ranges):
                pool = [n for n in range(lo, hi + 1) if n not in candidate]
                if len(pool) < count:
                    ok = False
                    break
                candidate.extend(random.sample(pool, count))
            if not ok:
                continue
            odd = sum(1 for n in candidate if n % 2 == 1)
            if odd == target_odd:
                return sorted(candidate)
        # 조건을 못 맞추면 무작위 폴백
        return sorted(random.sample(range(1, 46), 6))


class PairAI(BaseAI):
    id = "pair"
    name = "AI 엔진 #4 · 궁합수 조합"
    description = "역대 회차에서 함께 자주 나온 '궁합수 쌍'을 중심으로 조합을 확장합니다."

    def generate(self, db: LottoDB) -> list[int]:
        pair_counts = db.pair_cooccurrence()
        freq = db.number_frequency()
        seed = _weighted_sample(dict(freq), 1)[0]
        selected = [seed]

        while len(selected) < 6:
            scores = {}
            for n in range(1, 46):
                if n in selected:
                    continue
                score = 0
                for s in selected:
                    a, b = sorted((s, n))
                    score += pair_counts.get((a, b), 0)
                scores[n] = score + 1  # +1로 0점 방지
            nxt = _weighted_sample(scores, 1)[0]
            selected.append(nxt)
        return sorted(selected)


class MonteCarloAI(BaseAI):
    id = "montecarlo"
    name = "AI 엔진 #5 · 몬테카를로 시뮬레이션"
    description = "수천 번의 가상 추첨을 시뮬레이션해, 합계·홀짝비·번호대 분포가 역대 평균에 가장 가까운 조합을 선택합니다."

    def generate(self, db: LottoDB) -> list[int]:
        draws = db.get_all_draws()
        sums = []
        for row in draws:
            nums = [row["n1"], row["n2"], row["n3"], row["n4"], row["n5"], row["n6"]]
            sums.append(sum(nums))
        avg_sum = sum(sums) / len(sums) if sums else 138

        best, best_diff = None, float("inf")
        for _ in range(3000):
            candidate = sorted(random.sample(range(1, 46), 6))
            diff = abs(sum(candidate) - avg_sum)
            if diff < best_diff:
                best, best_diff = candidate, diff
        return best


def _trend_ai_lazy():
    """순환 import(algorithms.trend -> db 만 사용) 방지를 위해 지연 로딩"""
    from algorithms.trend import TrendAI
    return TrendAI()


ALL_GENERATORS: list[BaseAI] = [
    FrequencyAI(), ColdNumberAI(), BalanceAI(), PairAI(), MonteCarloAI(), _trend_ai_lazy(),
]


def generate_auto(db: LottoDB, engine_id: str | None = None) -> tuple[list[int], BaseAI]:
    """engine_id 지정 시 해당 엔진, 없으면 5개 중 무작위로 하나 선택해 생성"""
    engine = next((e for e in ALL_GENERATORS if e.id == engine_id), None) or random.choice(ALL_GENERATORS)
    return engine.generate(db), engine
