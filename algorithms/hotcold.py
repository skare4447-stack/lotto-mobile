"""핫/콜드 존 가중치 그리드 엔진"""
import random

from db.database import LottoDB


def zone_map(db: LottoDB) -> dict[int, str]:
    """전체 45개 번호를 역대 출현빈도 기준 상위/중위/하위 3등분으로 분류"""
    freq = db.number_frequency()
    ordered = sorted(freq.items(), key=lambda x: -x[1])
    n = len(ordered)
    hot_cut = n // 3
    warm_cut = 2 * n // 3
    zones = {}
    for i, (num, _) in enumerate(ordered):
        if i < hot_cut:
            zones[num] = "hot"
        elif i < warm_cut:
            zones[num] = "warm"
        else:
            zones[num] = "cold"
    return zones


def generate_weighted(
    db: LottoDB,
    hot_weight: float = 1.0,
    warm_weight: float = 1.0,
    cold_weight: float = 1.0,
    pinned: list[int] | None = None,
    excluded: list[int] | None = None,
) -> list[int]:
    """
    핫/콜드 존별 가중치 슬라이더 값을 반영해 6개 번호를 뽑는다.
    pinned: 반드시 포함할 번호, excluded: 후보에서 제외할 번호
    """
    pinned = pinned or []
    excluded = set(excluded or [])
    zones = zone_map(db)
    freq = db.number_frequency()

    weight_by_zone = {"hot": hot_weight, "warm": warm_weight, "cold": cold_weight}

    pool = [n for n in range(1, 46) if n not in excluded and n not in pinned]
    weights = [max(freq[n], 1) * weight_by_zone[zones[n]] for n in pool]

    selected = list(pinned)
    need = 6 - len(selected)
    if need < 0:
        raise ValueError("고정 번호는 최대 6개까지만 가능합니다.")

    while need > 0 and pool:
        n = random.choices(pool, weights=weights, k=1)[0]
        idx = pool.index(n)
        pool.pop(idx)
        weights.pop(idx)
        selected.append(n)
        need -= 1

    return sorted(selected)
