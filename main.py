"""
電力運用シミュレータ (Electric Power Company Simulator)
Pyxel 2D レトロゲーム
"""
import pyxel
import json
import os

from sim.frequency import FrequencySystem
from sim.power_plants import ThermalPlant, AdvancedThermalPlant, HydroPlant, PumpedStoragePlant
from sim.consumers import TownManager
from sim.grid import GridNetwork
from sim.economy import EconomySystem
from sim.event_manager import EventManager
from ui.sound import SoundManager
from ui.renderer import GameRenderer
from ui.controls import Button, Slider
from utils.resource import get_config_path, get_resource_path
from sim.story_stages import STORY_STAGES, get_stage, check_stage_clear

class GameState:
    TITLE = 0
    PLAYING = 1
    GAMEOVER = 2
    STAGE_BRIEFING = 3
    STAGE_CLEAR = 4

class PowerGridApp:
    def __init__(self):
        # 1. 設定ファイル読み込み
        self.config = self._load_config("config.json")
        fps = self.config.get("general", {}).get("fps", 30)
        screen_w = self.config.get("general", {}).get("screen_width", 480)
        screen_h = self.config.get("general", {}).get("screen_height", 360)
        
        # 2. Pyxel 初期化 (480x360, 30fps, quit_key無効化でESCによる強制終了を防止)
        pyxel.init(screen_w, screen_h, title="電力運用シミュレータ - Power Grid Sim", fps=fps, quit_key=pyxel.KEY_NONE)
        pyxel.mouse(True)

        # 3. サウンド・レンダラー初期化
        self.sound = SoundManager()
        self.renderer = GameRenderer()

        # 4. ゲーム状態・難易度・ストーリーモード管理
        self.state = GameState.TITLE
        self.difficulty_key = "normal"
        self.is_story_mode = False
        self.current_stage_idx = 0
        self.story_goal_text = ""
        self.selected_obj = None
        self.hovered_obj = None
        self.is_manual_paused = False

        # メッセージ履歴（ログ）管理
        self.message_logs = []
        self.is_showing_log = False
        self.log_scroll_y = 0

        # 変電所開閉盤モーダル管理
        self.is_showing_substation_modal = False
        self.substation_tab = 0  # 0: 供給側(発電所), 1: 需要側(町・工場)
        self.substation_scroll_y = 0

        # 発電設備新設モーダルダイアログ管理
        self.is_showing_build_modal = False

        # 5. UI ボタン・スライダー生成
        self.buttons = {}
        self.slider = None
        self._init_buttons()

        # 6. アラーム音・建設メッセージ管理
        self.alarm_sound_timer = 0.0
        self.construction_msg = ""
        self.construction_msg_timer = 0.0

        pyxel.run(self.update, self.draw)

    def add_message_log(self, time_sec: float, category: str, text: str, color: int = 7):
        """通報・指令・イベントメッセージを履歴ログに記録"""
        if not text:
            return
        # 直前と全く同一のテキストの重複追加を防止
        if self.message_logs and self.message_logs[-1]["text"] == text:
            return
        m = int(time_sec) // 60
        s = int(time_sec) % 60
        time_str = f"{m:02d}:{s:02d}"
        self.message_logs.append({
            "time_str": time_str,
            "time_sec": time_sec,
            "category": category,
            "text": text,
            "color": color
        })

    def _load_config(self, filename: str) -> dict:
        path = get_config_path(filename)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _init_buttons(self):
        panel_y = 268
        f = self.renderer.font

        # 閉じる（選択解除）ボタン
        self.buttons["btn_close"] = Button(252, panel_y + 4, 55, 14, "閉じる (右)", 1, 7, 8, font=f)

        # 指令送信確定ボタン (Enter)
        self.buttons["btn_commit"] = Button(228, panel_y + 32, 79, 22, "指令送信 (Enter)", 3, 7, 11, font=f, shortcut_key=(pyxel.KEY_RETURN, pyxel.KEY_KP_ENTER))

        # 出力制御スライダー (火力・改良火力発電所用)
        self.slider = Slider(8, panel_y + 34, 96, 10, min_val=10.0, max_val=80.0, initial_val=45.0, font=f)

        # 改良火力用 ガバナフリー（GF）運転切替ボタン (G)
        self.buttons["btn_gf_toggle"] = Button(150, panel_y + 32, 74, 22, "GF運転: ON (G)", 3, 7, 10, font=f, shortcut_key=pyxel.KEY_G)

        # 火力・改良火力用操作ボタン (panel_y + 60) - 左手操作キー (Q, S, W, E, A, D)
        self.buttons["btn_dec10"] = Button(8, panel_y + 60, 42, 16, "-10 (Q)", 1, 7, 9, font=f, shortcut_key=pyxel.KEY_Q)
        self.buttons["btn_dec1"]  = Button(53, panel_y + 60, 38, 16, "-1 (S)", 1, 7, 9, font=f, shortcut_key=pyxel.KEY_S)
        self.buttons["btn_inc1"]  = Button(94, panel_y + 60, 38, 16, "+1 (W)", 1, 7, 9, font=f, shortcut_key=pyxel.KEY_W)
        self.buttons["btn_inc10"] = Button(135, panel_y + 60, 42, 16, "+10 (E)", 1, 7, 9, font=f, shortcut_key=pyxel.KEY_E)
        self.buttons["btn_min"]   = Button(180, panel_y + 60, 44, 16, "MIN (A)", 1, 7, 9, font=f, shortcut_key=pyxel.KEY_A)
        self.buttons["btn_max"]   = Button(227, panel_y + 60, 44, 16, "MAX (D)", 1, 7, 9, font=f, shortcut_key=pyxel.KEY_D)

        # 揚水用操作ボタン (panel_y + 38) - 左手操作キー 停止(A), 発電(W), 揚水(S)
        self.buttons["btn_pump_off"]  = Button(8, panel_y + 38, 62, 18, "停止 (A)", 1, 7, 9, font=f, shortcut_key=pyxel.KEY_A)
        self.buttons["btn_pump_gen"]  = Button(74, panel_y + 38, 66, 18, "発電 (W)", 1, 7, 10, font=f, shortcut_key=pyxel.KEY_W)
        self.buttons["btn_pump_pump"] = Button(144, panel_y + 38, 66, 18, "揚水 (S)", 1, 7, 12, font=f, shortcut_key=(pyxel.KEY_S, pyxel.KEY_D))

        # 変電所用送受電切替ボタン (panel_y + 38) - 左手操作キー 送受電切替(Space / F)
        self.buttons["btn_toggle_power"] = Button(8, panel_y + 38, 130, 18, "送受電停止 (Space)", 1, 7, 9, font=f, shortcut_key=(pyxel.KEY_SPACE, pyxel.KEY_F))

        # 設備新設ダイアログを開くボタン (右側エリア: x=320, panel_y+24) - ショートカットキー B
        self.buttons["btn_open_build"] = Button(320, panel_y + 24, 145, 24, "＋発電所新設 (B)", 3, 7, 11, font=f, shortcut_key=pyxel.KEY_B)

        # タイトル画面用 難易度選択ボタン
        self.buttons["title_easy"]   = Button(150, 140, 180, 20, "初級 (ストーリー全5話) (1)", 1, 7, 11, font=f, shortcut_key=pyxel.KEY_1)
        self.buttons["title_normal"] = Button(150, 166, 180, 20, "中級 (フリーモード) (2)", 1, 7, 10, font=f, shortcut_key=pyxel.KEY_2)
        self.buttons["title_hard"]   = Button(150, 192, 180, 20, "上級 (フリーモード) (3)", 1, 7, 8, font=f, shortcut_key=pyxel.KEY_3)

    def _update_buy_buttons_text(self):
        pass

    def _get_plant_position(self, plant_type: str, index: int) -> tuple[int, int]:
        """
        発電所オブジェクトが重ならないように整然と配置する
        列: x = 20, 75, 130 (横に3基)
        行: 火力 y=54, 改良火力 y=104, 水力 y=154, 揚水 y=204
        """
        col = index % 3
        row = index // 3
        x = 20 + col * 55
        if plant_type == "thermal":
            y = 54 + row * 32
        elif plant_type == "advanced_thermal":
            y = 104 + row * 32
        elif plant_type == "hydro":
            y = 154 + row * 32
        elif plant_type == "pumped_storage":
            y = 204 + row * 32
        else:
            y = 54 + row * 32
        return (x, y)

    def start_game(self, diff_key: str):
        self.is_story_mode = False
        self.difficulty_key = diff_key
        diff_info = self.config.get("difficulties", {}).get(diff_key, {})
        rated_f = self.config.get("general", {}).get("rated_frequency_hz", 60.0)
        base_price = self.config.get("general", {}).get("base_electricity_price", 30.0)
        init_money = self.config.get("general", {}).get("initial_money", 10000000) + diff_info.get("initial_money_bonus", 0)
        expand_interval = self.config.get("general", {}).get("town_expansion_interval_sec", 45)
        cooldown_sec = diff_info.get("command_cooldown_sec", 1.5)

        # 周波数システム
        tol = diff_info.get("freq_tolerance_hz", 0.5)
        max_dur = diff_info.get("max_violation_duration_sec", 5.0)
        self.freq_sys = FrequencySystem(rated_freq=rated_f, tolerance=tol, max_violation_sec=max_dur)

        # 経済システム
        self.economy = EconomySystem(base_price=base_price, initial_money=init_money)

        # イベントマネージャー
        self.event_mgr = EventManager("scenario.json")

        # 難易度に応じた新設ボタンのテキスト更新
        self._update_buy_buttons_text()

        # 発電所初期構成（重ならない位置に配置、初期は即稼働、操作クールダウン時間を設定）
        p_configs = self.config.get("plant_types", {})
        pos_t1 = self._get_plant_position("thermal", 0)
        pos_h1 = self._get_plant_position("hydro", 0)
        pos_p1 = self._get_plant_position("pumped_storage", 0)

        self.plants = [
            ThermalPlant("thermal_1", "中央火力1号", pos_t1[0], pos_t1[1], p_configs.get("thermal", {}), construction_time_sec=0.0, command_cooldown_sec=cooldown_sec),
            HydroPlant("hydro_1", "上流第1水力", pos_h1[0], pos_h1[1], p_configs.get("hydro", {}), construction_time_sec=0.0, command_cooldown_sec=cooldown_sec),
            PumpedStoragePlant("pumped_1", "黒岳揚水所", pos_p1[0], pos_p1[1], p_configs.get("pumped_storage", {}), construction_time_sec=0.0, command_cooldown_sec=cooldown_sec)
        ]

        # 需要家・町発展
        self.town_mgr = TownManager(expansion_interval=expand_interval)
        for c in self.town_mgr.consumers:
            c.command_cooldown_sec = cooldown_sec

        # 送電網
        self.grid = GridNetwork(command_cooldown_sec=cooldown_sec)
        self.grid.build_network(self.plants, self.town_mgr.consumers)

        self.selected_obj = None
        self.is_manual_paused = False
        self.state = GameState.PLAYING
        self.alarm_sound_timer = 0.0
        self.construction_msg = ""
        self.construction_msg_timer = 0.0

        # メッセージ履歴の初期化
        self.message_logs.clear()
        self.is_showing_log = False
        self.log_scroll_y = 0
        self.is_showing_substation_modal = False
        self.substation_tab = 0
        self.substation_scroll_y = 0
        diff_name = diff_info.get("name", "通常")
        self.add_message_log(0.0, "SYSTEM", f"【系統運用開始】難易度: {diff_name} にて電力運用シミュレーションを開始しました。", 11)

    def start_story_stage(self, stage_idx: int):
        """初級ストーリーモードの特定ステージを開始"""
        self.is_story_mode = True
        self.current_stage_idx = stage_idx
        stage_data = STORY_STAGES[stage_idx]

        # 初級(easy)難易度設定を適用
        self.difficulty_key = "easy"
        diff_info = self.config.get("difficulties", {}).get("easy", {})
        rated_f = self.config.get("general", {}).get("rated_frequency_hz", 60.0)
        base_price = self.config.get("general", {}).get("base_electricity_price", 30.0)
        init_money = stage_data.get("initial_money", 15000000)
        expand_interval = self.config.get("general", {}).get("town_expansion_interval_sec", 45)
        cooldown_sec = diff_info.get("command_cooldown_sec", 0.5)

        # 周波数システム
        tol = diff_info.get("freq_tolerance_hz", 0.8)
        max_dur = diff_info.get("max_violation_duration_sec", 8.0)
        self.freq_sys = FrequencySystem(rated_freq=rated_f, tolerance=tol, max_violation_sec=max_dur)

        # 経済システム
        self.economy = EconomySystem(base_price=base_price, initial_money=init_money)

        # イベントマネージャーにステージ専用イベントを設定
        self.event_mgr = EventManager("scenario.json")
        self.event_mgr.load_custom_events(stage_data["events"], loop=True)

        # 難易度に応じた新設ボタンのテキスト更新
        self._update_buy_buttons_text()

        # 発電所初期構成
        p_configs = self.config.get("plant_types", {})
        pos_t1 = self._get_plant_position("thermal", 0)
        pos_h1 = self._get_plant_position("hydro", 0)
        pos_p1 = self._get_plant_position("pumped_storage", 0)

        self.plants = [
            ThermalPlant("thermal_1", "中央火力1号", pos_t1[0], pos_t1[1], p_configs.get("thermal", {}), construction_time_sec=0.0, command_cooldown_sec=cooldown_sec),
            HydroPlant("hydro_1", "上流第1水力", pos_h1[0], pos_h1[1], p_configs.get("hydro", {}), construction_time_sec=0.0, command_cooldown_sec=cooldown_sec),
            PumpedStoragePlant("pumped_1", "黒岳揚水所", pos_p1[0], pos_p1[1], p_configs.get("pumped_storage", {}), construction_time_sec=0.0, command_cooldown_sec=cooldown_sec)
        ]

        # 需要家・町発展
        self.town_mgr = TownManager(expansion_interval=expand_interval)
        for c in self.town_mgr.consumers:
            c.command_cooldown_sec = cooldown_sec

        # 送電網
        self.grid = GridNetwork(command_cooldown_sec=cooldown_sec)
        self.grid.build_network(self.plants, self.town_mgr.consumers)

        self.selected_obj = None
        self.is_manual_paused = False
        self.state = GameState.PLAYING
        self.alarm_sound_timer = 0.0
        self.construction_msg = ""
        self.construction_msg_timer = 0.0

        # メッセージ履歴の初期化
        self.message_logs.clear()
        self.is_showing_log = False
        self.log_scroll_y = 0
        self.is_showing_substation_modal = False
        self.substation_tab = 0
        self.substation_scroll_y = 0

        self.story_goal_text = stage_data["condition_desc"]
        self.add_message_log(0.0, "STORY", f"【開始】{stage_data['title']}：{stage_data['subtitle']}", 10)
        self.add_message_log(0.0, "GOAL", f"【目標】クリア条件: {stage_data['condition_desc']}", 11)

    def update(self):
        mx, my = pyxel.mouse_x, pyxel.mouse_y

        if self.state == GameState.TITLE:
            self._update_title(mx, my)
        elif self.state == GameState.STAGE_BRIEFING:
            self._update_stage_briefing(mx, my)
        elif self.state == GameState.PLAYING:
            self._update_playing(mx, my)
        elif self.state == GameState.STAGE_CLEAR:
            self._update_stage_clear(mx, my)
        elif self.state == GameState.GAMEOVER:
            self._update_gameover(mx, my)

    def _update_title(self, mx: int, my: int):
        for k in ["title_easy", "title_normal", "title_hard"]:
            btn = self.buttons[k]
            btn.update(mx, my)
            if btn.is_pressed():
                diff = k.replace("title_", "")
                self.sound.play_click()
                if diff == "easy":
                    # 初級はストーリーモード画面へ遷移
                    self.is_story_mode = True
                    self.current_stage_idx = 0
                    self.state = GameState.STAGE_BRIEFING
                else:
                    self.start_game(diff)
                return

    def _update_stage_briefing(self, mx: int, my: int):
        """ステージ開始前画面の操作"""
        # ESCでタイトル画面に戻る
        if pyxel.btnp(pyxel.KEY_ESCAPE):
            self.sound.play_click()
            self.state = GameState.TITLE
            return

        # 左右キーまたはA/Dでステージ切り替え
        if pyxel.btnp(pyxel.KEY_LEFT) or pyxel.btnp(pyxel.KEY_A):
            if self.current_stage_idx > 0:
                self.current_stage_idx -= 1
                self.sound.play_switch()
            return
        if pyxel.btnp(pyxel.KEY_RIGHT) or pyxel.btnp(pyxel.KEY_D):
            if self.current_stage_idx < len(STORY_STAGES) - 1:
                self.current_stage_idx += 1
                self.sound.play_switch()
            return

        # Enter または Space でステージ開始
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_KP_ENTER) or pyxel.btnp(pyxel.KEY_SPACE):
            self.sound.play_click()
            self.start_story_stage(self.current_stage_idx)
            return

        # マウスクリック判定 (y: 248〜276)
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            # [ < 前話 (Left) ]
            if 30 <= mx <= 125 and 248 <= my <= 276:
                if self.current_stage_idx > 0:
                    self.current_stage_idx -= 1
                    self.sound.play_switch()
                return

            # [ 運用開始 (Enter / Space) ]
            if 137 <= mx <= 343 and 248 <= my <= 276:
                self.sound.play_click()
                self.start_story_stage(self.current_stage_idx)
                return

            # [ 次話 > (Right) ]
            if 355 <= mx <= 450 and 248 <= my <= 276:
                if self.current_stage_idx < len(STORY_STAGES) - 1:
                    self.current_stage_idx += 1
                    self.sound.play_switch()
                return

    def _update_stage_clear(self, mx: int, my: int):
        """ステージクリア画面の操作"""
        if pyxel.btnp(pyxel.KEY_ESCAPE):
            self.sound.play_click()
            self.state = GameState.TITLE
            return

        is_all_clear = (self.current_stage_idx + 1 >= len(STORY_STAGES))

        # Enter / Space / クリックで次へ
        proceed = (pyxel.btnp(pyxel.KEY_RETURN) or 
                   pyxel.btnp(pyxel.KEY_KP_ENTER) or 
                   pyxel.btnp(pyxel.KEY_SPACE))

        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            # ボタン領域: gx=55, gw=370, btn_w=230, btn_x=125, btn_y=284, btn_h=24
            if 125 <= mx <= 355 and 284 <= my <= 308:
                proceed = True

        if proceed:
            self.sound.play_click()
            if is_all_clear:
                self.state = GameState.TITLE
            else:
                self.current_stage_idx += 1
                self.state = GameState.STAGE_BRIEFING

    def _update_message_log_modal(self, mx: int, my: int) -> bool:
        """メッセージログ表示中の入力処理。ログ表示中ならTrueを返す"""
        if not self.is_showing_log:
            return False

        # マウスホイールまたは上下キーでスクロール
        self.log_scroll_y -= int(pyxel.mouse_wheel * 24)
        if pyxel.btn(pyxel.KEY_UP) or pyxel.btn(pyxel.KEY_W):
            self.log_scroll_y -= 8
        if pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(pyxel.KEY_S):
            self.log_scroll_y += 8
        self.log_scroll_y = max(0, self.log_scroll_y)

        # 閉じる操作 ([閉じる X] ボタン、右クリック、ESCキー、Lキー、枠外クリック)
        close_clicked = False
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            # 閉じるボタン領域 (x: 385〜445, y: 23〜37)
            if 385 <= mx <= 445 and 23 <= my <= 37:
                close_clicked = True
            # ウィンドウ枠外クリック
            elif not (30 <= mx <= 450 and 20 <= my <= 340):
                close_clicked = True
        elif pyxel.btnp(pyxel.MOUSE_BUTTON_RIGHT) or pyxel.btnp(pyxel.KEY_ESCAPE) or pyxel.btnp(pyxel.KEY_L):
            close_clicked = True

        if close_clicked:
            self.is_showing_log = False
            self.sound.play_click()
        return True

    def _update_substation_modal(self, mx: int, my: int) -> bool:
        """変電所開閉盤モーダル表示中の入力処理"""
        if not self.is_showing_substation_modal:
            return False

        wx, wy, ww, wh = 25, 15, 430, 330
        tab_y = wy + 23
        list_x = wx + 8
        list_y = wy + 42
        list_w = ww - 16
        list_h = 222
        items = self.plants if self.substation_tab == 0 else self.town_mgr.consumers
        item_h = 36
        foot_y = wy + wh - 62
        commit_x, commit_y, commit_w, commit_h = wx + 12, foot_y + 24, 230, 24
        cancel_x, cancel_y, can_w, can_h = wx + ww - 160 - 12, foot_y + 24, 160, 24

        # 1. スクロール処理 (ホイール / 上下キー)
        wheel = pyxel.mouse_wheel
        if wheel != 0:
            self.substation_scroll_y -= int(wheel * 24)
        if pyxel.btn(pyxel.KEY_UP) or pyxel.btn(pyxel.KEY_W):
            self.substation_scroll_y -= 8
        if pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(pyxel.KEY_S):
            self.substation_scroll_y += 8
        max_scroll = max(0, len(items) * item_h - list_h)
        self.substation_scroll_y = max(0, min(max_scroll, self.substation_scroll_y))

        # 2. タブ切り替え (キー入力)
        if pyxel.btnp(pyxel.KEY_TAB) or pyxel.btnp(pyxel.KEY_Q) or pyxel.btnp(pyxel.KEY_E):
            self.substation_tab = 1 - self.substation_tab
            self.substation_scroll_y = 0
            self.sound.play_click()
            return True
        if pyxel.btnp(pyxel.KEY_1):
            if self.substation_tab != 0:
                self.substation_tab = 0
                self.substation_scroll_y = 0
                self.sound.play_click()
            return True
        if pyxel.btnp(pyxel.KEY_2):
            if self.substation_tab != 1:
                self.substation_tab = 1
                self.substation_scroll_y = 0
                self.sound.play_click()
            return True

        # 3. マウスクリック判定
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            # 閉じるボタン判定
            if (wx + ww - 65 <= mx <= wx + ww - 5) and (wy + 3 <= my <= wy + 17):
                self.is_showing_substation_modal = False
                self.sound.play_click()
                return True

            # 枠外クリックで閉じる
            if not (wx <= mx <= wx + ww and wy <= my <= wy + wh):
                self.is_showing_substation_modal = False
                self.sound.play_click()
                return True

            # タブ0クリック (供給側)
            if (wx + 8 <= mx <= wx + 138) and (tab_y <= my <= tab_y + 16):
                if self.substation_tab != 0:
                    self.substation_tab = 0
                    self.substation_scroll_y = 0
                    self.sound.play_click()
                return True

            # タブ1クリック (需要側)
            if (wx + 142 <= mx <= wx + 272) and (tab_y <= my <= tab_y + 16):
                if self.substation_tab != 1:
                    self.substation_tab = 1
                    self.substation_scroll_y = 0
                    self.sound.play_click()
                return True

            # 全接続ボタン
            if (wx + ww - 98 <= mx <= wx + ww - 54) and (tab_y <= my <= tab_y + 16):
                for obj in items:
                    if not getattr(obj, "is_under_construction", False):
                        obj.pending_connected = True
                self.sound.play_click()
                return True

            # 全切断ボタン
            if (wx + ww - 50 <= mx <= wx + ww - 6 and tab_y <= my <= tab_y + 16):
                for obj in items:
                    if not getattr(obj, "is_under_construction", False):
                        obj.pending_connected = False
                self.sound.play_click()
                return True

            # リスト内アイテムの切替トグルボタン判定
            if list_x <= mx <= list_x + list_w and list_y <= my <= list_y + list_h:
                curr_y = list_y + 3 - self.substation_scroll_y
                for obj in items:
                    if curr_y + item_h > list_y and curr_y < list_y + list_h:
                        btn_w = 70
                        btn_h = 20
                        btn_bx = list_x + list_w - 98
                        btn_by = curr_y + 6
                        if (btn_bx <= mx <= btn_bx + btn_w) and (btn_by <= my <= btn_by + btn_h):
                            if not getattr(obj, "is_under_construction", False):
                                obj.toggle_pending_connection()
                                self.sound.play_click()
                            return True
                    curr_y += item_h

            # キャンセルボタン
            if (cancel_x <= mx <= cancel_x + can_w) and (cancel_y <= my <= cancel_y + can_h):
                self.is_showing_substation_modal = False
                self.sound.play_click()
                return True

            # 確定指令送信ボタン
            if (commit_x <= mx <= commit_x + commit_w) and (commit_y <= my <= commit_y + commit_h):
                self._commit_substation_changes()
                return True

        # Enterキーで確定送信
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_KP_ENTER):
            self._commit_substation_changes()
            return True

        # 右クリックまたはESCでキャンセル閉じる
        if pyxel.btnp(pyxel.MOUSE_BUTTON_RIGHT) or pyxel.btnp(pyxel.KEY_ESCAPE):
            self.is_showing_substation_modal = False
            self.sound.play_click()
            return True

        return True

    def _commit_substation_changes(self):
        """系統開閉盤の接続・切断設定を一括確定"""
        sub = self.grid.substation
        if not sub.can_operate():
            return

        conn_changes = 0
        disc_changes = 0

        # 発電所の確定
        for p in self.plants:
            if hasattr(p, "commit_connection"):
                if not getattr(p, "is_under_construction", False):
                    old_c = p.connected
                    p.commit_connection()
                    if old_c != p.connected:
                        if p.connected:
                            conn_changes += 1
                        else:
                            disc_changes += 1

        # 需要家の確定
        for c in self.town_mgr.consumers:
            if hasattr(c, "commit_connection"):
                old_c = c.is_connected
                c.commit_connection()
                if old_c != c.is_connected:
                    if c.is_connected:
                        conn_changes += 1
                    else:
                        disc_changes += 1

        sub.trigger_cooldown()
        self.sound.play_switch()
        self.is_showing_substation_modal = False
        self.selected_obj = None
        self.is_manual_paused = False

        if conn_changes > 0 or disc_changes > 0:
            msg = f"【開閉盤操作】受給開閉器を操作（系統接続: {conn_changes}件, 系統遮断: {disc_changes}件）"
            self.add_message_log(self.event_mgr.elapsed_time, "SUBSTATION", msg, 10)

    def _update_plant_build_modal(self, mx: int, my: int) -> bool:
        """発電設備新設モーダルダイアログ表示中の入力処理"""
        if not self.is_showing_build_modal:
            return False

        wx, wy, ww, wh = 20, 14, 440, 332
        close_clicked = False

        # 閉じる判定 (右クリック, ESC, B, [閉じる X] ボタン, 枠外クリック)
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            if (wx + ww - 65 <= mx <= wx + ww - 5) and (wy + 4 <= my <= wy + 18):
                close_clicked = True
            elif not (wx <= mx <= wx + ww and wy <= my <= wy + wh):
                close_clicked = True
        elif pyxel.btnp(pyxel.MOUSE_BUTTON_RIGHT) or pyxel.btnp(pyxel.KEY_ESCAPE) or pyxel.btnp(pyxel.KEY_B):
            close_clicked = True

        if close_clicked:
            self.is_showing_build_modal = False
            self.sound.play_click()
            return True

        order = ["thermal", "advanced_thermal", "hydro", "pumped_storage"]

        # 数字キー 1〜4 での直接着工
        key_map = {
            pyxel.KEY_1: "thermal",
            pyxel.KEY_KP_1: "thermal",
            pyxel.KEY_2: "advanced_thermal",
            pyxel.KEY_KP_2: "advanced_thermal",
            pyxel.KEY_3: "hydro",
            pyxel.KEY_KP_3: "hydro",
            pyxel.KEY_4: "pumped_storage",
            pyxel.KEY_KP_4: "pumped_storage",
        }
        for k, p_type in key_map.items():
            if pyxel.btnp(k):
                if self._build_plant(p_type):
                    self.is_showing_build_modal = False
                return True

        # マウスクリックでの建設着工ボタン判定
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            card_x = wx + 8
            card_w = ww - 16
            for idx, p_type in enumerate(order):
                cy = wy + 25 + idx * 70
                bx = card_x + card_w - 96
                by = cy + 14
                bw, bh = 90, 38
                if (bx <= mx <= bx + bw) and (by <= my <= by + bh):
                    if self._build_plant(p_type):
                        self.is_showing_build_modal = False
                    return True

        return True

    def _build_plant(self, plant_type: str) -> bool:
        """発電設備を新設・着工する共通処理"""
        diff_info = self.config.get("difficulties", {}).get(self.difficulty_key, {})
        cost_mult = diff_info.get("cost_multiplier", 1.0)
        time_mult = diff_info.get("construction_time_multiplier", 1.0)
        cooldown_sec = diff_info.get("command_cooldown_sec", 1.5)
        p_configs = self.config.get("plant_types", {})
        cfg = p_configs.get(plant_type, {})
        if not cfg:
            return False

        cost = int(cfg.get("build_cost", 10000000) * cost_mult)
        c_time = float(cfg.get("construction_time_sec", 30.0) * time_mult)

        if not self.economy.spend_money(cost):
            self.sound.play_alarm()
            return False

        n = sum(1 for p in self.plants if p.plant_type == plant_type)
        pos = self._get_plant_position(plant_type, n)

        if plant_type == "thermal":
            new_p = ThermalPlant(f"thermal_{n+1}", f"火力{n+1}号機", pos[0], pos[1], cfg, construction_time_sec=c_time, command_cooldown_sec=cooldown_sec)
        elif plant_type == "advanced_thermal":
            new_p = AdvancedThermalPlant(f"adv_thermal_{n+1}", f"改良火力{n+1}号", pos[0], pos[1], cfg, construction_time_sec=c_time, command_cooldown_sec=cooldown_sec)
        elif plant_type == "hydro":
            new_p = HydroPlant(f"hydro_{n+1}", f"水力{n+1}号機", pos[0], pos[1], cfg, construction_time_sec=c_time, command_cooldown_sec=cooldown_sec)
        elif plant_type == "pumped_storage":
            new_p = PumpedStoragePlant(f"pumped_{n+1}", f"揚水{n+1}号機", pos[0], pos[1], cfg, construction_time_sec=c_time, command_cooldown_sec=cooldown_sec)
        else:
            return False

        self.plants.append(new_p)
        self.grid.build_network(self.plants, self.town_mgr.consumers)
        self.sound.play_build()
        self.selected_obj = new_p
        self.construction_msg = f"【着工】{new_p.name} の建設工事を開始！（完成まで約{int(c_time)}秒）"
        self.construction_msg_timer = 5.0
        self.add_message_log(self.event_mgr.elapsed_time, "BUILD_START", self.construction_msg, 10)
        return True

    def _update_playing(self, mx: int, my: int):
        # 0. モーダル表示中のインタラクション (時間は停止)
        if self._update_message_log_modal(mx, my):
            return
        if self._update_substation_modal(mx, my):
            return
        if self._update_plant_build_modal(mx, my):
            return

        # 1行メッセージ表示領域（y: 42〜55）または L キーで履歴ログ画面へ遷移
        if (pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) and (42 <= my <= 55)) or pyxel.btnp(pyxel.KEY_L):
            self.is_showing_log = True
            self.log_scroll_y = 0
            self.sound.play_click()
            return

        # ESCキーでメニュー（タイトル画面）に戻る
        if pyxel.btnp(pyxel.KEY_ESCAPE):
            self.sound.play_click()
            self.state = GameState.TITLE
            self.selected_obj = None
            self.is_manual_paused = False
            return

        # オブジェクト選択中、手動ポーズ中、ログ閲覧中、開閉盤閲覧中、新設メニュー閲覧中は時間を停止する
        is_paused = (self.selected_obj is not None) or self.is_manual_paused or self.is_showing_log or self.is_showing_substation_modal or self.is_showing_build_modal
        dt = 0.0 if is_paused else (1.0 / 30.0)

        # 建設メッセージタイマーの減算 (時間が進んでいる時のみ)
        if dt > 0.0 and self.construction_msg_timer > 0:
            self.construction_msg_timer -= dt
            if self.construction_msg_timer <= 0:
                self.construction_msg = ""

        # 1. イベントマネージャー更新 (時間が進んでいる時のみ)
        if dt > 0.0:
            self.event_mgr.update(dt)
            if self.event_mgr.notice_sound_trigger:
                self.sound.play_notice()
                self.add_message_log(self.event_mgr.elapsed_time, "EVENT_NOTICE", self.event_mgr.active_banner_msg, 10)
            if self.event_mgr.event_sound_trigger:
                self.sound.play_event()
                self.add_message_log(self.event_mgr.elapsed_time, "EVENT_ACTIVE", self.event_mgr.active_banner_msg, self.event_mgr.banner_color)
            if getattr(self.event_mgr, "finish_sound_trigger", False):
                self.add_message_log(self.event_mgr.elapsed_time, "EVENT_END", self.event_mgr.active_banner_msg, 7)

        # 経済システムの単価更新
        self.economy.set_price_multiplier(self.event_mgr.current_price_multiplier)

        # 2. 需要家（町）更新 (時間が進んでいる時のみ)
        if dt > 0.0:
            old_cons_count = len(self.town_mgr.consumers)
            self.town_mgr.update(dt, self.event_mgr.current_load_multiplier)
            if self.town_mgr.notice_sound_trigger:
                self.sound.play_notice()
                self.add_message_log(self.event_mgr.elapsed_time, "TOWN_NOTICE", self.town_mgr.banner_msg, 10)
            if self.town_mgr.expand_sound_trigger:
                self.sound.play_build()
                self.add_message_log(self.event_mgr.elapsed_time, "TOWN_EXPAND", self.town_mgr.banner_msg, 9)
            if len(self.town_mgr.consumers) > old_cons_count:
                # 新規需要家が追加されたら送電網を再構築
                self.grid.build_network(self.plants, self.town_mgr.consumers)

        # 3. 発電所更新
        total_gen_mw = 0.0
        total_pump_mw = 0.0
        rebuild_needed = False
        for p in self.plants:
            if dt > 0.0:
                if hasattr(p, "update_gf"):
                    p.update_gf(self.freq_sys.freq, self.freq_sys.rated_freq)
                p.update(dt, self.event_mgr.current_hydro_multiplier)
            if getattr(p, "just_completed", False):
                self.sound.play_build()
                self.construction_msg = f"【完成】{p.name} の建設工事が完了し系統へ接続されました！"
                self.construction_msg_timer = 6.0
                self.add_message_log(self.event_mgr.elapsed_time, "BUILD_DONE", self.construction_msg, 10)
                rebuild_needed = True
            total_gen_mw += p.get_output_mw()
            total_pump_mw += p.get_load_mw()

        # 変電所タイマー更新
        if dt > 0.0:
            self.grid.substation.update(dt)

        if rebuild_needed:
            self.grid.build_network(self.plants, self.town_mgr.consumers)

        if self.grid.substation.is_connected:
            grid_gen_mw = total_gen_mw
            grid_load_mw = self.town_mgr.get_total_load_mw() + total_pump_mw
            supplied_mw = self.town_mgr.get_total_load_mw()
            actual_pump_mw = total_pump_mw
        else:
            # 変電所の送受電遮断中：系統を通した受電・送電はゼロ
            grid_gen_mw = 0.0
            grid_load_mw = 0.0
            supplied_mw = 0.0
            actual_pump_mw = 0.0

        # 4. 周波数更新 & 警報サウンド (時間が進んでいる時のみ)
        if dt > 0.0:
            self.freq_sys.update(grid_gen_mw, grid_load_mw, dt)
            if self.freq_sys.is_violating:
                self.alarm_sound_timer += dt
                # 危険度に応じてアラーム間隔を短縮
                interval = 0.4 if self.freq_sys.is_critical else 0.8
                if self.alarm_sound_timer >= interval:
                    self.alarm_sound_timer = 0.0
                    self.sound.play_alarm()
            else:
                self.alarm_sound_timer = 0.0

            # ブラックアウト（ゲームオーバー）判定
            if self.freq_sys.is_blackout:
                self.sound.play_gameover()
                self.add_message_log(self.event_mgr.elapsed_time, "BLACKOUT", f"【系統崩壊】周波数が限界({self.freq_sys.freq:.2f}Hz)を逸脱継続し、全系統が停止しました", 8)
                self.state = GameState.GAMEOVER
                return

        # 5. 送電網潮流更新
        plants_dict = {p.id: p for p in self.plants}
        consumers_dict = {c.id: c for c in self.town_mgr.consumers}
        self.grid.update_flows(plants_dict, consumers_dict, dt)

        # 6. 売電スコア・資金更新 (時間が進んでいる時のみ)
        if dt > 0.0:
            self.economy.update(supplied_mw, actual_pump_mw, dt)

            # ストーリーモードのクリア判定
            if self.is_story_mode and self.state == GameState.PLAYING:
                stg = STORY_STAGES[self.current_stage_idx]
                cleared, progress = check_stage_clear(stg, self.plants, self.economy.money, self.event_mgr.elapsed_time)
                self.story_goal_text = f"{stg['condition_desc']} ({progress})"
                if cleared:
                    self.sound.play_clear()
                    self.add_message_log(self.event_mgr.elapsed_time, "CLEAR", f"【ステージクリア】{stg['title']} を達成しました！", 10)
                    self.state = GameState.STAGE_CLEAR
                    self.selected_obj = None
                    return

        # 7. UI インタラクション (クリック・選択・スライダー・キー操作)
        self._handle_ui_input(mx, my)

    def _handle_ui_input(self, mx: int, my: int):
        # ホバー判定
        self.hovered_obj = self._get_object_at(mx, my)

        # マウス右クリックで選択解除・一時停止解除（時間再開）
        if pyxel.btnp(pyxel.MOUSE_BUTTON_RIGHT):
            if self.selected_obj is not None or self.is_manual_paused:
                self.selected_obj = None
                self.is_manual_paused = False
                self.sound.play_click()
                return

        # Tab キーによる左手での設備順次選択切替 (Shift+Tab で逆順)
        if pyxel.btnp(pyxel.KEY_TAB):
            all_objs = self.plants + [self.grid.substation] + self.town_mgr.consumers
            if all_objs:
                curr_idx = -1
                for idx, obj in enumerate(all_objs):
                    if obj == self.selected_obj:
                        curr_idx = idx
                        break
                is_shift = pyxel.btn(pyxel.KEY_SHIFT)
                next_idx = (curr_idx - 1) % len(all_objs) if is_shift else (curr_idx + 1) % len(all_objs)
                self.selected_obj = all_objs[next_idx]
                self.is_manual_paused = False
                self.sound.play_click()
                if hasattr(self.selected_obj, "plant_type") and self.selected_obj.plant_type in ("thermal", "advanced_thermal") and self.slider:
                    self.slider.set_bounds(self.selected_obj.min_output_mw, self.selected_obj.max_output_mw)
                    target_val = getattr(self.selected_obj, "pending_base_output_mw", getattr(self.selected_obj, "pending_target_mw", self.selected_obj.target_output_mw))
                    self.slider.set_value(target_val)

        # オブジェクトクリック選択 / 空き地クリックでの時間停止
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            # 下部パネル（panel_y=268）より上のマップ領域をクリックした場合
            if my < 268:
                obj = self._get_object_at(mx, my)
                if obj is not None:
                    # 設備をクリック: 設備を選択して指令モード（時間停止）
                    self.selected_obj = obj
                    self.is_manual_paused = False
                    self.sound.play_click()
                    if hasattr(obj, "plant_type") and obj.plant_type in ("thermal", "advanced_thermal") and self.slider:
                        self.slider.set_bounds(obj.min_output_mw, obj.max_output_mw)
                        target_val = getattr(obj, "pending_base_output_mw", getattr(obj, "pending_target_mw", obj.target_output_mw))
                        self.slider.set_value(target_val)
                else:
                    # 何もないところ（空き地）をクリック: 時間停止（ポーズ）
                    if self.selected_obj is not None:
                        # 設備選択中なら選択解除して全体時間停止へ移行
                        self.selected_obj = None
                        self.is_manual_paused = True
                        self.sound.play_click()
                    else:
                        # 空き地クリックで一時停止 ↔ 再開をトグル
                        self.is_manual_paused = not self.is_manual_paused
                        self.sound.play_click()

        # 空き地ポーズ中、Spaceキーでも時間再開可能
        if self.selected_obj is None and self.is_manual_paused:
            if pyxel.btnp(pyxel.KEY_SPACE):
                self.is_manual_paused = False
                self.sound.play_click()

        # ボタン更新
        for btn in self.buttons.values():
            btn.update(mx, my)

        # 閉じるボタンが押されたら選択解除
        if "btn_close" in self.buttons and self.buttons["btn_close"].is_pressed():
            self.selected_obj = None
            self.is_manual_paused = False
            self.sound.play_click()
            return

        # スライダー更新（火力・改良火力発電所選択中かつ建設中でない場合）
        if self.selected_obj and hasattr(self.selected_obj, "plant_type") and self.selected_obj.plant_type in ("thermal", "advanced_thermal"):
            p = self.selected_obj
            if not getattr(p, "is_under_construction", False) and self.slider:
                self.slider.set_bounds(p.min_output_mw, p.max_output_mw)
                if p.can_operate():
                    if self.slider.update(mx, my):
                        p.set_target(self.slider.value)
                elif not self.slider.is_dragging:
                    target_val = getattr(p, "pending_base_output_mw", getattr(p, "pending_target_mw", p.target_output_mw))
                    self.slider.set_value(target_val)

        # ボタン・キー入力処理
        self._handle_button_and_key_inputs(mx, my)

    def _handle_button_and_key_inputs(self, mx: int, my: int):
        # 1. 選択中オブジェクトの操作
        if self.selected_obj is not None:
            obj = self.selected_obj
            can_op = getattr(obj, "can_operate", lambda: True)()

            # 指令送信 (btn_commit または Enter キー)
            commit_pressed = False
            if "btn_commit" in self.buttons and self.buttons["btn_commit"].is_pressed():
                commit_pressed = True
            elif pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_KP_ENTER):
                commit_pressed = True

            if commit_pressed and can_op:
                if hasattr(obj, "commit_command"):
                    if obj.commit_command():
                        self.sound.play_switch()
                        if hasattr(obj, "substation_type"):
                            if obj.is_connected:
                                self.add_message_log(self.event_mgr.elapsed_time, "SUBSTATION", "【中央変電所】全系統の送受電を復旧・再開しました！", 10)
                            else:
                                self.add_message_log(self.event_mgr.elapsed_time, "SUBSTATION", "【中央変電所】全系統の送受電を緊急停止（全系統遮断）しました！", 8)
                        # 送信完了後は選択解除して時間を再開
                        self.selected_obj = None
                        self.is_manual_paused = False
                        return

            # 各設備別の入力受付
            if getattr(obj, "is_under_construction", False):
                pass
            elif hasattr(obj, "plant_type") and obj.plant_type in ("thermal", "advanced_thermal"):
                p = obj
                is_shift = pyxel.btn(pyxel.KEY_SHIFT) or pyxel.btn(pyxel.KEY_CTRL)
                cur_val = getattr(p, "pending_base_output_mw", getattr(p, "pending_target_mw", p.target_output_mw))

                if self.buttons["btn_dec10"].is_pressed() or (pyxel.btnp(pyxel.KEY_S) and is_shift):
                    p.set_target(cur_val - 10.0)
                    self.sound.play_click()
                elif self.buttons["btn_inc10"].is_pressed() or (pyxel.btnp(pyxel.KEY_W) and is_shift):
                    p.set_target(cur_val + 10.0)
                    self.sound.play_click()
                elif self.buttons["btn_dec1"].is_pressed():
                    p.set_target(cur_val - 1.0)
                    self.sound.play_click()
                elif self.buttons["btn_inc1"].is_pressed():
                    p.set_target(cur_val + 1.0)
                    self.sound.play_click()
                elif self.buttons["btn_min"].is_pressed():
                    p.set_target(p.min_output_mw)
                    self.sound.play_click()
                elif self.buttons["btn_max"].is_pressed():
                    p.set_target(p.max_output_mw)
                    self.sound.play_click()

                # 改良火力専用: ガバナフリー（GF）運転切替 (Gキー / ボタン)
                if obj.plant_type == "advanced_thermal":
                    if self.buttons["btn_gf_toggle"].is_pressed() or pyxel.btnp(pyxel.KEY_G):
                        p.toggle_pending_governor_free()
                        self.sound.play_click()

                if self.slider and not self.slider.is_dragging:
                    target_val = getattr(p, "pending_base_output_mw", getattr(p, "pending_target_mw", p.target_output_mw))
                    self.slider.set_value(target_val)

            elif hasattr(obj, "plant_type") and obj.plant_type == "pumped_storage":
                p = obj
                if self.buttons["btn_pump_off"].is_pressed():
                    p.set_pending_mode("OFF")
                    self.sound.play_click()
                elif self.buttons["btn_pump_gen"].is_pressed():
                    p.set_pending_mode("GEN")
                    self.sound.play_click()
                elif self.buttons["btn_pump_pump"].is_pressed():
                    p.set_pending_mode("PUMP")
                    self.sound.play_click()
                elif pyxel.btnp(pyxel.KEY_SPACE):
                    p.toggle_pending_mode()
                    self.sound.play_click()

            elif hasattr(obj, "substation_type"):
                sub = obj
                if self.buttons["btn_toggle_power"].is_pressed() or pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_F):
                    self.is_showing_substation_modal = True
                    self.substation_scroll_y = 0
                    for p in self.plants:
                        p.pending_connected = p.connected
                    for c in self.town_mgr.consumers:
                        c.pending_connected = c.is_connected
                    self.sound.play_click()

            elif hasattr(obj, "consumer_type"):
                pass

        # 2. 設備新設メニューを開く（[＋発電所新設] ボタン または B キー）
        if self.buttons["btn_open_build"].is_pressed() or pyxel.btnp(pyxel.KEY_B):
            self.is_showing_build_modal = True
            self.sound.play_click()
            self.selected_obj = None
            self.is_manual_paused = False

    def _get_object_at(self, mx: int, my: int):
        # 変電所判定 (中心 200, 150, サイズ 20x20)
        sub = getattr(self.grid, "substation", None)
        if sub and (sub.x - 12 <= mx <= sub.x + 12 and sub.y - 12 <= my <= sub.y + 12):
            return sub
        # 発電所判定
        for p in self.plants:
            if p.x - 2 <= mx <= p.x + 28 and p.y - 2 <= my <= p.y + 24:
                return p
        # 需要家判定
        for c in self.town_mgr.consumers:
            if c.x - 2 <= mx <= c.x + 24 and c.y - 2 <= my <= c.y + 20:
                return c
        return None

    def _update_gameover(self, mx: int, my: int):
        # 履歴ログモーダル表示中の更新
        if self._update_message_log_modal(mx, my):
            return

        # Lキー押下、またはゲームオーバー画面の「履歴ログ確認」ボタンクリックで履歴表示
        # ボタン位置: gx=65, gw=350, btn_w=230, btn_x=125, btn_y=220 (gy=42, gy+178), btn_h=18
        if pyxel.btnp(pyxel.KEY_L):
            self.is_showing_log = True
            self.log_scroll_y = 0
            self.sound.play_click()
            return

        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            # 履歴ログ確認ボタン判定
            if 125 <= mx <= 355 and 220 <= my <= 238:
                self.is_showing_log = True
                self.log_scroll_y = 0
                self.sound.play_click()
                return
            # 上部1行メッセージバー判定
            if 42 <= my <= 55:
                self.is_showing_log = True
                self.log_scroll_y = 0
                self.sound.play_click()
                return

        # ESCキーまたはQキーでタイトル画面に戻る
        if pyxel.btnp(pyxel.KEY_ESCAPE) or pyxel.btnp(pyxel.KEY_Q):
            self.sound.play_click()
            self.state = GameState.TITLE
            self.selected_obj = None
            return

        # GameOver後の再挑戦は右クリックまたはRキー
        if pyxel.btnp(pyxel.KEY_R) or pyxel.btnp(pyxel.MOUSE_BUTTON_RIGHT):
            self.sound.play_click()
            if self.is_story_mode:
                self.start_story_stage(self.current_stage_idx)
            else:
                self.start_game(self.difficulty_key)

    def draw(self):
        pyxel.cls(0)

        if self.state == GameState.TITLE:
            self._draw_title()
        elif self.state == GameState.STAGE_BRIEFING:
            self.renderer.draw_stage_briefing(
                STORY_STAGES[self.current_stage_idx],
                len(STORY_STAGES),
                pyxel.mouse_x,
                pyxel.mouse_y
            )
        elif self.state in (GameState.PLAYING, GameState.STAGE_CLEAR, GameState.GAMEOVER):
            diff_name = "初級 (ストーリー)" if self.is_story_mode else self.config.get("difficulties", {}).get(self.difficulty_key, {}).get("name", "通常")
            
            # バナーメッセージの統合（発電・需要オブジェクトと被らないよう1行固定表示）
            banner = ""
            b_color = 7

            if self.event_mgr.active_banner_msg:
                # 複数行ある場合は最初の行を表示
                banner = self.event_mgr.active_banner_msg.split("\n")[0]
                b_color = self.event_mgr.banner_color
            elif self.town_mgr.banner_msg:
                banner = self.town_mgr.banner_msg.split("\n")[0]
                b_color = self.town_mgr.banner_color
            elif self.construction_msg:
                banner = self.construction_msg.split("\n")[0]
                b_color = 10

            if self.grid.substation.is_connected:
                cur_total_gen = sum(p.get_output_mw() for p in self.plants)
                cur_total_load = self.town_mgr.get_total_load_mw() + sum(p.get_load_mw() for p in self.plants)
            else:
                cur_total_gen = 0.0
                cur_total_load = 0.0

            is_paused = (self.selected_obj is not None) or self.is_manual_paused or self.is_showing_log or self.is_showing_substation_modal or self.is_showing_build_modal
            sim_state = {
                "elapsed_time": self.event_mgr.elapsed_time,
                "money": self.economy.money,
                "score": self.economy.total_sales_revenue,
                "current_price": self.economy.current_price,
                "price_multiplier": self.economy.price_multiplier,
                "total_gen_mw": cur_total_gen,
                "total_load_mw": cur_total_load,
                "frequency": self.freq_sys.freq,
                "rated_freq": self.freq_sys.rated_freq,
                "freq_tolerance": self.freq_sys.tolerance,
                "is_violating": self.freq_sys.is_violating,
                "is_critical": self.freq_sys.is_critical,
                "violation_ratio": self.freq_sys.violation_ratio,
                "difficulty_name": diff_name,
                "banner_msg": banner,
                "banner_color": b_color,
                "is_paused": is_paused,
                "story_goal_text": self.story_goal_text if self.is_story_mode else ""
            }

            next_exp = self.town_mgr.next_expansion if self.town_mgr.is_noticing else None
            # 1. まずマップを描画（y=42〜268の背景や送電線、設備、建設予定マーカー）
            self.renderer.draw_map(self.plants, self.town_mgr.consumers, self.grid.lines, self.selected_obj, self.hovered_obj, next_expansion=next_exp, substation=self.grid.substation)
            # 2. マップの上に重ねてHUDヘッダーとイベントバナーを描画（マップ背景で塗りつぶされない！）
            self.renderer.draw_hud(sim_state)
            # 3. 下部操作パネルを描画
            self.renderer.draw_inspector_and_controls(self.selected_obj, self.buttons, self.plants, self.grid.lines, pyxel.mouse_x, pyxel.mouse_y, slider=self.slider, is_manual_paused=self.is_manual_paused)

            # 周波数異常時の画面全体赤色点滅オーバーレイ（点滅間隔を短くして危機感を演出）
            if self.state == GameState.PLAYING and self.freq_sys.is_violating:
                self.renderer.draw_frequency_alarm_overlay(self.freq_sys.violation_ratio, self.freq_sys.is_critical)

            if self.state == GameState.GAMEOVER:
                self.renderer.draw_game_over(
                    score=self.economy.total_sales_revenue,
                    time_sec=self.event_mgr.elapsed_time,
                    energy_kwh=self.economy.total_energy_kwh,
                    mx=pyxel.mouse_x,
                    my=pyxel.mouse_y
                )

            if self.state == GameState.STAGE_CLEAR:
                stg = STORY_STAGES[self.current_stage_idx]
                self.renderer.draw_stage_clear(
                    stage_data=stg,
                    total_stages=len(STORY_STAGES),
                    score=self.economy.total_sales_revenue,
                    money=self.economy.money,
                    time_sec=self.event_mgr.elapsed_time,
                    energy_kwh=self.economy.total_energy_kwh,
                    mx=pyxel.mouse_x,
                    my=pyxel.mouse_y
                )

            # 4. 変電所開閉盤モーダルを描画（表示中のみ。時間が停止した状態で受給個別設定可能）
            if self.is_showing_substation_modal:
                can_com = self.grid.substation.can_operate()
                self.renderer.draw_substation_modal(
                    self.plants, self.town_mgr.consumers,
                    self.substation_tab, self.substation_scroll_y,
                    pyxel.mouse_x, pyxel.mouse_y,
                    can_commit=can_com
                )

            # 5. 発電設備新設モーダルダイアログを描画（表示中のみ。時間が停止した状態で設備投資可能）
            if self.is_showing_build_modal:
                diff_info = self.config.get("difficulties", {}).get(self.difficulty_key, {})
                c_mult = diff_info.get("cost_multiplier", 1.0)
                t_mult = diff_info.get("construction_time_multiplier", 1.0)
                p_configs = self.config.get("plant_types", {})
                self.renderer.draw_plant_build_modal(
                    plant_configs=p_configs,
                    current_money=self.economy.money,
                    cost_multiplier=c_mult,
                    time_multiplier=t_mult,
                    plants=self.plants,
                    mx=pyxel.mouse_x,
                    my=pyxel.mouse_y
                )

            # 6. 最前面にメッセージ履歴ログモーダルを描画（表示中のみ。時間が停止した状態で確認可能。ゲームオーバー後も閲覧可能）
            if self.is_showing_log:
                self.renderer.draw_message_log_modal(self.message_logs, self.log_scroll_y, pyxel.mouse_x, pyxel.mouse_y)

    def _draw_title(self):
        # タイトル画面描画 (480x360)
        pyxel.rect(0, 0, 480, 360, 1)

        # タイトルロゴ
        self.renderer.draw_text(135, 28, "=== 電力運用シミュレータ ===", 10)
        self.renderer.draw_text(175, 46, "GRID FREQUENCY CONTROL", 7)
        
        # 説明文
        self.renderer.draw_text(85, 72, "周波数 60.00Hz を維持して電力系統崩壊 (大停電) を防ごう！\n市場単価の高騰時に発電し、余剰時には揚水充電して売電収益を最大化！", 11, line_spacing=14)

        # 難易度ボタン
        self.renderer.draw_text(176, 122, "- モード／難易度を選択 -", 6)
        self.buttons["title_easy"].draw()
        self.buttons["title_normal"].draw()
        self.buttons["title_hard"].draw()

        # 操作説明ボックス
        bx, by, bw, bh = 40, 214, 400, 140
        pyxel.rect(bx, by, bw, bh, 0)
        pyxel.rectb(bx, by, bw, bh, 5)
        self.renderer.draw_text(bx + 8, by + 4, "【操作ガイド（司令塔モード）】", 10)
        self.renderer.draw_text(bx + 8, by + 18, "・時間一時停止: マップ空き地クリックで時間停止 ↔ 再開 (右クリック/Space)", 11)
        self.renderer.draw_text(bx + 8, by + 32, "・設備選択: Tabキー / 設備クリック (選択中も時間が一時停止)", 7)
        self.renderer.draw_text(bx + 8, by + 46, "・指令送信: Enterキー / [指令送信]ボタン (確定後、時間再開&待機時間)", 10)
        self.renderer.draw_text(bx + 8, by + 60, "・火力出力: W/S (微増減), Q/E (10MW), A(MIN), D(MAX), スライダー", 7)
        self.renderer.draw_text(bx + 8, by + 74, "・改良火力: Gキーでガバナフリー(GF)自動調速運転ON/OFF！周波数自律安定化", 11)
        self.renderer.draw_text(bx + 8, by + 88, "・揚水切替: W(発電), S(揚水充電), A(停止) | 変電所: Spaceで系統開閉盤", 7)
        self.renderer.draw_text(bx + 8, by + 102, "・設備新設: Bキー / [＋発電所新設]で新設メニューを開き新発電所を着工！", 10)
        self.renderer.draw_text(bx + 8, by + 116, "・履歴ログ: Lキー / メッセージバーClick | ESCキー: タイトルに戻る", 9)


if __name__ == "__main__":
    PowerGridApp()
