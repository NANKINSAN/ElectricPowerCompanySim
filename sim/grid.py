"""
送電網（グリッド）および電力潮流モデル
発電所、中央変電所、需要家を接続する電線オブジェクトと潮流計算
"""
import math

class PowerLine:
    def __init__(self, line_id: str, name: str, node_a: tuple[int, int], node_b: tuple[int, int],
                 capacity_mw: float = 120.0, obj_a_id: str = "", obj_b_id: str = ""):
        self.id = line_id
        self.name = name
        self.x1, self.y1 = node_a
        self.x2, self.y2 = node_b
        self.obj_a_id = obj_a_id
        self.obj_b_id = obj_b_id
        self.capacity_mw = capacity_mw
        self.flow_mw = 0.0          # 潮流 (正: A->B, 負: B->A)
        self.is_connected = True
        self.anim_offset = 0.0      # 粒子アニメーション累積距離

    def update_anim(self, dt: float):
        if not self.is_connected:
            return
        # 潮流（MW）に応じた速度で移動（1MWあたり1.2px/秒）
        # 正なら A->B へ、負なら B->A へ高速移動
        speed = self.flow_mw * 1.2
        self.anim_offset += speed * dt


class GridNetwork:
    """電力系統ネットワーク全体のトポロジーと潮流計算"""
    def __init__(self):
        # 中央ハブ（変電所）座標
        self.substation_pos = (130, 115)
        self.substation_name = "中央変電所 (Central Hub)"
        self.lines: list[PowerLine] = []

    def build_network(self, plants: list, consumers: list):
        """発電所と需要家を中央ハブに接続するネットワークを構築"""
        self.lines.clear()
        
        # 1. 各発電所から中央変電所への幹線
        for p in plants:
            line_id = f"line_plant_{p.id}"
            line_name = f"{p.name} - 中央変電所"
            # 発電所の位置から変電所へ
            line = PowerLine(
                line_id=line_id,
                name=line_name,
                node_a=(p.x + 12, p.y + 12),
                node_b=self.substation_pos,
                capacity_mw=max(100.0, p.max_output_mw * 1.3),
                obj_a_id=p.id,
                obj_b_id="substation"
            )
            self.lines.append(line)

        # 2. 中央変電所から各需要家への配電線
        for c in consumers:
            line_id = f"line_cons_{c.id}"
            line_name = f"中央変電所 - {c.name}"
            line = PowerLine(
                line_id=line_id,
                name=line_name,
                node_a=self.substation_pos,
                node_b=(c.x + 8, c.y + 8),
                capacity_mw=max(60.0, c.base_load_mw * 2.0),
                obj_a_id="substation",
                obj_b_id=c.id
            )
            self.lines.append(line)

    def update_flows(self, plants_dict: dict, consumers_dict: dict, dt: float):
        """各電線の潮流を計算"""
        # 発電所から変電所への流入潮流
        # 揚水がPUMPの場合は変電所から発電所へ逆流（負の潮流）
        for line in self.lines:
            if line.obj_b_id == "substation" and line.obj_a_id in plants_dict:
                plant = plants_dict[line.obj_a_id]
                if not plant.connected or not plant.is_active:
                    line.flow_mw = 0.0
                elif plant.plant_type == "pumped_storage" and plant.mode == "PUMP":
                    # 変電所から揚水所へ電力消費（逆向き潮流）
                    line.flow_mw = -plant.get_load_mw()
                else:
                    line.flow_mw = plant.get_output_mw()

            elif line.obj_a_id == "substation" and line.obj_b_id in consumers_dict:
                consumer = consumers_dict[line.obj_b_id]
                if consumer.is_connected:
                    line.flow_mw = consumer.get_load_mw()
                else:
                    line.flow_mw = 0.0

            line.update_anim(dt)
