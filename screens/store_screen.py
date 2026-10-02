"""판매점 찾기 화면: GPS 기반 내 주변 검색 + 시/도-구/군 수동 검색"""
import math
import threading

from kivy.clock import mainthread
from kivy.metrics import dp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.label import MDLabel
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.menu import MDDropdownMenu

from api import store_finder
from screens.widgets_common import autosize_label
from screens.toast import toast

# 시/도 대략적인 중심 좌표 (GPS 위치 -> 가장 가까운 시/도를 추정하는 용도).
# 정확한 구/군까지는 못 짚어도, "내 주변" 검색의 출발점으로 충분히 실용적임.
PROVINCE_CENTERS = {
    "서울특별시": (37.5665, 126.9780),
    "부산광역시": (35.1796, 129.0756),
    "대구광역시": (35.8714, 128.6014),
    "인천광역시": (37.4563, 126.7052),
    "대전광역시": (36.3504, 127.3845),
    "울산광역시": (35.5384, 129.3114),
    "세종특별자치시": (36.4800, 127.2890),
    "경기도": (37.4138, 127.5183),
    "강원특별자치도": (37.8228, 128.1555),
    "충청북도": (36.6357, 127.4914),
    "충청남도": (36.5184, 126.8000),
    "전북특별자치도": (35.7175, 127.1530),
    "전남광주통합특별시": (35.1595, 126.8526),
    "경상북도": (36.4919, 128.8889),
    "경상남도": (35.4606, 128.2132),
    "제주특별자치도": (33.4996, 126.5312),
}


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def nearest_province(lat, lon) -> str:
    return min(
        PROVINCE_CENTERS,
        key=lambda name: haversine_km(lat, lon, *PROVINCE_CENTERS[name]),
    )


class StoreRow(MDBoxLayout):
    def __init__(self, store: dict, distance_km: float = None, **kwargs):
        super().__init__(
            orientation="vertical",
            size_hint_y=None,
            padding=dp(10),
            spacing=dp(4),
            md_bg_color=(0.16, 0.13, 0.28, 1),
            radius=[dp(10)],
            **kwargs,
        )
        self.store = store

        name = store.get("name") or "(이름 없음)"
        badge = "  [6/45]" if store.get("sells_645") else ""
        dist_txt = f"  ·  {distance_km:.1f}km" if distance_km is not None else ""
        top = MDBoxLayout(size_hint_y=None, height=dp(26))
        top.add_widget(
            MDLabel(text=f"{name}{badge}{dist_txt}", bold=True, size_hint_x=1)
        )
        map_btn = MDButton(MDButtonText(text="지도"), style="text", size_hint=(None, None), height=dp(30), width=dp(50))
        map_btn.bind(on_release=lambda *_: self.open_map())
        top.add_widget(map_btn)
        self.add_widget(top)

        addr_label = autosize_label(
            MDLabel(
                text=store.get("address") or "-",
                theme_text_color="Secondary",
                size_hint_y=None,
                halign="left",
                font_style="Label",
            )
        )
        self.add_widget(addr_label)

        phone = store.get("phone") or "전화번호 정보 없음"
        self.add_widget(
            MDLabel(
                text=phone, theme_text_color="Secondary", size_hint_y=None, height=dp(20),
                font_style="Label",
            )
        )
        self.bind(minimum_height=self.setter("height"))

    def open_map(self):
        import webbrowser
        webbrowser.open(store_finder.naver_map_url(self.store))


class StoreScreen(MDBoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=dp(16), spacing=dp(10), **kwargs)
        self.user_lat = None
        self.user_lon = None
        self.province_menu = None
        self.district_menu = None
        self.selected_province = None
        self.selected_district = ""

        self.add_widget(
            MDLabel(text="로또 판매점 찾기", font_style="Title", role="small", size_hint_y=None, height=dp(30))
        )

        gps_btn = MDButton(MDButtonText(text="내 위치로 주변 판매점 찾기"), style="filled")
        gps_btn.bind(on_release=lambda *_: self.use_gps())
        self.add_widget(gps_btn)

        divider = MDLabel(
            text="또는 지역 직접 선택", theme_text_color="Secondary", size_hint_y=None,
            height=dp(24), halign="center",
        )
        self.add_widget(divider)

        select_row = MDBoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        self.province_btn = MDButton(MDButtonText(text="시/도 선택"), style="outlined")
        self.province_btn.bind(on_release=self.open_province_menu)
        self.district_btn = MDButton(MDButtonText(text="구/군: 전체"), style="outlined")
        self.district_btn.bind(on_release=self.open_district_menu)
        select_row.add_widget(self.province_btn)
        select_row.add_widget(self.district_btn)
        self.add_widget(select_row)

        search_btn = MDButton(MDButtonText(text="판매점 검색"), style="tonal")
        search_btn.bind(on_release=lambda *_: self.search_manual())
        self.add_widget(search_btn)

        self.status_label = MDLabel(
            text="위치를 사용하거나 지역을 선택해 검색해보세요.",
            theme_text_color="Secondary",
            size_hint_y=None,
            height=dp(24),
        )
        self.add_widget(self.status_label)

        scroll = MDScrollView()
        self.result_box = MDBoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(8))
        self.result_box.bind(minimum_height=self.result_box.setter("height"))
        scroll.add_widget(self.result_box)
        self.add_widget(scroll)

    # ---------- 시/도, 구/군 수동 선택 ----------
    def open_province_menu(self, *_):
        items = [
            {"text": name, "on_release": lambda n=name: self.select_province(n)}
            for name in store_finder.province_display_names()
        ]
        self.province_menu = MDDropdownMenu(caller=self.province_btn, items=items, width_mult=4)
        self.province_menu.open()

    def select_province(self, name):
        self.selected_province = name
        self.province_btn.children[0].text = name
        self.selected_district = ""
        self.district_btn.children[0].text = "구/군: 전체"
        if self.province_menu:
            self.province_menu.dismiss()
        self._load_districts_async(name)

    def _load_districts_async(self, province):
        def worker():
            try:
                districts = store_finder.fetch_districts(province)
            except Exception:
                districts = []
            self._on_districts(districts)

        threading.Thread(target=worker, daemon=True).start()

    @mainthread
    def _on_districts(self, districts):
        self._districts = districts

    def open_district_menu(self, *_):
        if not self.selected_province:
            toast("시/도를 먼저 선택해주세요")
            return
        districts = getattr(self, "_districts", [])
        items = [{"text": "전체", "on_release": lambda: self.select_district("")}]
        items += [{"text": d, "on_release": lambda d=d: self.select_district(d)} for d in districts]
        self.district_menu = MDDropdownMenu(caller=self.district_btn, items=items, width_mult=4)
        self.district_menu.open()

    def select_district(self, district):
        self.selected_district = district
        self.district_btn.children[0].text = f"구/군: {district or '전체'}"
        if self.district_menu:
            self.district_menu.dismiss()

    def search_manual(self):
        if not self.selected_province:
            toast("시/도를 먼저 선택해주세요")
            return
        self.status_label.text = "검색 중..."
        self.result_box.clear_widgets()
        province, district = self.selected_province, self.selected_district

        def worker():
            try:
                stores = store_finder.search_stores(province, district)
                self._on_search_result(stores, None)
            except Exception as e:
                self._on_search_result([], str(e))

        threading.Thread(target=worker, daemon=True).start()

    # ---------- GPS ----------
    def use_gps(self):
        self.status_label.text = "위치 확인 중..."
        try:
            from plyer import gps

            gps.configure(on_location=self._on_gps_location, on_status=self._on_gps_status)
            gps.start(minTime=1000, minDistance=0)
        except Exception as e:
            # 데스크톱 등 GPS 미지원 환경 - 개발 미리보기용 폴백(서울시청 좌표)
            toast(f"이 기기에서는 GPS를 사용할 수 없어요 ({e}). 지역을 직접 선택해주세요")
            self.status_label.text = "GPS 사용 불가 - 지역을 직접 선택해주세요"

    def _on_gps_status(self, stype, status):
        pass

    def _on_gps_location(self, **kwargs):
        lat = kwargs.get("lat")
        lon = kwargs.get("lon")
        if lat is None or lon is None:
            return
        try:
            from plyer import gps
            gps.stop()
        except Exception:
            pass
        self.user_lat, self.user_lon = lat, lon
        self._search_by_location(lat, lon)

    @mainthread
    def _search_by_location(self, lat, lon):
        province = nearest_province(lat, lon)
        self.status_label.text = f"현재 위치 기준 '{province}' 판매점 검색 중..."
        self.result_box.clear_widgets()

        def worker():
            try:
                stores = store_finder.search_stores(province, "")
                for s in stores:
                    if s.get("lat") and s.get("lon"):
                        s["_distance"] = haversine_km(lat, lon, s["lat"], s["lon"])
                    else:
                        s["_distance"] = None
                stores.sort(key=lambda s: (s["_distance"] is None, s["_distance"]))
                self._on_search_result(stores[:30], None)
            except Exception as e:
                self._on_search_result([], str(e))

        threading.Thread(target=worker, daemon=True).start()

    @mainthread
    def _on_search_result(self, stores, error):
        self.result_box.clear_widgets()
        if error:
            self.status_label.text = "검색에 실패했습니다."
            toast(f"판매점 검색 실패: {error}")
            return
        if not stores:
            self.status_label.text = "검색 결과가 없습니다."
            return
        self.status_label.text = f"총 {len(stores)}개 판매점을 찾았습니다."
        for s in stores:
            self.result_box.add_widget(StoreRow(s, distance_km=s.get("_distance")))
