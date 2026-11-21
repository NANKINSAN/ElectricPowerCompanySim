"""
UI操作用コンポーネント
ボタン、スライダ、クリック判定
"""
import pyxel

class Button:
    def __init__(self, x: int, y: int, w: int, h: int, text: str, col_bg: int = 1, col_fg: int = 7, col_hover: int = 9):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.text = text
        self.col_bg = col_bg
        self.col_fg = col_fg
        self.col_hover = col_hover
        self.is_hovered = False

    def is_inside(self, mx: int, my: int) -> bool:
        return self.x <= mx <= self.x + self.w and self.y <= my <= self.y + self.h

    def update(self, mx: int, my: int):
        self.is_hovered = self.is_inside(mx, my)

    def draw(self):
        bg = self.col_hover if self.is_hovered else self.col_bg
        pyxel.rect(self.x, self.y, self.w, self.h, bg)
        pyxel.rectb(self.x, self.y, self.w, self.h, 7)
        # テキストを中央揃え
        # 1文字4px幅と仮定
        tw = len(self.text) * 4
        tx = self.x + max(2, (self.w - tw) // 2)
        ty = self.y + (self.h - 5) // 2
        pyxel.text(tx, ty, self.text, self.col_fg)
