"""여러 화면에서 공용으로 쓰는 위젯 (1~45 번호 선택 그리드, 로또볼 등)

주의: 45개씩 반복 생성되는 번호 그리드는 KivyMD의 MDButton(리플 효과용 FBO 사용)을
쓰면 한 번에 너무 많은 프레임버퍼가 생성되어 일부 환경(특히 소프트웨어 렌더링)에서
"FBO Initialization failed"로 죽거나, 저사양 폰에서 렌더링이 느려질 수 있다.
그래서 순수 Kivy 위젯(캔버스 직접 그리기)으로 가벼운 토글 버튼을 직접 구현한다.
"""
from kivy.metrics import dp
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.behaviors import ButtonBehavior
from kivy.graphics import Color, Ellipse, RoundedRectangle

BALL_COLOR_BANDS = [
    (1, 10, (0.98, 0.75, 0.14, 1)),   # 노랑
    (11, 20, (0.29, 0.56, 0.89, 1)),  # 파랑
    (21, 30, (0.91, 0.30, 0.24, 1)),  # 빨강
    (31, 40, (0.42, 0.42, 0.42, 1)),  # 회색
    (41, 45, (0.30, 0.69, 0.31, 1)),  # 초록
]


def ball_color(n: int):
    for lo, hi, color in BALL_COLOR_BANDS:
        if lo <= n <= hi:
            return color
    return (0.5, 0.5, 0.5, 1)


class LottoBall(BoxLayout):
    """숫자가 적힌 동그란 로또볼 (읽기 전용 표시용)"""

    def __init__(self, number: int, size_dp: int = 34, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (dp(size_dp), dp(size_dp))
        color = ball_color(number)
        with self.canvas.before:
            Color(*color)
            self._ellipse = Ellipse(pos=self.pos, size=self.size)
        self.bind(pos=self._update, size=self._update)
        self.add_widget(
            Label(
                text=str(number),
                bold=True,
                color=(1, 1, 1, 1),
                font_size=dp(size_dp * 0.4),
            )
        )

    def _update(self, *_):
        self._ellipse.pos = self.pos
        self._ellipse.size = self.size


INACTIVE_BALL = (1, 1, 1, 0.08)


class NumberButton(ButtonBehavior, BoxLayout):
    """캔버스로 직접 그리는 가벼운 원형 토글 버튼 (MDButton의 리플/FBO 비용 없음)"""

    def __init__(self, number: int, size_dp: int = 38, **kwargs):
        super().__init__(**kwargs)
        self.number = number
        self.active = False
        self.size_hint = (None, None)
        self.size = (dp(size_dp), dp(size_dp))
        with self.canvas.before:
            self._color = Color(*INACTIVE_BALL)
            self._ellipse = Ellipse(pos=self.pos, size=self.size)
        self.bind(pos=self._redraw, size=self._redraw)
        self.label = Label(text=str(number), bold=True, font_size=dp(size_dp * 0.38))
        self.add_widget(self.label)

    def _redraw(self, *_):
        self._ellipse.pos = self.pos
        self._ellipse.size = self.size

    def set_active(self, active: bool):
        self.active = active
        self._color.rgba = ball_color(self.number) if active else INACTIVE_BALL


def autosize_label(label):
    """MDLabel/Label이 긴 텍스트에서 위젯 높이를 넘어 그려지는(다른 위젯과 겹치는)
    문제를 막기 위해, 폭에 맞춰 줄바꿈하고 실제 텍스처 높이에 맞춰
    위젯 높이를 자동으로 늘려준다. size_hint_y=None인 라벨에 사용."""
    label.bind(
        width=lambda inst, w: setattr(inst, "text_size", (w, None)),
        texture_size=lambda inst, ts: setattr(inst, "height", ts[1]),
    )
    return label


PILL_ACTIVE = (0.78, 0.29, 0.90, 1)
PILL_INACTIVE = (1, 1, 1, 0.08)


class PillTabButton(ButtonBehavior, BoxLayout):
    """상단 모드 전환용 알약 모양 토글 버튼.
    (MDButton은 style 속성을 런타임에 바꿀 때 내부 MDButtonText 색상이
    갱신되지 않아 글자가 안 보이는 경우가 있어, 직접 그리는 방식으로 대체)"""

    def __init__(self, text: str, active: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.padding = (dp(4), dp(4))
        with self.canvas.before:
            self._color = Color(*(PILL_ACTIVE if active else PILL_INACTIVE))
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(20)])
        self.bind(pos=self._redraw, size=self._redraw)
        self.label = Label(text=text, bold=active, color=(1, 1, 1, 1))
        self.add_widget(self.label)

    def _redraw(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size

    def set_active(self, active: bool):
        self._color.rgba = PILL_ACTIVE if active else PILL_INACTIVE
        self.label.bold = active


class NumberToggleGrid(GridLayout):
    """1~45 토글 버튼 그리드. 선택 상태를 self.selected(list)에 유지."""

    def __init__(self, max_select: int = 6, on_change=None, interactive: bool = True, **kwargs):
        super().__init__(cols=9, spacing=dp(4), padding=dp(4), size_hint_y=None, **kwargs)
        self.bind(minimum_height=self.setter("height"))
        self.max_select = max_select
        self.on_change = on_change
        self.selected: list[int] = []
        self.buttons = {}
        # interactive=False: 그리드는 버튼만 만들고 클릭 동작은 만들지 않는다.
        # (예: 핫콜드 화면처럼 고정/제외 3단계 순환 등 자체 클릭 로직이 필요한 경우)
        self.interactive = interactive
        self._build()

    def _build(self):
        for n in range(1, 46):
            btn = NumberButton(n)
            if self.interactive:
                btn.bind(on_release=lambda inst, n=n: self._toggle(n))
            self.buttons[n] = btn
            self.add_widget(btn)

    def _toggle(self, n):
        if n in self.selected:
            self.selected.remove(n)
            self.buttons[n].set_active(False)
        else:
            if len(self.selected) >= self.max_select:
                return
            self.selected.append(n)
            self.buttons[n].set_active(True)
        if self.on_change:
            self.on_change(self.selected)

    def clear(self):
        for n in list(self.selected):
            self._toggle(n)

    def set_pinned(self, numbers: list[int]):
        self.clear()
        for n in numbers:
            self._toggle(n)
