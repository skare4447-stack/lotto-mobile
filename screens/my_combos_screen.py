"""내 조합 관리 화면: 저장된 조합 조회/삭제/일괄 당첨확인"""
from kivy.metrics import dp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.label import MDLabel
from kivymd.uix.scrollview import MDScrollView

from algorithms.checker import check_saved_combinations
from screens.widgets_common import LottoBall, autosize_label
from screens.toast import toast

RESULT_COLORS = {
    "1등": (0.98, 0.75, 0.14, 1),
    "2등": (0.91, 0.55, 0.14, 1),
    "3등": (0.91, 0.30, 0.24, 1),
    "4등": (0.42, 0.69, 0.91, 1),
    "5등": (0.42, 0.42, 0.42, 1),
    "낙첨": (0.55, 0.55, 0.6, 1),
}


class ComboRow(MDBoxLayout):
    def __init__(self, combo, on_delete, **kwargs):
        super().__init__(
            orientation="vertical",
            size_hint_y=None,
            padding=dp(10),
            spacing=dp(4),
            md_bg_color=(0.16, 0.13, 0.28, 1),
            radius=[dp(10)],
            **kwargs,
        )
        self.combo_id = combo["id"]

        top_row = MDBoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))
        numbers = [combo["n1"], combo["n2"], combo["n3"], combo["n4"], combo["n5"], combo["n6"]]
        for n in numbers:
            top_row.add_widget(LottoBall(n, size_dp=32))
        top_row.add_widget(MDBoxLayout())  # spacer

        del_btn = MDButton(MDButtonText(text="삭제"), style="text", size_hint=(None, None), height=dp(36), width=dp(60))
        del_btn.bind(on_release=lambda *_: on_delete(self.combo_id))
        top_row.add_widget(del_btn)
        self.add_widget(top_row)

        source = combo["source"] or ""
        result = combo["result"]
        info = f"{source} · {combo['created_at']}"
        if result:
            info += f"  ->  {result}"
        color = RESULT_COLORS.get(result, (0.7, 0.65, 0.85, 1))
        info_label = autosize_label(
            MDLabel(
                text=info,
                theme_text_color="Custom",
                text_color=color,
                size_hint_y=None,
                halign="left",
                font_style="Label",
            )
        )
        self.add_widget(info_label)
        self.bind(minimum_height=self.setter("height"))


class MyCombosScreen(MDBoxLayout):
    def __init__(self, db, **kwargs):
        super().__init__(orientation="vertical", padding=dp(16), spacing=dp(10), **kwargs)
        self.db = db

        header = MDBoxLayout(size_hint_y=None, height=dp(30))
        header.add_widget(
            MDLabel(text="내 조합", font_style="Title", role="small", size_hint_x=1)
        )
        self.add_widget(header)

        btn_row = MDBoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        check_btn = MDButton(MDButtonText(text="일괄 당첨확인"), style="filled")
        check_btn.bind(on_release=lambda *_: self.check_all())
        delete_all_btn = MDButton(MDButtonText(text="전체 삭제"), style="outlined")
        delete_all_btn.bind(on_release=lambda *_: self.delete_all())
        btn_row.add_widget(check_btn)
        btn_row.add_widget(delete_all_btn)
        self.add_widget(btn_row)

        self.status_label = MDLabel(
            text="", theme_text_color="Secondary", size_hint_y=None, height=dp(24)
        )
        self.add_widget(self.status_label)

        scroll = MDScrollView()
        self.list_box = MDBoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(8))
        self.list_box.bind(minimum_height=self.list_box.setter("height"))
        scroll.add_widget(self.list_box)
        self.add_widget(scroll)

        self.refresh()

    def refresh(self):
        self.list_box.clear_widgets()
        combos = self.db.get_saved_combinations()
        self.status_label.text = f"총 {len(combos)}개 저장됨"
        for combo in combos:
            self.list_box.add_widget(ComboRow(combo, on_delete=self.delete_one))

    def delete_one(self, combo_id):
        self.db.delete_combination(combo_id)
        toast("삭제했습니다")
        self.refresh()

    def delete_all(self):
        self.db.delete_all_combinations()
        toast("전체 삭제했습니다")
        self.refresh()

    def check_all(self):
        updated = check_saved_combinations(self.db)
        if updated:
            toast(f"{len(updated)}개 조합을 확인했습니다")
        else:
            toast("새로 확인할 조합이 없습니다 (이미 최신 회차로 확인됨)")
        self.refresh()
