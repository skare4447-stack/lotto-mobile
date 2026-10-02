"""저장된 조합을 특정 회차 당첨번호와 대조해 등수를 판정한다."""


def judge(numbers: list[int], draw_row) -> str:
    win_nums = {draw_row["n1"], draw_row["n2"], draw_row["n3"],
                draw_row["n4"], draw_row["n5"], draw_row["n6"]}
    bonus = draw_row["bonus"]
    match = len(set(numbers) & win_nums)
    has_bonus = bonus in numbers

    if match == 6:
        return "1등"
    if match == 5 and has_bonus:
        return "2등"
    if match == 5:
        return "3등"
    if match == 4:
        return "4등"
    if match == 3:
        return "5등"
    return "낙첨"


def check_saved_combinations(db):
    """저장된 미확인 조합들을 최신 회차 기준으로 자동 확인"""
    latest_round = db.get_latest_round()
    latest_draw = db.get_draw(latest_round)
    updated = []
    for comb in db.get_saved_combinations():
        if comb["checked_round"] == latest_round:
            continue
        numbers = [comb["n1"], comb["n2"], comb["n3"], comb["n4"], comb["n5"], comb["n6"]]
        result = judge(numbers, latest_draw)
        db.update_combination_result(comb["id"], latest_round, result)
        updated.append((comb["id"], result))
    return updated
