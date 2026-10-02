"""가벼운 토스트 팝업 (KivyMD MDSnackbar는 리플용 FBO를 써서 일부 렌더링 환경에서
불안정하므로, 순수 Kivy 위젯으로 직접 구현한 대체품)"""
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.label import Label
from kivy.graphics import Color, RoundedRectangle


class _ToastLabel(Label):
    def __init__(self, text, **kwargs):
        super().__init__(
            text=text,
            size_hint=(None, None),
            padding=(dp(16), dp(10)),
            color=(1, 1, 1, 1),
            **kwargs,
        )
        self.texture_update()
        self.size = (self.texture_size[0] + dp(32), dp(44))
        with self.canvas.before:
            Color(0.25, 0.15, 0.45, 0.95)
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *_):
        self._bg.pos = self.pos
        self._bg.size = self.size


def toast(text: str, duration: float = 1.6):
    label = _ToastLabel(text)
    label.center_x = Window.width / 2
    label.y = dp(90)
    label.opacity = 0
    Window.add_widget(label)

    anim_in = Animation(opacity=1, duration=0.15)

    def remove(*_):
        anim_out = Animation(opacity=0, duration=0.25)
        anim_out.bind(on_complete=lambda *_: Window.remove_widget(label))
        anim_out.start(label)

    anim_in.start(label)
    Clock.schedule_once(remove, duration)
