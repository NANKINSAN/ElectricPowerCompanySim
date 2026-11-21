"""
需要家モデル（民家・工場）および町の自動発展
"""
import random

class Consumer:
    def __init__(self, consumer_id: str, name: str, consumer_type: str, x: int, y: int, base_load_mw: float):
        self.id = consumer_id
        self.name = name
        self.consumer_type = consumer_type  # "residential", "factory"
        self.x = x
        self.y = y
        self.base_load_mw = base_load_mw
        self.current_load_mw = base_load_mw
        
        # プレイヤーが操作可能な送電スイッチ (True=送電中, False=遮断/停電)
        self.is_connected = True
        
        # 停電時間（遮断状態の累積時間）
        self.blackout_time_sec = 0.0

    def toggle_connection(self):
        self.is_connected = not self.is_connected

    def update(self, dt: float, load_multiplier: float = 1.0):
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
    """需要家の管理と町の自動発展ロジック"""
    def __init__(self, expansion_interval: float = 45.0):
        self.expansion_interval = expansion_interval
        self.timer = 0.0
        self.consumers: list[Consumer] = []
        self.expansion_count = 0
        self.latest_expansion_msg = ""
        self.msg_timer = 0.0

        # 初期配置
        self._init_starting_town()

    def _init_starting_town(self):
        self.consumers = [
            Consumer("res_1", "中央区住宅街", "residential", 170, 75, base_load_mw=25.0),
            Consumer("res_2", "東町ニュータウン", "residential", 230, 95, base_load_mw=30.0),
            Consumer("fac_1", "西部工業コンビナート", "factory", 185, 155, base_load_mw=45.0),
        ]

    def update(self, dt: float, load_multiplier: float = 1.0):
        for c in self.consumers:
            c.update(dt, load_multiplier)

        # 時間経過による自動発展
        self.timer += dt
        if self.timer >= self.expansion_interval:
            self.timer = 0.0
            self._expand_town()

        if self.msg_timer > 0:
            self.msg_timer -= dt

    def _expand_town(self):
        self.expansion_count += 1
        cid = f"exp_{self.expansion_count}"
        
        # 住宅地または工場の追加（位置は空いているグリッド座標）
        if self.expansion_count % 2 == 1:
            name = f"新興住宅街 第{self.expansion_count}地区"
            c_type = "residential"
            base_load = 20.0 + random.random() * 15.0
            # マップ上の配置位置
            x = 140 + (self.expansion_count * 25) % 110
            y = 110 + (self.expansion_count * 18) % 60
        else:
            name = f"ハイテク工場 第{self.expansion_count // 2}プラント"
            c_type = "factory"
            base_load = 35.0 + random.random() * 20.0
            x = 220 + (self.expansion_count * 15) % 65
            y = 160 + (self.expansion_count * 20) % 50

        new_consumer = Consumer(cid, name, c_type, x, y, base_load)
        self.consumers.append(new_consumer)
        self.latest_expansion_msg = f"【街の発展】{name}\n負荷:{base_load:.0f}MW がグリッドに新設！"
        self.msg_timer = 5.0

    def get_total_load_mw(self) -> float:
        return sum(c.get_load_mw() for c in self.consumers)
