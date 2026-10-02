"""
패턴 마스크 필터
생성된 조합이 특정 통계적 패턴 조건을 만족하는지 검사하고,
불만족 시 거부(재생성)하는 필터 규칙 모음.

각 규칙은 (통과여부, 사유) 를 반환한다.
"""
from itertools import combinations


class PatternMaskFilter:
    def __init__(self, db=None):
        self.db = db
        # 기본 활성화 상태 (UI 체크박스와 매핑)
        self.enabled = {
            "sum_range": True,
            "max_consecutive": True,
            "odd_even_extreme": True,
            "zone_monopoly": True,
            "ac_value_min": True,
            "exclude_prior_winners": True,
        }
        # 파라미터 (UI에서 조정 가능)
        self.sum_min = 100
        self.sum_max = 175
        self.max_consecutive_allowed = 2   # 연속번호 몇 쌍까지 허용
        self.ac_min_value = 3              # 이보다 낮으면(너무 규칙적) 제외
        self._prior_sets = None

    # ---------- 개별 규칙 ----------
    def _rule_sum_range(self, nums):
        s = sum(nums)
        ok = self.sum_min <= s <= self.sum_max
        return ok, f"총합 {s} (허용범위 {self.sum_min}~{self.sum_max})"

    def _rule_max_consecutive(self, nums):
        ns = sorted(nums)
        consec = sum(1 for a, b in zip(ns, ns[1:]) if b - a == 1)
        ok = consec <= self.max_consecutive_allowed
        return ok, f"연속번호 쌍 {consec}개 (허용 최대 {self.max_consecutive_allowed}개)"

    def _rule_odd_even_extreme(self, nums):
        odd = sum(1 for n in nums if n % 2 == 1)
        ok = odd not in (0, 6)
        return ok, f"홀{odd}:짝{6-odd} (0:6 / 6:0 극단 비율 제외)"

    def _rule_zone_monopoly(self, nums):
        zones = [(1, 15), (16, 30), (31, 45)]
        counts = [sum(1 for n in nums if lo <= n <= hi) for lo, hi in zones]
        ok = max(counts) < 5  # 한 구간에 5개 이상 몰리면 제외
        return ok, f"구간분포 {counts} (한 구간 5개 이상 독점 제외)"

    def _rule_ac_value_min(self, nums):
        diffs = {abs(a - b) for a, b in combinations(nums, 2)}
        ac = len(diffs) - (len(nums) - 1)
        ok = ac >= self.ac_min_value
        return ok, f"AC값 {ac} (최소 {self.ac_min_value} 이상, 너무 규칙적인 조합 제외)"

    def _rule_exclude_prior_winners(self, nums):
        if self.db is None:
            return True, "DB 없음 - 검사 생략"
        if self._prior_sets is None:
            self._prior_sets = [
                frozenset([r["n1"], r["n2"], r["n3"], r["n4"], r["n5"], r["n6"]])
                for r in self.db.get_all_draws()
            ]
        target = frozenset(nums)
        ok = target not in self._prior_sets
        return ok, "역대 당첨조합과 완전 동일하지 않음" if ok else "⚠ 역대 당첨조합과 완전히 동일함"

    _RULE_MAP = {
        "sum_range": ("총합 범위", _rule_sum_range),
        "max_consecutive": ("연속번호 개수 제한", _rule_max_consecutive),
        "odd_even_extreme": ("홀짝 극단(6:0) 제외", _rule_odd_even_extreme),
        "zone_monopoly": ("구간 독점 제외", _rule_zone_monopoly),
        "ac_value_min": ("AC값(복잡도) 최소값", _rule_ac_value_min),
        "exclude_prior_winners": ("역대 당첨조합 제외", _rule_exclude_prior_winners),
    }

    def rule_labels(self):
        return {k: v[0] for k, v in self._RULE_MAP.items()}

    def check(self, nums: list[int]) -> tuple[bool, list[str]]:
        """모든 활성화된 규칙을 검사. (전체통과여부, 각 규칙 결과 메시지 리스트)"""
        messages = []
        passed_all = True
        for key, (label, func) in self._RULE_MAP.items():
            if not self.enabled.get(key, False):
                continue
            ok, msg = func(self, nums)
            messages.append(f"{'✅' if ok else '❌'} {label}: {msg}")
            if not ok:
                passed_all = False
        return passed_all, messages


def generate_with_filters(generate_fn, filter_obj: PatternMaskFilter, max_tries: int = 500):
    """
    generate_fn() -> list[int] (6개 번호) 를 반복 호출하여
    filter_obj를 통과하는 조합을 찾는다. 못 찾으면 (None, 마지막 검사결과) 반환.
    """
    last_messages = []
    for _ in range(max_tries):
        candidate = generate_fn()
        ok, messages = filter_obj.check(candidate)
        last_messages = messages
        if ok:
            return candidate, messages
    return None, last_messages
