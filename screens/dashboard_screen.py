"""당첨결과·패턴 대시보드 + 실시간 동기화"""
import threading

from kivy.clock import Clock, mainthread
from kivy.metrics import dp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.label import MDLabel
from kivymd.uix.scrollview import MDScrollView

from algorithms.pattern_ai import PatternAI
from algorithms.trend import trend_ranking
from algorithms.checker import check_saved_combinations
from api.client import sync_to_latest, DhLotteryError
from screens.widgets_common import LottoBall, autosize_label
from screens.toast import toast

SYNC_INTERVAL_SEC = 30 * 60  # 30분마다 자동 확인


def numbered_row(pairs, size_dp=28):
    """[(번호, 값), ...] 리스트를 로또볼 + 값 라벨 가로 스크롤 행으로 표시"""
    scroll = MDScrollView(size_hint_y=None, height=dp(size_dp + 22), do_scroll_y=False)
    box = MDBoxLayout(size_hint_x=None, spacing=dp(10), padding=(dp(4), dp(2)))
    box.bind(minimum_width=box.setter("width"))
    for n, val in pairs:
        cell = MDBoxLayout(orientation="vertical", size_hint_x=None, width=dp(size_dp + 16))
        cell.add_widget(LottoBall(n, size_dp=size_dp))
        cell.add_widget(
            MDLabel(
                text=str(val),
                halign="center",
                theme_text_color="Secondary",
                size_hint_y=None,
                height=dp(18),
                font_size=dp(12),
            )
        )
        box.add_widget(cell)
    scroll.add_widget(box)
    return scroll


class DashboardScreen(MDBoxLayout):
    def __init__(self, db, **kwargs):
        super().__init__(orientation="vertical", padding=dp(16), spacing=dp(10), **kwargs)
        self.db = db
        self.auto_sync_enabled = False
        self._sync_event = None

        self.add_widget(
            MDLabel(text="당첨결과 · 패턴", font_style="Title", role="small", size_hint_y=None, height=dp(30))
        )

        # ---- 최신 회차 + 동기화 ----
        self.latest_label = MDLabel(
            text="", theme_text_color="Custom", text_color=(0.98, 0.75, 0.14, 1),
            size_hint_y=None, height=dp(28), bold=True,
        )
        self.add_widget(self.latest_label)

        self.latest_balls = MDBoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))
        self.add_widget(self.latest_balls)

        sync_row = MDBoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        sync_btn = MDButton(MDButtonText(text="지금 동기화"), style="filled")
        sync_btn.bind(on_release=lambda *_: self.sync_now(manual=True))
        self.auto_btn = MDButton(MDButtonText(text="자동 동기화: 꺼짐"), style="outlined")
        self.auto_btn.bind(on_release=lambda *_: self.toggle_auto_sync())
        sync_row.add_widget(sync_btn)
        sync_row.add_widget(self.auto_btn)
        self.add_widget(sync_row)

        self.sync_status = autosize_label(
            MDLabel(text="", theme_text_color="Secondary", size_hint_y=None, halign="left", font_style="Label")
        )
        self.add_widget(self.sync_status)

        # ---- 패턴 요약 (스크롤 영역) ----
        scroll = MDScrollView()
        content = MDBoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(14))
        content.bind(minimum_height=content.setter("height"))

        content.add_widget(self._section_title("핫 넘버 TOP10 (역대 최다 출현)"))
        self.hot_box = MDBoxLayout(size_hint_y=None, height=dp(50))
        content.add_widget(self.hot_box)

        content.add_widget(self._section_title("콜드 넘버 TOP10 (역대 최소 출현)"))
        self.cold_box = MDBoxLayout(size_hint_y=None, height=dp(50))
        content.add_widget(self.cold_box)

        content.add_widget(self._section_title("이월수 TOP10 (오래 안 나온 번호)"))
        self.overdue_box = MDBoxLayout(size_hint_y=None, height=dp(50))
        content.add_widget(self.overdue_box)

        content.add_widget(self._section_title("최근 20회 트렌드 TOP10 (지수감쇠 가중치)"))
        self.trend_box = MDBoxLayout(size_hint_y=None, height=dp(50))
        content.add_widget(self.trend_box)

        scroll.add_widget(content)
        self.add_widget(scroll)

        self.refresh_all()

    def _section_title(self, text):
        return MDLabel(
            text=text, font_style="Label", theme_text_color="Custom",
            text_color=(0.78, 0.29, 0.90, 1), bold=True, size_hint_y=None, height=dp(22),
        )

    def refresh_all(self):
        latest_round = self.db.get_latest_round()
        row = self.db.get_draw(latest_round)
        self.latest_label.text = f"제 {latest_round}회 당첨번호"
        self.latest_balls.clear_widgets()
        if row:
            for col in ("n1", "n2", "n3", "n4", "n5", "n6"):
                self.latest_balls.add_widget(LottoBall(row[col]))
            plus = MDLabel(text="+", size_hint_x=None, width=dp(16))
            self.latest_balls.add_widget(plus)
            bonus_ball = LottoBall(row["bonus"])
            self.latest_balls.add_widget(bonus_ball)

        summary = PatternAI().summary(self.db)
        self._fill_row(self.hot_box, summary["hot_numbers"])
        self._fill_row(self.cold_box, summary["cold_numbers"])
        self._fill_row(self.overdue_box, summary["overdue_numbers"])
        trend = trend_ranking(self.db, window=20, decay=0.9, top=10)
        self._fill_row(self.trend_box, trend)

    def _fill_row(self, container, pairs):
        container.clear_widgets()
        container.add_widget(numbered_row(pairs))

    # ---------- 동기화 ----------
    def sync_now(self, manual=False):
        self.sync_status.text = "동기화 중..."

        def worker():
            try:
                added = sync_to_latest(self.db)
                updated = check_saved_combinations(self.db)
                self._on_sync_done(added, len(updated), None)
            except DhLotteryError as e:
                self._on_sync_done(0, 0, str(e))
            except Exception as e:
                self._on_sync_done(0, 0, f"동기화 실패: {e}")

        threading.Thread(target=worker, daemon=True).start()

    @mainthread
    def _on_sync_done(self, added, updated, error):
        if error:
            self.sync_status.text = f"동기화 실패: {error}"
            if True:  # 수동/자동 모두 실패는 조용히 로그만 (자동일 때 매번 토스트는 성가심)
                pass
            return
        if added > 0:
            self.sync_status.text = f"{added}개 회차를 새로 반영했습니다 ({updated}개 조합 확인됨)"
            toast(f"새 회차 {added}개 반영!")
            self.refresh_all()
        else:
            self.sync_status.text = "이미 최신 회차입니다."

    def toggle_auto_sync(self):
        self.auto_sync_enabled = not self.auto_sync_enabled
        if self.auto_sync_enabled:
            self.auto_btn.children[0].text = "자동 동기화: 켜짐"
            self._sync_event = Clock.schedule_interval(
                lambda dt: self.sync_now(), SYNC_INTERVAL_SEC
            )
            self.sync_now()
        else:
            self.auto_btn.children[0].text = "자동 동기화: 꺼짐"
            if self._sync_event:
                self._sync_event.cancel()
                self._sync_event = None
