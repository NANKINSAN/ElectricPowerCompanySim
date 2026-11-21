"""
プロモーション用ゲーム画面キャプチャスクリプト
ゲームの主要シーン（タイトル、プレイ中潮流、変電所系統開閉盤、周波数警戒）を自動撮影してPNG保存する
"""
import os
import pyxel
from main import PowerGridApp, GameState

class ScreenCaptureApp(PowerGridApp):
    def __init__(self):
        self.shots_taken = {}
        self.frame_step = 0
        super().__init__()

    def update(self):
        self.frame_step += 1

        # 1. タイトル画面のキャプチャ (フレーム 5)
        if self.frame_step == 5 and "title" not in self.shots_taken:
            pyxel.screenshot("promo_shot_1_title.png")
            self.shots_taken["title"] = True
            print("Captured: promo_shot_1_title.png")
            # ゲーム開始 (中級)
            self.start_game("normal")
            return

        if self.state == GameState.PLAYING:
            # 時間を進める
            super().update()

            # 2. プレイ中通常運転・潮流アニメーション画面 (フレーム 50)
            if self.frame_step == 50 and "playing" not in self.shots_taken:
                pyxel.screenshot("promo_shot_2_playing.png")
                self.shots_taken["playing"] = True
                print("Captured: promo_shot_2_playing.png")

            # 3. 中央変電所選択＆系統開閉盤モーダル表示 (フレーム 80)
            if self.frame_step == 80 and "substation" not in self.shots_taken:
                self.selected_obj = self.grid.substation
                self.is_showing_substation_modal = True
                self.substation_tab = 0
                for p in self.plants:
                    p.pending_connected = p.connected
                for c in self.town_mgr.consumers:
                    c.pending_connected = c.is_connected
            
            if self.frame_step == 90 and "substation" not in self.shots_taken:
                pyxel.screenshot("promo_shot_3_substation.png")
                self.shots_taken["substation"] = True
                print("Captured: promo_shot_3_substation.png")
                self.is_showing_substation_modal = False
                self.selected_obj = None

            # 4. 需要側タブ画面 (フレーム 100)
            if self.frame_step == 100 and "consumers" not in self.shots_taken:
                self.selected_obj = self.grid.substation
                self.is_showing_substation_modal = True
                self.substation_tab = 1
            
            if self.frame_step == 110 and "consumers" not in self.shots_taken:
                pyxel.screenshot("promo_shot_4_consumers.png")
                self.shots_taken["consumers"] = True
                print("Captured: promo_shot_4_consumers.png")
                self.is_showing_substation_modal = False
                self.selected_obj = None

            # 5. 周波数アラート画面 (フレーム 130)
            if self.frame_step == 130 and "alert" not in self.shots_taken:
                # 負荷を急増させて周波数を低下させる
                self.freq_sys.freq = 59.35
                self.freq_sys.is_violating = True
                self.freq_sys.violation_ratio = 0.65
                self.freq_sys.is_critical = False

            if self.frame_step == 135 and "alert" not in self.shots_taken:
                pyxel.screenshot("promo_shot_5_alert.png")
                self.shots_taken["alert"] = True
                print("Captured: promo_shot_5_alert.png")
                pyxel.quit()

if __name__ == "__main__":
    ScreenCaptureApp()
