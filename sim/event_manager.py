"""
イベント・シナリオ管理マネージャー
JSON形式のシナリオ定義をロードし、事前予告・イベント発火・パラメータ変動を制御
"""
import json
import os
from utils.resource import get_config_path

class ScenarioEvent:
    def __init__(self, data: dict):
        self.trigger_time = float(data.get("trigger_time_sec", 30))
        self.notice_time = float(data.get("notice_time_sec", 10))
        self.duration = float(data.get("duration_sec", 20))
        self.name = data.get("name", "イベント")
        self.notice_msg = data.get("notice_msg", "イベント予告")
        self.active_msg = data.get("active_msg", "イベント発生中")
        self.price_multiplier = float(data.get("price_multiplier", 1.0))
        self.load_multiplier = float(data.get("load_multiplier", 1.0))
        self.hydro_multiplier = float(data.get("hydro_multiplier", 1.0))

        self.noticed = False
        self.started = False
        self.finished = False

    def reset(self):
        self.noticed = False
        self.started = False
        self.finished = False


class EventManager:
    def __init__(self, scenario_filename: str = "scenario.json"):
        self.scenario_filename = scenario_filename
        self.scenario_path = get_config_path(scenario_filename)
        self.events: list[ScenarioEvent] = []
        self.loop_scenario = True
        self.elapsed_time = 0.0
        
        # 現在適用中の倍率
        self.current_price_multiplier = 1.0
        self.current_load_multiplier = 1.0
        self.current_hydro_multiplier = 1.0
        
        # UI表示用メッセージ
        self.active_banner_msg = ""
        self.banner_timer = 0.0
        self.banner_color = 7 # 白
        self.notice_sound_trigger = False
        self.event_sound_trigger = False
        
        self.load_scenario()

    def load_scenario(self):
        if not os.path.exists(self.scenario_path):
            print(f"Warning: {self.scenario_path} not found. Using defaults.")
            return

        with open(self.scenario_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.loop_scenario = data.get("loop_scenario", True)
        self.events = [ScenarioEvent(item) for item in data.get("events", [])]
        # 時間順にソート
        self.events.sort(key=lambda e: e.trigger_time)

    def reset(self):
        self.elapsed_time = 0.0
        self.current_price_multiplier = 1.0
        self.current_load_multiplier = 1.0
        self.current_hydro_multiplier = 1.0
        self.active_banner_msg = ""
        self.banner_timer = 0.0
        for ev in self.events:
            ev.reset()

    def update(self, dt: float):
        self.elapsed_time += dt
        self.notice_sound_trigger = False
        self.event_sound_trigger = False
        
        if self.banner_timer > 0:
            self.banner_timer -= dt
            if self.banner_timer <= 0:
                self.active_banner_msg = ""

        # 倍率のリセット（デフォルト 1.0）
        active_event: ScenarioEvent | None = None

        for ev in self.events:
            notice_start = ev.trigger_time - ev.notice_time
            # 予告判定
            if not ev.noticed and self.elapsed_time >= notice_start and self.elapsed_time < ev.trigger_time:
                ev.noticed = True
                self.active_banner_msg = ev.notice_msg
                self.banner_timer = ev.notice_time
                self.banner_color = 10 # 黄色
                self.notice_sound_trigger = True

            # イベント発生判定
            if self.elapsed_time >= ev.trigger_time and self.elapsed_time < ev.trigger_time + ev.duration:
                if not ev.started:
                    ev.started = True
                    self.active_banner_msg = ev.active_msg
                    self.banner_timer = 6.0
                    self.banner_color = 8 # 赤/マゼンタ (単価高) または 11 (単価安)
                    if ev.price_multiplier < 1.0:
                        self.banner_color = 12 # シアン/水色 (余剰)
                    self.event_sound_trigger = True
                active_event = ev
                break

            # 終了判定
            if ev.started and not ev.finished and self.elapsed_time >= ev.trigger_time + ev.duration:
                ev.finished = True
                self.active_banner_msg = f"【終了】{ev.name} が終了し、需給が通常状態に戻りました。"
                self.banner_timer = 4.0
                self.banner_color = 7

        if active_event:
            self.current_price_multiplier = active_event.price_multiplier
            self.current_load_multiplier = active_event.load_multiplier
            self.current_hydro_multiplier = active_event.hydro_multiplier
        else:
            self.current_price_multiplier = 1.0
            self.current_load_multiplier = 1.0
            self.current_hydro_multiplier = 1.0

        # 全イベント終了時のループ処理
        if self.loop_scenario and self.events:
            last_end = max(e.trigger_time + e.duration for e in self.events)
            if self.elapsed_time > last_end + 10.0:
                self.elapsed_time = 0.0
                for ev in self.events:
                    ev.reset()
