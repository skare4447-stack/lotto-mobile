"""커피아자씨 로또 AI - 모바일(안드로이드) 앱 진입점

KivyMD 2.0의 MD3 네비게이션 위젯은 버전별로 API 변동이 커서,
대신 직접 만든 심플한 하단 탭바 + 표준 Kivy ScreenManager 조합을 사용한다.
(더 예측 가능하고 유지보수가 쉬움)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kivy.core.window import Window
from kivy.core.text import LabelBase
from kivy.metrics import dp
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDIconButton
from kivymd.uix.label import MDLabel

from db.database import LottoDB
from screens.generate_screen import GenerateScreen
from screens.advanced_screen import AdvancedScreen
from screens.my_combos_screen import MyCombosScreen
from screens.store_screen import StoreScreen
from screens.dashboard_screen import DashboardScreen

# 개발 중 데스크톱 미리보기 창 크기 (실제 APK에서는 전체화면으로 동작)
if os.environ.get("LOTTO_DESKTOP_PREVIEW"):
    Window.size = (420, 780)

# 한글 폰트 등록 - KivyMD 기본 폰트(Roboto 계열)는 한글 글리프가 없어서
# 화면에 네모(□)로 깨져 보이므로, 앱 전체에서 쓰이는 모든 폰트 패밀리명을
# 나눔고딕으로 덮어씌운다. (한글+영문+숫자 모두 정상 표시)
_FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "fonts")
_KR_REGULAR = os.path.join(_FONT_DIR, "NanumGothic-Regular.ttf")
_KR_BOLD = os.path.join(_FONT_DIR, "NanumGothic-Bold.ttf")
for _family in ("Roboto", "RobotoThin", "RobotoLight", "RobotoMedium", "RobotoBlack"):
    LabelBase.register(
        name=_family,
        fn_regular=_KR_REGULAR,
        fn_bold=_KR_BOLD,
        fn_italic=_KR_REGULAR,
        fn_bolditalic=_KR_BOLD,
    )

# 앱 전체 배경 - MDBoxLayout/Screen 등 일반 레이아웃은 기본적으로 투명이라
# 지정 안 하면 Window 기본 배경(흰색)이 그대로 비쳐 보인다. PC버전의 어두운
# 보라 톤 테마와 맞춰서 창 배경 자체를 어둡게 깔아준다.
Window.clearcolor = (0.07, 0.06, 0.14, 1)

NAV_ITEMS = [
    ("generate", "dice-multiple", "번호생성"),
    ("advanced", "chart-bell-curve", "고급생성"),
    ("combos", "folder-star", "내조합"),
    ("store", "storefront", "판매점"),
    ("dashboard", "chart-box", "당첨결과"),
]

ACTIVE_COLOR = (0.78, 0.29, 0.90, 1)
INACTIVE_COLOR = (0.7, 0.65, 0.85, 1)


class NavItem(MDBoxLayout):
    def __init__(self, name, icon, label, on_press, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.name = name
        self.on_press_cb = on_press
        self.icon_btn = MDIconButton(icon=icon, theme_icon_color="Custom", icon_color=INACTIVE_COLOR)
        self.icon_btn.bind(on_release=lambda *_: self.on_press_cb(self.name))
        self.label = MDLabel(
            text=label,
            halign="center",
            font_style="Label",
            role="small",
            theme_text_color="Custom",
            text_color=INACTIVE_COLOR,
            size_hint_y=None,
            height=dp(16),
        )
        self.add_widget(self.icon_btn)
        self.add_widget(self.label)

    def set_active(self, active: bool):
        color = ACTIVE_COLOR if active else INACTIVE_COLOR
        self.icon_btn.icon_color = color
        self.label.text_color = color


class RootLayout(MDBoxLayout):
    def __init__(self, db, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.db = db

        self.sm = ScreenManager(transition=NoTransition())
        for name, screen_cls_widget in self._build_screens():
            screen = Screen(name=name)
            screen.add_widget(screen_cls_widget)
            self.sm.add_widget(screen)
        self.add_widget(self.sm)

        nav_bar = MDBoxLayout(
            size_hint_y=None,
            height=dp(64),
            md_bg_color=(0.11, 0.09, 0.22, 1),
            padding=(dp(4), dp(4)),
        )
        self.nav_items = {}
        for name, icon, label in NAV_ITEMS:
            item = NavItem(name, icon, label, on_press=self.switch)
            self.nav_items[name] = item
            nav_bar.add_widget(item)
        self.add_widget(nav_bar)

        self.switch("generate")

    def _build_screens(self):
        return [
            ("generate", GenerateScreen(self.db)),
            ("advanced", AdvancedScreen(self.db)),
            ("combos", MyCombosScreen(self.db)),
            ("store", StoreScreen()),
            ("dashboard", DashboardScreen(self.db)),
        ]

    def switch(self, name):
        self.sm.current = name
        for n, item in self.nav_items.items():
            item.set_active(n == name)


class LottoCoffeeApp(MDApp):
    def build(self):
        self.title = "커피아자씨 로또 AI"
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Purple"

        self.db = LottoDB()
        return RootLayout(self.db)


if __name__ == "__main__":
    LottoCoffeeApp().run()
