"""고급 생성 화면: 휠링 시스템 / 핫콜드 그리드 / 패턴 마스크 필터"""
from kivy.metrics import dp
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.label import MDLabel
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.slider import MDSlider, MDSliderHandle
from kivymd.uix.selectioncontrol import MDSwitch

from algorithms.wheeling import full_wheel, greedy_abbreviated_wheel, estimate_full_wheel_tickets
from algorithms.hotcold import generate_weighted
from algorithms.filters import PatternMaskFilter, generate_with_filters
from algorithms.generators import ALL_GENERATORS
from screens.widgets_common import LottoBall, NumberToggleGrid, PillTabButton, autosize_label
from screens.toast import toast


def clean_msg(msg: str) -> str:
    """필터 결과 메시지의 이모지(✅/❌)를 폰트가 지원하는 텍스트로 교체"""
    return msg.replace("✅", "[통과]").replace("❌", "[실패]")


class WheelSubScreen(Screen):
    def __init__(self, db, **kwargs):
        super().__init__(name="wheel", **kwargs)
        self.db = db
        self.tickets = []

        root = MDBoxLayout(orientation="vertical", padding=dp(16), spacing=dp(10))
        root.add_widget(
            MDLabel(
                text="번호 풀을 7~17개 고르면 여러 장을 체계적으로 배분합니다.",
                theme_text_color="Secondary",
                size_hint_y=None,
                height=dp(40),
            )
        )
        self.status_label = MDLabel(
            text="0개 선택됨", size_hint_y=None, height=dp(24), theme_text_color="Custom",
            text_color=(0.98, 0.75, 0.14, 1),
        )
        root.add_widget(self.status_label)

        grid_scroll = MDScrollView(size_hint_y=None, height=dp(260))
        self.grid = NumberToggleGrid(max_select=17, on_change=self.on_change)
        grid_scroll.add_widget(self.grid)
        root.add_widget(grid_scroll)

        type_row = MDBoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        self.btn_full = PillTabButton("완전휠(100% 보장)", active=True)
        self.btn_abbrev = PillTabButton("축소휠(티켓 절감)", active=False)
        self.btn_full.bind(on_release=lambda *_: self.set_wheel_type("full"))
        self.btn_abbrev.bind(on_release=lambda *_: self.set_wheel_type("abbrev"))
        type_row.add_widget(self.btn_full)
        type_row.add_widget(self.btn_abbrev)
        root.add_widget(type_row)
        self.wheel_type = "full"

        guarantee_row = MDBoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        self.btn_g4 = PillTabButton("4개 보장", active=True)
        self.btn_g3 = PillTabButton("3개 보장", active=False)
        self.btn_g4.bind(on_release=lambda *_: self.set_guarantee(4))
        self.btn_g3.bind(on_release=lambda *_: self.set_guarantee(3))
        guarantee_row.add_widget(self.btn_g4)
        guarantee_row.add_widget(self.btn_g3)
        self.guarantee_row = guarantee_row
        self.guarantee = 4
        root.add_widget(guarantee_row)
        self.set_wheel_type("full")

        gen_btn = MDButton(MDButtonText(text="휠 생성하기"), style="filled")
        gen_btn.bind(on_release=lambda *_: self.generate())
        root.add_widget(gen_btn)

        self.summary_label = MDLabel(text="", size_hint_y=None, height=dp(40), theme_text_color="Secondary")
        root.add_widget(self.summary_label)

        ticket_scroll = MDScrollView()
        self.ticket_box = MDBoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(8))
        self.ticket_box.bind(minimum_height=self.ticket_box.setter("height"))
        ticket_scroll.add_widget(self.ticket_box)
        root.add_widget(ticket_scroll)

        save_btn = MDButton(MDButtonText(text="생성된 티켓 전체 저장"), style="tonal")
        save_btn.bind(on_release=lambda *_: self.save_all())
        root.add_widget(save_btn)

        self.add_widget(root)

    def on_change(self, selected):
        self.status_label.text = f"{len(selected)}개 선택됨 (최소 7개)"

    def set_wheel_type(self, wt):
        self.wheel_type = wt
        self.btn_full.set_active(wt == "full")
        self.btn_abbrev.set_active(wt == "abbrev")
        self.guarantee_row.opacity = 1 if wt == "abbrev" else 0.3
        self.guarantee_row.disabled = wt != "abbrev"

    def set_guarantee(self, g):
        self.guarantee = g
        self.btn_g4.set_active(g == 4)
        self.btn_g3.set_active(g == 3)

    def generate(self):
        pool = sorted(self.grid.selected)
        if len(pool) < 7:
            toast("번호 풀은 최소 7개 이상 선택해주세요")
            return
        try:
            if self.wheel_type == "full":
                est = estimate_full_wheel_tickets(len(pool))
                if est > 500:
                    toast(f"완전휠은 {est}장이 생성돼요. 풀을 줄여주세요")
                    return
                tickets = full_wheel(pool)
                guarantee = 6
            else:
                tickets = greedy_abbreviated_wheel(pool, guarantee_size=self.guarantee)
                guarantee = self.guarantee
        except ValueError as e:
            toast(str(e))
            return

        self.tickets = tickets
        self.summary_label.text = (
            f"번호 풀 {len(pool)}개 -> 총 {len(tickets)}장 생성 "
            f"(풀 중 {guarantee}개 적중 시 최소 1장 {guarantee}개 이상 일치 보장)"
        )
        self.render_tickets()

    def render_tickets(self):
        self.ticket_box.clear_widgets()
        for i, ticket in enumerate(self.tickets, 1):
            row = MDBoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))
            row.add_widget(
                MDLabel(text=f"{i}", size_hint_x=None, width=dp(24), theme_text_color="Secondary")
            )
            for n in ticket:
                row.add_widget(LottoBall(n, size_dp=30))
            self.ticket_box.add_widget(row)

    def save_all(self):
        if not self.tickets:
            toast("먼저 휠을 생성해주세요")
            return
        for t in self.tickets:
            self.db.save_combination(t, source="휠링시스템")
        toast(f"{len(self.tickets)}장을 저장했습니다")


class HotColdSubScreen(Screen):
    def __init__(self, db, **kwargs):
        super().__init__(name="hotcold", **kwargs)
        self.db = db
        self.pinned = []
        self.excluded = []
        self.last_numbers = None

        root = MDBoxLayout(orientation="vertical", padding=dp(16), spacing=dp(8))
        root.add_widget(
            MDLabel(
                text="번호를 탭하면 고정, 한번 더 탭하면 제외로 순환합니다.",
                theme_text_color="Secondary",
                size_hint_y=None,
                height=dp(40),
            )
        )

        grid_scroll = MDScrollView(size_hint_y=None, height=dp(260))
        # 핫콜드 그리드는 고정/제외 3단계 순환이 필요해서 그리드 자체 토글은 끄고
        # cycle()을 직접 바인딩한다.
        self.grid = NumberToggleGrid(max_select=6, interactive=False)
        self._bind_cycle()
        grid_scroll.add_widget(self.grid)
        root.add_widget(grid_scroll)

        self.pin_label = MDLabel(
            text="고정: 없음 / 제외: 없음", size_hint_y=None, height=dp(24), theme_text_color="Secondary"
        )
        root.add_widget(self.pin_label)

        self.hot_slider, hot_row = self._slider_row("핫 존 가중치")
        self.warm_slider, warm_row = self._slider_row("미지근 존 가중치")
        self.cold_slider, cold_row = self._slider_row("콜드 존 가중치")
        root.add_widget(hot_row)
        root.add_widget(warm_row)
        root.add_widget(cold_row)

        gen_btn = MDButton(MDButtonText(text="가중치 반영 생성"), style="filled")
        gen_btn.bind(on_release=lambda *_: self.generate())
        root.add_widget(gen_btn)

        self.result_box = MDBoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        root.add_widget(self.result_box)

        save_btn = MDButton(MDButtonText(text="이 조합 저장"), style="tonal")
        save_btn.bind(on_release=lambda *_: self.save())
        root.add_widget(save_btn)

        self.add_widget(root)

    def _slider_row(self, label):
        row = MDBoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        row.add_widget(MDLabel(text=label, size_hint_x=0.4, theme_text_color="Secondary"))
        slider = MDSlider(min=0.2, max=3.0, value=1.0)
        slider.add_widget(MDSliderHandle())
        row.add_widget(slider)
        return slider, row

    def _bind_cycle(self):
        for n, btn in self.grid.buttons.items():
            btn.bind(on_release=lambda inst, n=n: self.cycle(n))

    def cycle(self, n):
        if n in self.pinned:
            self.pinned.remove(n)
            self.excluded.append(n)
            self._paint(n, "excluded")
        elif n in self.excluded:
            self.excluded.remove(n)
            self._paint(n, "normal")
        else:
            if len(self.pinned) >= 6:
                toast("고정 번호는 최대 6개까지 가능해요")
                return
            self.pinned.append(n)
            self._paint(n, "pinned")
        pinned_txt = ", ".join(map(str, sorted(self.pinned))) or "없음"
        excluded_txt = ", ".join(map(str, sorted(self.excluded))) or "없음"
        self.pin_label.text = f"고정: {pinned_txt} / 제외: {excluded_txt}"

    def _paint(self, n, state):
        btn = self.grid.buttons[n]
        if state == "pinned":
            btn.set_active(True)
        elif state == "excluded":
            btn._color.rgba = (0.9, 0.2, 0.2, 0.5)
        else:
            btn.set_active(False)

    def generate(self):
        numbers = generate_weighted(
            self.db,
            hot_weight=self.hot_slider.value,
            warm_weight=self.warm_slider.value,
            cold_weight=self.cold_slider.value,
            pinned=self.pinned,
            excluded=self.excluded,
        )
        self.last_numbers = numbers
        self.result_box.clear_widgets()
        for n in numbers:
            self.result_box.add_widget(LottoBall(n))

    def save(self):
        if not self.last_numbers:
            toast("먼저 번호를 생성해주세요")
            return
        self.db.save_combination(self.last_numbers, source="핫콜드가중치")
        toast("저장했습니다")


class FilterSubScreen(Screen):
    def __init__(self, db, **kwargs):
        super().__init__(name="filter", **kwargs)
        self.db = db
        self.filter_obj = PatternMaskFilter(db)
        self.last_numbers = None

        root = MDBoxLayout(orientation="vertical", padding=dp(16), spacing=dp(6))
        root.add_widget(
            MDLabel(
                text="생성된 조합이 아래 규칙을 모두 통과할 때까지 자동 재시도합니다.",
                theme_text_color="Secondary",
                size_hint_y=None,
                height=dp(40),
            )
        )

        scroll = MDScrollView(size_hint_y=None, height=dp(260))
        switch_box = MDBoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(4))
        switch_box.bind(minimum_height=switch_box.setter("height"))
        labels = self.filter_obj.rule_labels()
        self.switches = {}
        for key, label in labels.items():
            row = MDBoxLayout(size_hint_y=None, height=dp(40))
            row.add_widget(MDLabel(text=label, theme_text_color="Secondary"))
            # MDSwitch는 생성자에서 active=를 바로 넘기면 내부 ids가 아직 준비되기 전에
            # on_active가 발동해 죽는 경우가 있어, 생성 후에 값을 대입한다.
            sw = MDSwitch()
            sw.active = self.filter_obj.enabled.get(key, True)
            sw.bind(active=lambda inst, val, key=key: self.filter_obj.enabled.__setitem__(key, val))
            self.switches[key] = sw
            row.add_widget(sw)
            switch_box.add_widget(row)
        scroll.add_widget(switch_box)
        root.add_widget(scroll)

        gen_btn = MDButton(MDButtonText(text="필터 통과 조합 생성 (빈도분석 AI)"), style="filled")
        gen_btn.bind(on_release=lambda *_: self.generate())
        root.add_widget(gen_btn)

        self.result_box = MDBoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        root.add_widget(self.result_box)

        self.msg_label = autosize_label(
            MDLabel(text="", theme_text_color="Secondary", size_hint_y=None, halign="left")
        )
        root.add_widget(self.msg_label)

        save_btn = MDButton(MDButtonText(text="이 조합 저장"), style="tonal")
        save_btn.bind(on_release=lambda *_: self.save())
        root.add_widget(save_btn)

        self.add_widget(root)

    def generate(self):
        base_engine = ALL_GENERATORS[0]
        numbers, messages = generate_with_filters(
            lambda: base_engine.generate(self.db), self.filter_obj
        )
        self.result_box.clear_widgets()
        if numbers is None:
            toast("조건을 만족하는 조합을 찾지 못했어요. 규칙을 완화해보세요")
            self.last_numbers = None
        else:
            self.last_numbers = numbers
            for n in numbers:
                self.result_box.add_widget(LottoBall(n))
        self.msg_label.text = "\n".join(clean_msg(m) for m in messages[:4])

    def save(self):
        if not self.last_numbers:
            toast("먼저 조합을 생성해주세요")
            return
        self.db.save_combination(self.last_numbers, source="패턴필터")
        toast("저장했습니다")


class AdvancedScreen(MDBoxLayout):
    def __init__(self, db, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.db = db

        tab_row = MDBoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6), padding=dp(8))
        self.tabs = {}
        for name, label in (("wheel", "휠링"), ("hotcold", "핫콜드"), ("filter", "필터")):
            btn = PillTabButton(label, active=(name == "wheel"))
            btn.bind(on_release=lambda inst, name=name: self.switch(name))
            self.tabs[name] = btn
            tab_row.add_widget(btn)
        self.add_widget(tab_row)

        self.sm = ScreenManager(transition=NoTransition())
        self.sm.add_widget(WheelSubScreen(db))
        self.sm.add_widget(HotColdSubScreen(db))
        self.sm.add_widget(FilterSubScreen(db))
        self.add_widget(self.sm)

    def switch(self, name):
        self.sm.current = name
        for n, btn in self.tabs.items():
            btn.set_active(n == name)
