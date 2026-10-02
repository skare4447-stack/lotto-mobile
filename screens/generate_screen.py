"""번호 생성 화면: AI 자동생성 / 직접 선택(수동+선택조합 통합)"""
from kivy.metrics import dp
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.label import MDLabel
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.menu import MDDropdownMenu

from algorithms.generators import ALL_GENERATORS
from algorithms.validators import recompute_all
from screens.widgets_common import LottoBall, NumberToggleGrid, PillTabButton, autosize_label
from screens.toast import toast


class ResultRow(MDBoxLayout):
    def __init__(self, numbers: list[int], comment: str = "", **kwargs):
        super().__init__(
            orientation="vertical", size_hint_y=None, padding=dp(10), spacing=dp(6), **kwargs
        )
        self.numbers = numbers
        balls_row = MDBoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))
        for n in numbers:
            balls_row.add_widget(LottoBall(n))
        self.add_widget(balls_row)
        if comment:
            label = autosize_label(
                MDLabel(
                    text=comment,
                    font_style="Label",
                    theme_text_color="Secondary",
                    size_hint_y=None,
                    halign="left",
                )
            )
            self.add_widget(label)
        self.bind(minimum_height=self.setter("height"))


MAX_GAMES = 20


class AutoModeScreen(Screen):
    def __init__(self, db, **kwargs):
        super().__init__(name="auto", **kwargs)
        self.db = db
        self.last_batch: list[list[int]] = []
        self.menu = None
        self.count_menu = None
        self.game_count = 1

        root = MDBoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))

        self.engine_btn = MDButton(
            MDButtonText(text="엔진 선택: 빈도분석 AI"), style="outlined"
        )
        self.engine_btn.bind(on_release=self.open_menu)
        root.add_widget(self.engine_btn)
        self.selected_engine = ALL_GENERATORS[0]

        count_row = MDBoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        count_row.add_widget(
            MDLabel(text="게임 수", theme_text_color="Secondary", size_hint_x=None, width=dp(60))
        )
        self.count_btn = MDButton(MDButtonText(text="1게임"), style="outlined")
        self.count_btn.bind(on_release=self.open_count_menu)
        count_row.add_widget(self.count_btn)
        root.add_widget(count_row)

        gen_btn = MDButton(MDButtonText(text="번호 생성"), style="filled")
        gen_btn.bind(on_release=lambda *_: self.generate())
        root.add_widget(gen_btn)

        scroll = MDScrollView()
        self.result_box = MDBoxLayout(
            orientation="vertical", size_hint_y=None, spacing=dp(10)
        )
        self.result_box.bind(minimum_height=self.result_box.setter("height"))
        scroll.add_widget(self.result_box)
        root.add_widget(scroll)

        save_btn = MDButton(MDButtonText(text="전체 저장"), style="tonal")
        save_btn.bind(on_release=lambda *_: self.save())
        root.add_widget(save_btn)

        self.add_widget(root)

    def open_menu(self, *_):
        items = [
            {
                "text": eng.name,
                "on_release": lambda e=eng: self.select_engine(e),
            }
            for eng in ALL_GENERATORS
        ]
        self.menu = MDDropdownMenu(caller=self.engine_btn, items=items, width_mult=4)
        self.menu.open()

    def select_engine(self, engine):
        self.selected_engine = engine
        self.engine_btn.children[0].text = f"엔진 선택: {engine.name}"
        if self.menu:
            self.menu.dismiss()

    def open_count_menu(self, *_):
        items = [
            {"text": f"{n}게임", "on_release": lambda n=n: self.select_count(n)}
            for n in range(1, MAX_GAMES + 1)
        ]
        self.count_menu = MDDropdownMenu(caller=self.count_btn, items=items, width_mult=3)
        self.count_menu.open()

    def select_count(self, n):
        self.game_count = n
        self.count_btn.children[0].text = f"{n}게임"
        if self.count_menu:
            self.count_menu.dismiss()

    def generate(self):
        batch = []
        seen = set()
        # 한 번에 여러 게임을 뽑을 때 배치 내에서 완전히 같은 조합이 겹치지 않도록
        # (실물 로또 용지 5게임처럼) 약간의 재시도를 둔다.
        for _ in range(self.game_count):
            for _try in range(10):
                numbers = sorted(self.selected_engine.generate(self.db))
                key = tuple(numbers)
                if key not in seen or _try == 9:
                    seen.add(key)
                    batch.append(numbers)
                    break

        self.last_batch = batch
        self.result_box.clear_widgets()
        for i, numbers in enumerate(batch, 1):
            recomputed = recompute_all(numbers, self.db)
            top_comments = [r["comment"] for r in recomputed["results"][:2]]
            comment = f"{i}게임 · 재계산 점수 {recomputed['overall_score']}점 · " + " / ".join(top_comments)
            self.result_box.add_widget(ResultRow(numbers, comment))

    def save(self):
        if not self.last_batch:
            toast("먼저 번호를 생성해주세요")
            return
        for numbers in self.last_batch:
            self.db.save_combination(numbers, source=f"자동·{self.selected_engine.name}")
        toast(f"{len(self.last_batch)}게임을 저장했습니다")


class ManualModeScreen(Screen):
    def __init__(self, db, **kwargs):
        super().__init__(name="manual", **kwargs)
        self.db = db

        root = MDBoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
        root.add_widget(
            MDLabel(
                text="번호 6개를 직접 골라주세요",
                font_style="Title",
                role="small",
                size_hint_y=None,
                height=dp(30),
            )
        )
        self.status_label = MDLabel(
            text="0/6 선택됨", theme_text_color="Secondary", size_hint_y=None, height=dp(24)
        )
        root.add_widget(self.status_label)

        scroll = MDScrollView(size_hint_y=None, height=dp(320))
        self.grid = NumberToggleGrid(max_select=6, on_change=self.on_change)
        scroll.add_widget(self.grid)
        root.add_widget(scroll)

        btn_row = MDBoxLayout(size_hint_y=None, height=dp(48), spacing=dp(10))
        clear_btn = MDButton(MDButtonText(text="초기화"), style="outlined")
        clear_btn.bind(on_release=lambda *_: self.grid.clear())
        save_btn = MDButton(MDButtonText(text="저장"), style="filled")
        save_btn.bind(on_release=lambda *_: self.save())
        btn_row.add_widget(clear_btn)
        btn_row.add_widget(save_btn)
        root.add_widget(btn_row)

        self.add_widget(root)

    def on_change(self, selected):
        self.status_label.text = f"{len(selected)}/6 선택됨"

    def save(self):
        if len(self.grid.selected) != 6:
            toast("6개를 모두 선택해주세요")
            return
        self.db.save_combination(self.grid.selected, source="수동/선택")
        toast("저장했습니다")
        self.grid.clear()


class GenerateScreen(MDBoxLayout):
    def __init__(self, db, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.db = db

        tab_row = MDBoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8), padding=dp(8))
        self.btn_auto = PillTabButton("AI 자동생성", active=True)
        self.btn_manual = PillTabButton("직접 선택", active=False)
        self.btn_auto.bind(on_release=lambda *_: self.switch("auto"))
        self.btn_manual.bind(on_release=lambda *_: self.switch("manual"))
        tab_row.add_widget(self.btn_auto)
        tab_row.add_widget(self.btn_manual)
        self.add_widget(tab_row)

        self.sm = ScreenManager(transition=NoTransition())
        self.sm.add_widget(AutoModeScreen(db))
        self.sm.add_widget(ManualModeScreen(db))
        self.add_widget(self.sm)

    def switch(self, name):
        self.sm.current = name
        self.btn_auto.set_active(name == "auto")
        self.btn_manual.set_active(name == "manual")
