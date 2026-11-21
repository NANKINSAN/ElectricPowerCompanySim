"""
UI操作用コンポーネント
ボタン、スライダ、クリック判定
"""
import pyxel

class Button:
    def __init__(self, x: int, y: int, w: int, h: int, text: str, col_bg: int = 1, col_fg: int = 7, col_hover: int = 9, font=None, shortcut_key=None):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.text = text
        self.col_bg = col_bg
        self.col_fg = col_fg
        self.col_hover = col_hover
        self.font = font
        self.shortcut_key = shortcut_key  # 単一のキーまたはタプル/リスト
        self.is_hovered = False
        self.enabled = True

    def is_inside(self, mx: int, my: int) -> bool:
        return self.x <= mx <= self.x + self.w and self.y <= my <= self.y + self.h

    def update(self, mx: int, my: int):
        self.is_hovered = self.is_inside(mx, my)

    def is_pressed(self) -> bool:
        """マウスクリックまたは割り当てられたショートカットキーで発火したか"""
        if not self.enabled:
            return False
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) and self.is_hovered:
            return True
        if self.shortcut_key is not None:
            if isinstance(self.shortcut_key, (list, tuple)):
                for k in self.shortcut_key:
                    if pyxel.btnp(k):
                        return True
            else:
                if pyxel.btnp(self.shortcut_key):
                    return True
        return False

    def _calc_text_width(self) -> int:
        w = 0
        for ch in self.text:
            if ord(ch) < 128:
                w += 5 if self.font else 4
            else:
                w += 10 if self.font else 8
        return w

    def draw(self):
        if not self.enabled:
            bg = 0
            border_col = 5
            fg_col = 5
        else:
            bg = self.col_hover if self.is_hovered else self.col_bg
            border_col = 7
            fg_col = self.col_fg

        pyxel.rect(self.x, self.y, self.w, self.h, bg)
        pyxel.rectb(self.x, self.y, self.w, self.h, border_col)
        
        # テキストを中央揃え
        tw = self._calc_text_width()
        tx = self.x + max(2, (self.w - tw) // 2)
        th = 10 if self.font else 6
        ty = self.y + max(1, (self.h - th) // 2)
        
        if self.font:
            pyxel.text(tx, ty, self.text, fg_col, self.font)
        else:
            pyxel.text(tx, ty, self.text, fg_col)


class Slider:
    """出力制御用インタラクティブスライダー"""
    def __init__(self, x: int, y: int, w: int, h: int, min_val: float, max_val: float, initial_val: float, font=None):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.min_val = min_val
        self.max_val = max_val
        self.value = initial_val
        self.font = font
        self.is_dragging = False
        self.enabled = True

    def set_bounds(self, min_val: float, max_val: float):
        self.min_val = min_val
        self.max_val = max_val
        self.value = max(self.min_val, min(self.max_val, self.value))

    def set_value(self, val: float):
        self.value = max(self.min_val, min(self.max_val, val))

    def update(self, mx: int, my: int) -> bool:
        """マウス操作で値を更新。値が変化したら True を返す"""
        if not self.enabled:
            self.is_dragging = False
            return False

        changed = False

        # 左クリック押下時、スライダー領域内ならドラッグ開始
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            if self.x - 4 <= mx <= self.x + self.w + 4 and self.y - 4 <= my <= self.y + self.h + 4:
                self.is_dragging = True

        # 左クリック解放でドラッグ終了
        if pyxel.btnr(pyxel.MOUSE_BUTTON_LEFT):
            self.is_dragging = False

        if self.is_dragging and pyxel.btn(pyxel.MOUSE_BUTTON_LEFT):
            ratio = max(0.0, min(1.0, (mx - self.x) / max(1.0, self.w)))
            new_val = self.min_val + ratio * (self.max_val - self.min_val)
            new_val = round(new_val)
            if abs(new_val - self.value) >= 0.5:
                self.value = new_val
                changed = True

        return changed

    def draw(self):
        rail_y = self.y + self.h // 2 - 2
        pyxel.rect(self.x, rail_y, self.w, 5, 0)
        pyxel.rectb(self.x, rail_y, self.w, 5, 5 if self.enabled else 1)

        # 満たされているアクティブバー
        span = max(0.1, self.max_val - self.min_val)
        ratio = max(0.0, min(1.0, (self.value - self.min_val) / span))
        fill_w = int(self.w * ratio)
        fill_col = 10 if self.enabled else 5
        if fill_w > 0:
            pyxel.rect(self.x + 1, rail_y + 1, max(1, fill_w - 2), 3, fill_col)

        # つまみ（ノブ）
        knob_x = self.x + fill_w
        knob_w, knob_h = 7, self.h
        knob_top = self.y
        knob_col = (10 if self.is_dragging else 7) if self.enabled else 5
        pyxel.rect(knob_x - knob_w // 2, knob_top, knob_w, knob_h, knob_col)
        pyxel.rectb(knob_x - knob_w // 2, knob_top, knob_w, knob_h, 0)


