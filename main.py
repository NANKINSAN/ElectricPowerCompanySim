"""
電力運用シミュレータ (Electric Power Company Simulator)
Pyxel 2D レトロゲーム
"""
import pyxel
import json
import os

from sim.frequency import FrequencySystem
from sim.power_plants import ThermalPlant, HydroPlant, PumpedStoragePlant
from sim.consumers import TownManager
from sim.grid import GridNetwork
from sim.economy import EconomySystem
from sim.event_manager import EventManager
from ui.sound import SoundManager
from ui.renderer import GameRenderer
from ui.controls import Button
from utils.resource import get_config_path, get_resource_path

class GameState:
    TITLE = 0
    PLAYING = 1
    GAMEOVER = 2

class PowerGridApp:
    def __init__(self):
        # 1. 設定ファイル読み込み
        self.config = self._load_config("config.json")
        fps = self.config.get("general", {}).get("fps", 30)
        
        # 2. Pyxel 初期化 (320x240, 30fps)
        pyxel.init(320, 240, title="電力運用シミュレータ - Power Grid Sim", fps=fps)
        pyxel.mouse(True)

        # 3. サウンド・レンダラー初期化
        self.sound = SoundManager()
        self.renderer = GameRenderer()

        # 4. ゲーム状態・難易度
        self.state = GameState.TITLE
        self.difficulty_key = "normal"
        self.selected_obj = None
        self.hovered_obj = None

        # 5. UI ボタン生成
        self.buttons = {}
        self._init_buttons()

        # 6. アラーム音インターバル管理
        self.alarm_sound_timer = 0.0

        pyxel.run(self.update, self.draw)

    def _load_config(self, filename: str) -> dict:
        path = get_config_path(filename)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _init_buttons(self):
        panel_y = 182
        # 火力用操作ボタン
        self.buttons["btn_dec10"] = Button(6, panel_y + 26, 24, 12, "-10", 1, 7, 9)
        self.buttons["btn_dec1"]  = Button(33, panel_y + 26, 20, 12, "-1", 1, 7, 9)
        self.buttons["btn_inc1"]  = Button(56, panel_y + 26, 20, 12, "+1", 1, 7, 9)
        self.buttons["btn_inc10"] = Button(79, panel_y + 26, 24, 12, "+10", 1, 7, 9)
        self.buttons["btn_min"]   = Button(106, panel_y + 26, 24, 12, "MIN", 1, 7, 9)
        self.buttons["btn_max"]   = Button(133, panel_y + 26, 24, 12, "MAX", 1, 7, 9)

        # 揚水用操作ボタン
        self.buttons["btn_pump_off"]  = Button(6, panel_y + 26, 32, 12, "OFF", 1, 7, 9)
        self.buttons["btn_pump_gen"]  = Button(42, panel_y + 26, 54, 12, "発電(GEN)", 1, 7, 10)
        self.buttons["btn_pump_pump"] = Button(100, panel_y + 26, 54, 12, "揚水(PUMP)", 1, 7, 12)

        # 需要家用送電切替ボタン
        self.buttons["btn_toggle_power"] = Button(6, panel_y + 26, 80, 12, "送電 ON/OFF", 1, 7, 9)

        # 設備新設（購入）ボタン
        self.buttons["btn_buy_thermal"] = Button(184, panel_y + 38, 42, 14, "+火力 8万", 4, 7, 9)
        self.buttons["btn_buy_hydro"]   = Button(229, panel_y + 38, 42, 14, "+水力 6万", 1, 7, 11)
        self.buttons["btn_buy_pumped"]  = Button(274, panel_y + 38, 42, 14, "+揚水 12万", 2, 7, 10)

        # タイトル画面用 難易度選択ボタン
        self.buttons["title_easy"]   = Button(110, 114, 100, 15, "初級 (Easy)", 1, 7, 11)
        self.buttons["title_normal"] = Button(110, 133, 100, 15, "中級 (Normal)", 1, 7, 10)
        self.buttons["title_hard"]   = Button(110, 152, 100, 15, "上級 (Hard)", 1, 7, 8)

    def start_game(self, diff_key: str):
        self.difficulty_key = diff_key
        diff_info = self.config.get("difficulties", {}).get(diff_key, {})
        rated_f = self.config.get("general", {}).get("rated_frequency_hz", 60.0)
        base_price = self.config.get("general", {}).get("base_electricity_price", 30.0)
        init_money = self.config.get("general", {}).get("initial_money", 100000) + diff_info.get("initial_money_bonus", 0)
        expand_interval = self.config.get("general", {}).get("town_expansion_interval_sec", 45)

        # 周波数システム
        tol = diff_info.get("freq_tolerance_hz", 0.5)
        max_dur = diff_info.get("max_violation_duration_sec", 5.0)
        self.freq_sys = FrequencySystem(rated_freq=rated_f, tolerance=tol, max_violation_sec=max_dur)

        # 経済システム
        self.economy = EconomySystem(base_price=base_price, initial_money=init_money)

        # イベントマネージャー
        self.event_mgr = EventManager("scenario.json")

        # 発電所初期構成
        p_configs = self.config.get("plant_types", {})
        self.plants = [
            ThermalPlant("thermal_1", "中央火力1号", 30, 60, p_configs.get("thermal", {})),
            HydroPlant("hydro_1", "上流第1水力", 35, 115, p_configs.get("hydro", {})),
            PumpedStoragePlant("pumped_1", "黒岳揚水所", 30, 155, p_configs.get("pumped_storage", {}))
        ]

        # 需要家・町発展
        self.town_mgr = TownManager(expansion_interval=expand_interval)

        # 送電網
        self.grid = GridNetwork()
        self.grid.build_network(self.plants, self.town_mgr.consumers)

        self.selected_obj = self.plants[0]
        self.state = GameState.PLAYING
        self.alarm_sound_timer = 0.0

    def update(self):
        mx, my = pyxel.mouse_x, pyxel.mouse_y

        if self.state == GameState.TITLE:
            self._update_title(mx, my)
        elif self.state == GameState.PLAYING:
            self._update_playing(mx, my)
        elif self.state == GameState.GAMEOVER:
            self._update_gameover(mx, my)

    def _update_title(self, mx: int, my: int):
        for k in ["title_easy", "title_normal", "title_hard"]:
            btn = self.buttons[k]
            btn.update(mx, my)
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) and btn.is_hovered:
                diff = k.replace("title_", "")
                self.sound.play_click()
                self.start_game(diff)
                return

    def _update_playing(self, mx: int, my: int):
        dt = 1.0 / 30.0

        # 1. イベントマネージャー更新
        self.event_mgr.update(dt)
        if self.event_mgr.notice_sound_trigger:
            self.sound.play_notice()
        if self.event_mgr.event_sound_trigger:
            self.sound.play_event()

        # 経済システムの単価更新
        self.economy.set_price_multiplier(self.event_mgr.current_price_multiplier)

        # 2. 需要家（町）更新
        old_cons_count = len(self.town_mgr.consumers)
        self.town_mgr.update(dt, self.event_mgr.current_load_multiplier)
        if len(self.town_mgr.consumers) > old_cons_count:
            # 新規需要家が追加されたら送電網を再構築
            self.grid.build_network(self.plants, self.town_mgr.consumers)
            self.sound.play_build()

        # 3. 発電所更新
        total_gen_mw = 0.0
        total_pump_mw = 0.0
        for p in self.plants:
            p.update(dt, self.event_mgr.current_hydro_multiplier)
            total_gen_mw += p.get_output_mw()
            total_pump_mw += p.get_load_mw()

        total_load_mw = self.town_mgr.get_total_load_mw() + total_pump_mw

        # 4. 周波数更新 & 警報サウンド
        self.freq_sys.update(total_gen_mw, total_load_mw, dt)
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
            self.state = GameState.GAMEOVER
            return

        # 5. 送電網潮流更新
        plants_dict = {p.id: p for p in self.plants}
        consumers_dict = {c.id: c for c in self.town_mgr.consumers}
        self.grid.update_flows(plants_dict, consumers_dict, dt)

        # 6. 売電スコア・資金更新
        supplied_mw = self.town_mgr.get_total_load_mw()
        self.economy.update(supplied_mw, total_pump_mw, dt)

        # 7. UI インタラクション (クリック・選択・操作)
        self._handle_ui_input(mx, my)

    def _handle_ui_input(self, mx: int, my: int):
        # ホバー判定
        self.hovered_obj = self._get_object_at(mx, my)

        # オブジェクトクリック選択
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            obj = self._get_object_at(mx, my)
            if obj is not None:
                self.selected_obj = obj
                self.sound.play_click()

        # ボタン更新 & クリック
        for btn in self.buttons.values():
            btn.update(mx, my)

        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self._handle_button_clicks(mx, my)

        # キーボードショートカット
        if self.selected_obj and hasattr(self.selected_obj, "plant_type") and self.selected_obj.plant_type == "thermal":
            if pyxel.btnp(pyxel.KEY_UP) or pyxel.btnp(pyxel.KEY_W):
                self.selected_obj.set_target(self.selected_obj.target_output_mw + 5.0)
                self.sound.play_click()
            elif pyxel.btnp(pyxel.KEY_DOWN) or pyxel.btnp(pyxel.KEY_S):
                self.selected_obj.set_target(self.selected_obj.target_output_mw - 5.0)
                self.sound.play_click()

        elif self.selected_obj and hasattr(self.selected_obj, "plant_type") and self.selected_obj.plant_type == "pumped_storage":
            if pyxel.btnp(pyxel.KEY_SPACE):
                self.selected_obj.toggle_mode()
                self.sound.play_switch()

    def _handle_button_clicks(self, mx: int, my: int):
        # 1. 選択中オブジェクトの操作
        if self.selected_obj is not None:
            if hasattr(self.selected_obj, "plant_type") and self.selected_obj.plant_type == "thermal":
                p = self.selected_obj
                if self.buttons["btn_dec10"].is_hovered:
                    p.set_target(p.target_output_mw - 10.0)
                    self.sound.play_click()
                elif self.buttons["btn_dec1"].is_hovered:
                    p.set_target(p.target_output_mw - 1.0)
                    self.sound.play_click()
                elif self.buttons["btn_inc1"].is_hovered:
                    p.set_target(p.target_output_mw + 1.0)
                    self.sound.play_click()
                elif self.buttons["btn_inc10"].is_hovered:
                    p.set_target(p.target_output_mw + 10.0)
                    self.sound.play_click()
                elif self.buttons["btn_min"].is_hovered:
                    p.set_target(p.min_output_mw)
                    self.sound.play_click()
                elif self.buttons["btn_max"].is_hovered:
                    p.set_target(p.max_output_mw)
                    self.sound.play_click()

            elif hasattr(self.selected_obj, "plant_type") and self.selected_obj.plant_type == "pumped_storage":
                p = self.selected_obj
                if self.buttons["btn_pump_off"].is_hovered:
                    p.set_mode("OFF")
                    self.sound.play_switch()
                elif self.buttons["btn_pump_gen"].is_hovered:
                    p.set_mode("GEN")
                    self.sound.play_switch()
                elif self.buttons["btn_pump_pump"].is_hovered:
                    p.set_mode("PUMP")
                    self.sound.play_switch()

            elif hasattr(self.selected_obj, "consumer_type"):
                c = self.selected_obj
                if self.buttons["btn_toggle_power"].is_hovered:
                    c.toggle_connection()
                    self.sound.play_switch()

        # 2. 設備新設（購入）
        p_configs = self.config.get("plant_types", {})
        if self.buttons["btn_buy_thermal"].is_hovered:
            cost = p_configs.get("thermal", {}).get("build_cost", 80000)
            if self.economy.spend_money(cost):
                n = sum(1 for p in self.plants if p.plant_type == "thermal") + 1
                new_p = ThermalPlant(f"thermal_{n}", f"火力{n}号機", 30, 48 + n * 24, p_configs.get("thermal", {}))
                self.plants.append(new_p)
                self.grid.build_network(self.plants, self.town_mgr.consumers)
                self.sound.play_build()
                self.selected_obj = new_p

        elif self.buttons["btn_buy_hydro"].is_hovered:
            cost = p_configs.get("hydro", {}).get("build_cost", 60000)
            if self.economy.spend_money(cost):
                n = sum(1 for p in self.plants if p.plant_type == "hydro") + 1
                new_p = HydroPlant(f"hydro_{n}", f"水力{n}号機", 65, 80 + n * 24, p_configs.get("hydro", {}))
                self.plants.append(new_p)
                self.grid.build_network(self.plants, self.town_mgr.consumers)
                self.sound.play_build()
                self.selected_obj = new_p

        elif self.buttons["btn_buy_pumped"].is_hovered:
            cost = p_configs.get("pumped_storage", {}).get("build_cost", 120000)
            if self.economy.spend_money(cost):
                n = sum(1 for p in self.plants if p.plant_type == "pumped_storage") + 1
                new_p = PumpedStoragePlant(f"pumped_{n}", f"揚水{n}号機", 75, 140 + n * 20, p_configs.get("pumped_storage", {}))
                self.plants.append(new_p)
                self.grid.build_network(self.plants, self.town_mgr.consumers)
                self.sound.play_build()
                self.selected_obj = new_p

    def _get_object_at(self, mx: int, my: int):
        # 発電所判定
        for p in self.plants:
            if p.x <= mx <= p.x + 24 and p.y <= my <= p.y + 20:
                return p
        # 需要家判定
        for c in self.town_mgr.consumers:
            if c.x <= mx <= c.x + 20 and c.y <= my <= c.y + 16:
                return c
        return None

    def _update_gameover(self, mx: int, my: int):
        if pyxel.btnp(pyxel.KEY_R) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.sound.play_click()
            self.start_game(self.difficulty_key)
        elif pyxel.btnp(pyxel.KEY_Q):
            self.state = GameState.TITLE

    def draw(self):
        pyxel.cls(0)

        if self.state == GameState.TITLE:
            self._draw_title()
        elif self.state in (GameState.PLAYING, GameState.GAMEOVER):
            # シミュレーション状態のパッキング
            diff_name = self.config.get("difficulties", {}).get(self.difficulty_key, {}).get("name", "通常")
            
            # バナーメッセージの選択（イベント優先、なければ街の発展通知）
            banner = self.event_mgr.active_banner_msg
            b_color = self.event_mgr.banner_color
            if not banner and self.town_mgr.msg_timer > 0:
                banner = self.town_mgr.latest_expansion_msg
                b_color = 11

            sim_state = {
                "elapsed_time": self.event_mgr.elapsed_time,
                "money": self.economy.money,
                "score": self.economy.total_sales_revenue,
                "current_price": self.economy.current_price,
                "price_multiplier": self.economy.price_multiplier,
                "total_gen_mw": sum(p.get_output_mw() for p in self.plants),
                "total_load_mw": self.town_mgr.get_total_load_mw() + sum(p.get_load_mw() for p in self.plants),
                "frequency": self.freq_sys.freq,
                "rated_freq": self.freq_sys.rated_freq,
                "freq_tolerance": self.freq_sys.tolerance,
                "is_violating": self.freq_sys.is_violating,
                "is_critical": self.freq_sys.is_critical,
                "violation_ratio": self.freq_sys.violation_ratio,
                "difficulty_name": diff_name,
                "banner_msg": banner,
                "banner_color": b_color
            }

            self.renderer.draw_hud(sim_state)
            self.renderer.draw_map(self.plants, self.town_mgr.consumers, self.grid.lines, self.selected_obj, self.hovered_obj)
            self.renderer.draw_inspector_and_controls(self.selected_obj, self.buttons, self.plants, self.grid.lines, pyxel.mouse_x, pyxel.mouse_y)

            if self.state == GameState.GAMEOVER:
                self.renderer.draw_game_over(
                    score=self.economy.total_sales_revenue,
                    time_sec=self.event_mgr.elapsed_time,
                    energy_kwh=self.economy.total_energy_kwh
                )

    def _draw_title(self):
        # タイトル画面描画
        pyxel.rect(0, 0, 320, 240, 1)

        # タイトルロゴ
        self.renderer.draw_text(85, 24, "=== 電力運用シミュレータ ===", 10)
        self.renderer.draw_text(105, 40, "GRID FREQUENCY CONTROL", 7)
        
        # 1行全角20文字程度に洗練
        self.renderer.draw_text(70, 56, "周波数60.00Hzを維持して\n系統崩壊(大停電)を防ごう！", 11, line_spacing=12)
        self.renderer.draw_text(70, 82, "市場単価に合わせて揚水を充放電し\n売電収入の最大化を狙え！", 7, line_spacing=12)

        # 難易度ボタン
        self.renderer.draw_text(125, 102, "- 難易度を選択 -", 6)
        self.buttons["title_easy"].draw()
        self.buttons["title_normal"].draw()
        self.buttons["title_hard"].draw()

        # 操作説明（無駄な文字を削り、1行全角20文字程度で洗練）
        pyxel.rect(48, 174, 224, 56, 0)
        pyxel.rectb(48, 174, 224, 56, 5)
        self.renderer.draw_text(56, 178, "【基本操作】", 10)
        self.renderer.draw_text(56, 190, "・クリック: 設備を選択 / 各種操作", 7)
        self.renderer.draw_text(56, 201, "・火力: 出力調整 (W/Sキー)", 7)
        self.renderer.draw_text(56, 212, "・揚水: 充放電切替 (Spaceキー)", 7)
        self.renderer.draw_text(56, 223, "・電線: マウスを重ねて潮流監視", 7)


if __name__ == "__main__":
    PowerGridApp()
