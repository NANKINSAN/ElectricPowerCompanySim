"""
需要家モデル（民家・工場）および町の自動発展
"""
import random

class Consumer:
    def __init__(self, consumer_id: str, name: str, consumer_type: str, x: int, y: int, base_load_mw: float, command_cooldown_sec: float = 1.0):
        self.id = consumer_id
        self.name = name
        self.consumer_type = consumer_type  # "residential", "factory"
        self.x = x
        self.y = y
        self.base_load_mw = base_load_mw
        self.current_load_mw = base_load_mw
        
        # プレイヤーが操作可能な送電スイッチ (True=送電中, False=遮断/停電)
        self.is_connected = True
        self.pending_connected = True
        
        # 停電時間（遮断状態の累積時間）
        self.blackout_time_sec = 0.0

        # 操作制限クールダウン
        self.command_cooldown_sec = command_cooldown_sec
        self.cooldown_timer = 0.0

    def can_operate(self) -> bool:
        return self.cooldown_timer <= 0.0

    def toggle_pending_connection(self) -> bool:
        """仮の送電状態を反転"""
        self.pending_connected = not self.pending_connected
        return True

    def commit_connection(self):
        """変電所からの送電線接続・遮断指令を確定"""
        self.is_connected = self.pending_connected

    def commit_command(self) -> bool:
        """指令確定：仮の送電状態を適用しクールダウン開始"""
        if not self.can_operate():
            return False
        self.is_connected = self.pending_connected
        self.cooldown_timer = self.command_cooldown_sec
        return True

    def toggle_connection(self) -> bool:
        self.toggle_pending_connection()
        return self.commit_command()

    def update(self, dt: float, load_multiplier: float = 1.0):
        if self.cooldown_timer > 0.0:
            self.cooldown_timer = max(0.0, self.cooldown_timer - dt)

        if not self.is_connected:
            self.blackout_time_sec += dt
            self.current_load_mw = 0.0
            return

        self.blackout_time_sec = max(0.0, self.blackout_time_sec - dt * 0.5)
        # 自然な負荷揺らぎ (±5% 程度)
        fluctuation = 1.0 + (random.random() - 0.5) * 0.08
        self.current_load_mw = self.base_load_mw * load_multiplier * fluctuation

    def get_load_mw(self) -> float:
        if not self.is_connected:
            return 0.0
        return self.current_load_mw


class TownManager:
    """需要家の管理と町の自動発展ロジック（事前予告＆新設イベント）"""
    def __init__(self, expansion_interval: float = 45.0, notice_time: float = 12.0):
        self.expansion_interval = expansion_interval
        self.notice_time = notice_time
        self.timer = 0.0
        self.consumers: list[Consumer] = []
        self.expansion_count = 0
        
        # 予告・発生メッセージとサウンド
        self.is_noticing = False
        self.notice_sound_trigger = False
        self.expand_sound_trigger = False
        self.banner_msg = ""
        self.banner_color = 10
        self.msg_timer = 0.0

        # 次の新設予定計画
        self.next_expansion: dict | None = None

        # 初期配置
        self._init_starting_town()
        self._plan_next_expansion()

    def _init_starting_town(self):
        self.consumers = [
            Consumer("res_1", "中央区住宅街", "residential", 280, 75, base_load_mw=25.0),
            Consumer("res_2", "東町ニュータウン", "residential", 380, 105, base_load_mw=30.0),
            Consumer("fac_1", "西部工業コンビナート", "factory", 290, 190, base_load_mw=45.0),
        ]

    def _plan_next_expansion(self):
        """次に追加される需要オブジェクトをあらかじめ計画"""
        next_count = self.expansion_count + 1
        cid = f"exp_{next_count}"
        if next_count % 2 == 1:
            name = f"新興住宅街 第{next_count}地区"
            c_type = "residential"
            base_load = 20.0 + random.random() * 15.0
            x = 270 + (next_count * 35) % 140
            y = 65 + (next_count * 25) % 85
        else:
            name = f"ハイテク工場 第{next_count // 2}プラント"
            c_type = "factory"
            base_load = 35.0 + random.random() * 20.0
            x = 300 + (next_count * 30) % 120
            y = 165 + (next_count * 20) % 75

        self.next_expansion = {
            "id": cid,
            "name": name,
            "type": c_type,
            "base_load": base_load,
            "x": x,
            "y": y
        }

    def update(self, dt: float, load_multiplier: float = 1.0):
        for c in self.consumers:
            c.update(dt, load_multiplier)

        self.notice_sound_trigger = False
        self.expand_sound_trigger = False

        if self.msg_timer > 0:
            self.msg_timer -= dt
            if self.msg_timer <= 0:
                self.banner_msg = ""

        # 時間経過による自動発展
        self.timer += dt

        rem_sec = self.expansion_interval - self.timer
        # 1. 予告判定（notice_time 秒前からカウントダウン）
        if 0 < rem_sec <= self.notice_time:
            if not self.is_noticing:
                self.is_noticing = True
                self.notice_sound_trigger = True

            if self.next_expansion:
                sec_disp = max(1, int(rem_sec + 0.9))
                n = self.next_expansion
                kind_str = "住宅街" if n["type"] == "residential" else "工場"
                self.banner_msg = f"【需要追加予告】あと{sec_disp}秒で送電網に接続されます！\n対象: {n['name']} ({kind_str}, 想定負荷: 約{n['base_load']:.0f}MW)"
                self.banner_color = 10 # 黄色

        # 2. 新設イベント発生（グリッド接続）
        if self.timer >= self.expansion_interval:
            self.timer = 0.0
            self.is_noticing = False
            self._expand_town()
            self._plan_next_expansion()

    def _expand_town(self):
        if not self.next_expansion:
            return
        self.expansion_count += 1
        n = self.next_expansion
        new_consumer = Consumer(n["id"], n["name"], n["type"], n["x"], n["y"], n["base_load"])
        self.consumers.append(new_consumer)
        self.expand_sound_trigger = True
        self.banner_msg = f"【需要追加】「{n['name']}」(負荷:{n['base_load']:.0f}MW) が接続されました！\n発電所出力を調整して周波数の急低下を防いでください！"
        self.banner_color = 9 # オレンジ
        self.msg_timer = 7.0

    def get_total_load_mw(self) -> float:
        return sum(c.get_load_mw() for c in self.consumers)
