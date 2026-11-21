"""
サウンド管理モジュール
周波数警告音、イベント通知音、操作音などの定義と再生
"""
import pyxel

class SoundManager:
    def __init__(self):
        self.muted = False
        self._init_sounds()

    def _init_sounds(self):
        # 0: 操作音（ピコッ）
        pyxel.sounds[0].set(
            notes="c3 e3",
            tones="p",
            volumes="4",
            effects="n",
            speed=4
        )
        # 1: スイッチ切替・モード変更（カチッ）
        pyxel.sounds[1].set(
            notes="g2 c3",
            tones="t",
            volumes="5",
            effects="s",
            speed=6
        )
        # 2: 周波数異常警告音（ピピピッ！）
        pyxel.sounds[2].set(
            notes="a3 a3 a3",
            tones="s",
            volumes="6",
            effects="n",
            speed=6
        )
        # 3: イベント予告音（ポーン）
        pyxel.sounds[3].set(
            notes="c3 g3 e3",
            tones="t",
            volumes="5",
            effects="f",
            speed=10
        )
        # 4: イベント発生アラート（ファンファーレ短）
        pyxel.sounds[4].set(
            notes="c3 e3 g3 c4",
            tones="t",
            volumes="6",
            effects="f",
            speed=8
        )
        # 5: ゲームオーバー（ブラックアウト・ドォォン）
        pyxel.sounds[5].set(
            notes="f2 d2 b1 g1",
            tones="n",
            volumes="7",
            effects="f",
            speed=20
        )
        # 6: 設備建設音（コインチャリン）
        pyxel.sounds[6].set(
            notes="b2 d3 g3 b3",
            tones="p",
            volumes="5",
            effects="s",
            speed=6
        )

    def play_click(self):
        if not self.muted:
            pyxel.play(0, 0)

    def play_switch(self):
        if not self.muted:
            pyxel.play(0, 1)

    def play_alarm(self):
        if not self.muted:
            # チャンネル1で警告音を鳴らす（チャンネル0の操作音と被らないように）
            pyxel.play(1, 2)

    def play_notice(self):
        if not self.muted:
            pyxel.play(2, 3)

    def play_event(self):
        if not self.muted:
            pyxel.play(2, 4)

    def play_gameover(self):
        if not self.muted:
            pyxel.play(0, 5)

    def play_build(self):
        if not self.muted:
            pyxel.play(0, 6)
