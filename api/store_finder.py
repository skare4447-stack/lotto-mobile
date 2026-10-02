"""로또645 판매점 찾기 - 동행복권 판매점 검색 API 클라이언트

동행복권 홈페이지(https://dhlottery.co.kr/prchsplcsrch/home)의 판매점 찾기 기능이
사용하는 내부 AJAX 엔드포인트를 그대로 사용합니다.

- 시/도 선택 시 구/군 목록 조회: GET /prchsplcsrch/selectAdmdst.do?srchCtpvNm={전체시도명}
- 판매점 검색: GET /prchsplcsrch/selectLtShp.do?...&srchCtpvNm={축약시도명}&srchSggNm={구군명}

⚠ 비공식 API이므로 동행복권 사이트 개편 시 주소/파라미터가 바뀔 수 있습니다.
"""
import requests

BASE_URL = "https://www.dhlottery.co.kr"

HEADERS = {
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Referer": "https://www.dhlottery.co.kr/prchsplcsrch/home",
}

# 시/도 드롭다운에 실제 표시되는 전체 명칭 (selectAdmdst.do 호출 시 사용)
PROVINCE_FULL_NAMES = [
    "서울특별시",
    "부산광역시",
    "대구광역시",
    "인천광역시",
    "대전광역시",
    "울산광역시",
    "세종특별자치시",
    "경기도",
    "강원도",           # 화면 표시는 "강원특별자치도"지만 API 파라미터 값은 "강원도"
    "충청북도",
    "충청남도",
    "전라북도",         # 화면 표시는 "전북특별자치도"지만 API 파라미터 값은 "전라북도"
    "전남광주통합특별시",
    "경상북도",
    "경상남도",
    "제주특별자치도",
]

# 화면에 보여줄 예쁜 이름 (UI 드롭다운 표시용) -> 실제 API 파라미터로 쓰는 전체 명칭
PROVINCE_DISPLAY_TO_FULL = {
    "서울특별시": "서울특별시",
    "부산광역시": "부산광역시",
    "대구광역시": "대구광역시",
    "인천광역시": "인천광역시",
    "대전광역시": "대전광역시",
    "울산광역시": "울산광역시",
    "세종특별자치시": "세종특별자치시",
    "경기도": "경기도",
    "강원특별자치도": "강원도",
    "충청북도": "충청북도",
    "충청남도": "충청남도",
    "전북특별자치도": "전라북도",
    "전남광주통합특별시": "전남광주통합특별시",
    "경상북도": "경상북도",
    "경상남도": "경상남도",
    "제주특별자치도": "제주특별자치도",
}

# 전체 시/도 명칭 -> 판매점 검색(selectLtShp.do)에 필요한 축약 코드
# 동행복권 페이지 자체 JS(PrchsPlcSrchM.ctpvMap)에서 그대로 가져온 검증된 매핑
CTPV_FULL_TO_SHORT = {
    "서울특별시": "서울",
    "경기도": "경기",
    "부산광역시": "부산",
    "대구광역시": "대구",
    "인천광역시": "인천",
    "대전광역시": "대전",
    "울산광역시": "울산",
    "강원도": "강원",
    "충청북도": "충북",
    "충청남도": "충남",
    "전남광주통합특별시": "전남광주",
    "전라북도": "전북",
    "경상북도": "경북",
    "경상남도": "경남",
    "제주특별자치도": "제주",
    "세종특별자치시": "세종",
}


def province_display_names() -> list[str]:
    """UI 드롭다운에 표시할 시/도 이름 목록 (동행복권 화면 표기 그대로)"""
    return list(PROVINCE_DISPLAY_TO_FULL.keys())


def fetch_districts(province_display_name: str, timeout: int = 10) -> list[str]:
    """선택한 시/도의 구/군 목록을 조회한다.

    province_display_name: province_display_names()에서 고른 값
        (예: "서울특별시", "강원특별자치도", "전북특별자치도" 등)
    """
    full_name = PROVINCE_DISPLAY_TO_FULL.get(province_display_name, province_display_name)
    resp = requests.get(
        f"{BASE_URL}/prchsplcsrch/selectAdmdst.do",
        params={"srchCtpvNm": full_name},
        headers=HEADERS,
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    items = ((data or {}).get("data") or {}).get("list") or []
    return [item["sggNm"] for item in items if item.get("sggNm")]


def search_stores(
    province_display_name: str,
    district: str = "",
    only_lotto645: bool = True,
    page_num: int = 1,
    record_count_per_page: int = 200,
    timeout: int = 10,
) -> list[dict]:
    """판매점을 검색한다.

    province_display_name: province_display_names()에서 고른 값
    district: fetch_districts()가 반환한 구/군 이름. 빈 문자열이면 시/도 전체 검색.
    only_lotto645: True면 로또6/45 판매 가능 판매점만 필터링

    반환값의 각 dict는 다음 키를 포함:
        name, phone, address, road_address, lat, lon, sells_645
    """
    full_name = PROVINCE_DISPLAY_TO_FULL.get(province_display_name, province_display_name)
    short_name = CTPV_FULL_TO_SHORT.get(full_name, full_name)

    params = {
        "l645LtNtslYn": "Y" if only_lotto645 else "N",
        "l520LtNtslYn": "N",
        "st5LtNtslYn": "N",
        "st10LtNtslYn": "N",
        "st20LtNtslYn": "N",
        "cpexUsePsbltyYn": "N",
        "pageNum": page_num,
        "recordCountPerPage": record_count_per_page,
        "pageCount": 5,
        "srchCtpvNm": short_name,
        "srchSggNm": district,
    }
    resp = requests.get(
        f"{BASE_URL}/prchsplcsrch/selectLtShp.do",
        params=params,
        headers=HEADERS,
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    items = ((data or {}).get("data") or {}).get("list") or []

    results = []
    for item in items:
        if only_lotto645 and item.get("l645LtNtslYn") != "Y":
            continue
        results.append(
            {
                "name": item.get("conmNm") or "",
                "phone": item.get("shpTelno") or "",
                "address": item.get("bplcRdnmDaddr") or item.get("bplcLctnDaddr") or "",
                "sido": item.get("tm1BplcLctnAddr") or "",
                "sigungu": item.get("tm2BplcLctnAddr") or "",
                "dong": item.get("tm3BplcLctnAddr") or "",
                "lat": item.get("shpLat"),
                "lon": item.get("shpLot"),
                "sells_645": item.get("l645LtNtslYn") == "Y",
            }
        )
    return results


def naver_map_url(store: dict) -> str:
    """판매점 위치를 네이버 지도에서 바로 보여주는 검색 URL 생성 (상호+주소로 검색)"""
    from urllib.parse import quote

    name = store.get("name") or "로또판매점"
    address = store.get("address") or ""
    query = f"{name} {address}".strip()
    return f"https://map.naver.com/p/search/{quote(query)}"
