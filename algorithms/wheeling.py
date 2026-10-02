"""
휠링 시스템(Wheeling System)
사용자가 고른 '번호 풀'로 여러 장의 6개 조합 티켓을 만들어,
풀 안에서 일정 개수 이상 맞았을 때 최소 등수를 보장받을 확률을 높이는
실제 로또 전략에서 쓰이는 조합 설계 기법이다.

- full_wheel: 번호 풀의 모든 6-조합 (완전 보장, 티켓 수 많음)
- greedy_abbreviated_wheel: 그리디 커버링 디자인으로 티켓 수를 줄인 축소휠
  (풀에서 뽑은 모든 k-부분집합을 최소 한 장 이상의 티켓이 포함하도록 그리디하게 구성)

※ 여전히 당첨 확률 자체(무작위 추첨)를 높이는 것은 아니며,
   '번호 풀을 좁혀서 그 안에서 조합을 체계적으로 배분'하는 기법이다.
"""
from itertools import combinations
import math

MAX_FULL_WHEEL_POOL = 12  # C(12,6)=924, 그 이상은 폭발적으로 커짐


def full_wheel(pool: list[int]) -> list[list[int]]:
    if len(pool) < 6:
        raise ValueError("번호 풀은 최소 6개 이상이어야 합니다.")
    if len(pool) > MAX_FULL_WHEEL_POOL:
        raise ValueError(
            f"완전휠은 번호 풀 {MAX_FULL_WHEEL_POOL}개 이하에서만 지원합니다. "
            f"더 많은 번호는 '축소휠'을 사용하세요."
        )
    return [sorted(c) for c in combinations(sorted(pool), 6)]


def estimate_full_wheel_tickets(pool_size: int) -> int:
    if pool_size < 6:
        return 0
    return math.comb(pool_size, 6)


def greedy_abbreviated_wheel(
    pool: list[int], guarantee_size: int = 4, max_tickets: int | None = None
) -> list[list[int]]:
    """
    그리디 커버링 알고리즘.
    풀에서 뽑을 수 있는 모든 `guarantee_size`-부분집합을 최소 1장의 티켓이
    포함하도록, 매 단계 '아직 안 덮인 부분집합을 가장 많이 덮는' 6-조합 티켓을
    하나씩 골라 추가한다. (Set Cover 근사 그리디 알고리즘)

    guarantee_size=4 라면: "내 번호 풀 중 4개가 실제로 당첨번호에 포함되면
    티켓 중 최소 1장은 4개 이상 맞는다"를 보장.
    """
    pool = sorted(pool)
    if len(pool) < 6:
        raise ValueError("번호 풀은 최소 6개 이상이어야 합니다.")
    if guarantee_size not in (3, 4):
        raise ValueError(
            "보장 개수는 3 또는 4만 지원합니다. "
            "(5 이상은 커버링에 필요한 티켓 수가 급격히 늘어 계산이 비현실적으로 오래 걸립니다)"
        )
    if len(pool) > 20:
        raise ValueError("축소휠은 번호 풀 20개까지만 지원합니다.")
    if guarantee_size == 4 and len(pool) > 17:
        raise ValueError("보장 4에서는 번호 풀을 17개 이하로 선택해주세요.")

    targets = list(combinations(pool, guarantee_size))
    target_index = {t: i for i, t in enumerate(targets)}
    all_tickets = list(combinations(pool, 6))

    # 각 티켓이 커버하는 target들을 비트마스크 정수로 표현 (고속 커버링 계산)
    ticket_masks = []
    for t in all_tickets:
        mask = 0
        for sub in combinations(t, guarantee_size):
            mask |= 1 << target_index[sub]
        ticket_masks.append(mask)

    full_mask = (1 << len(targets)) - 1
    uncovered = full_mask
    chosen_idx: list[int] = []
    used = [False] * len(all_tickets)

    while uncovered:
        best_i, best_gain = -1, 0
        for i, mask in enumerate(ticket_masks):
            if used[i]:
                continue
            gain = bin(mask & uncovered).count("1")
            if gain > best_gain:
                best_i, best_gain = i, gain
        if best_i == -1:
            break
        used[best_i] = True
        chosen_idx.append(best_i)
        uncovered &= ~ticket_masks[best_i]
        if max_tickets and len(chosen_idx) >= max_tickets:
            break

    return [sorted(all_tickets[i]) for i in chosen_idx]


def wheel_summary(pool: list[int], tickets: list[list[int]], guarantee_size: int | None = None) -> str:
    lines = [f"번호 풀: {sorted(pool)} ({len(pool)}개)", f"생성된 티켓 수: {len(tickets)}장"]
    if guarantee_size:
        lines.append(
            f"보장 조건: 풀 중 {guarantee_size}개가 실제 당첨번호에 포함되면 "
            f"최소 1장은 {guarantee_size}개 이상 일치"
        )
    return "\n".join(lines)
