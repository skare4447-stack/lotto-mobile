"""
생성된 조합을 다시 검증/재계산하는 엔진 5종 ("재계산 AI").
각 엔진은 0~100점 사이의 점수와 코멘트를 반환한다.
※ 이 점수는 통계적 '흔함/특이함' 정도를 보여줄 뿐, 당첨 확률과는 무관하다.
"""
from itertools import combinations

from db.database import LottoDB


class BaseValidator:
    id = "base"
    name = "Base Validator"

    def score(self, numbers: list[int], db: LottoDB) -> tuple[int, str]:
        raise NotImplementedError


class SumRangeValidator(BaseValidator):
    id = "sum_range"
    name = "재계산 AI #1 · 총합 범위 분석"

    def score(self, numbers, db):
        draws = db.get_all_draws()
        sums = [sum([r["n1"], r["n2"], r["n3"], r["n4"], r["n5"], r["n6"]]) for r in draws]
        avg = sum(sums) / len(sums)
        std = (sum((s - avg) ** 2 for s in sums) / len(sums)) ** 0.5
        total = sum(numbers)
        z = abs(total - avg) / std if std else 0
        score = max(0, round(100 - z * 25))
        comment = f"조합 총합 {total} (역대 평균 {avg:.1f} ±{std:.1f})"
        return score, comment


class OddEvenValidator(BaseValidator):
    id = "odd_even"
    name = "재계산 AI #2 · 홀짝비 분석"

    def score(self, numbers, db):
        draws = db.get_all_draws()
        counter = {}
        for r in draws:
            nums = [r["n1"], r["n2"], r["n3"], r["n4"], r["n5"], r["n6"]]
            odd = sum(1 for n in nums if n % 2 == 1)
            counter[odd] = counter.get(odd, 0) + 1
        total_draws = sum(counter.values())
        odd = sum(1 for n in numbers if n % 2 == 1)
        freq_ratio = counter.get(odd, 0) / total_draws
        score = round(freq_ratio * 100 / max(counter.values()) * total_draws)
        score = min(100, round(freq_ratio * 300))  # 흔한 비율일수록 고득점
        comment = f"홀{odd}:짝{6-odd} 비율 (역대 이 비율 등장 {counter.get(odd,0)}회 / {total_draws}회)"
        return score, comment


class ConsecutiveValidator(BaseValidator):
    id = "consecutive"
    name = "재계산 AI #3 · 연속번호 분석"

    def score(self, numbers, db):
        nums = sorted(numbers)
        consec = sum(1 for a, b in zip(nums, nums[1:]) if b - a == 1)

        draws = db.get_all_draws()
        counter = {}
        for r in draws:
            ns = sorted([r["n1"], r["n2"], r["n3"], r["n4"], r["n5"], r["n6"]])
            c = sum(1 for a, b in zip(ns, ns[1:]) if b - a == 1)
            counter[c] = counter.get(c, 0) + 1
        total = sum(counter.values())
        ratio = counter.get(consec, 0) / total if total else 0
        score = min(100, round(ratio * 300))
        comment = f"연속번호 쌍 {consec}개 (역대 이 패턴 비중 {ratio*100:.1f}%)"
        return score, comment


class ACValueValidator(BaseValidator):
    id = "ac_value"
    name = "재계산 AI #4 · AC값(복잡도) 분석"

    @staticmethod
    def _ac_value(numbers: list[int]) -> int:
        diffs = {abs(a - b) for a, b in combinations(numbers, 2)}
        return len(diffs) - (len(numbers) - 1)

    def score(self, numbers, db):
        ac = self._ac_value(numbers)
        # AC값은 보통 0~10 사이, 역대 당첨 조합은 대부분 7 이상(무작위성 높음)
        score = min(100, round(ac / 10 * 100))
        comment = f"AC값 {ac} (7 이상이면 번호 간 간격이 다양함 = 무작위 추첨과 유사)"
        return score, comment


class HistoryDuplicateValidator(BaseValidator):
    id = "history_duplicate"
    name = "재계산 AI #5 · 역대 중복 검사"

    def score(self, numbers, db):
        target = set(numbers)
        best_match = 0
        exact = False
        for r in db.get_all_draws():
            nums = {r["n1"], r["n2"], r["n3"], r["n4"], r["n5"], r["n6"]}
            match = len(target & nums)
            if match > best_match:
                best_match = match
            if match == 6:
                exact = True
        if exact:
            score = 0
            comment = "⚠ 역대 당첨번호와 완전히 동일한 조합입니다!"
        else:
            score = 100 - best_match * 10
            comment = f"역대 조합과 최대 {best_match}개 번호 일치 (완전 중복 없음)"
        return max(0, score), comment


ALL_VALIDATORS: list[BaseValidator] = [
    SumRangeValidator(), OddEvenValidator(), ConsecutiveValidator(),
    ACValueValidator(), HistoryDuplicateValidator(),
]


def recompute_all(numbers: list[int], db: LottoDB) -> dict:
    """5개 검증 AI 결과 + 종합 신뢰도 점수"""
    results = []
    for v in ALL_VALIDATORS:
        score, comment = v.score(numbers, db)
        results.append({"id": v.id, "name": v.name, "score": score, "comment": comment})
    overall = round(sum(r["score"] for r in results) / len(results))
    return {"results": results, "overall_score": overall}
