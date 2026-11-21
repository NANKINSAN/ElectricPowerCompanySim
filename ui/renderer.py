"""
描画レンダラー
HUD、周波数メーター、電力網マップ、送電線潮流アニメーション、下部操作パネル
"""
import pyxel
import math
import os
from utils.resource import get_resource_path

class GameRenderer:
    def __init__(self, font_path: str = "assets/umplus_j10r.bdf"):
        self.font = None
        resolved_path = get_resource_path(font_path)
        if os.path.exists(resolved_path):
            try:
                self.font = pyxel.Font(resolved_path)
            except Exception as e:
                print(f"Failed to load font from {resolved_path}: {e}")

    def draw_text(self, x: int, y: int, text: str, col: int = 7, line_spacing: int = 11):
        """改行コード(\\n)に対応したテキスト描画"""
        lines = str(text).split("\n")
        for i, line in enumerate(lines):
            if self.font:
                pyxel.text(x, y + i * line_spacing, line, col, self.font)
            else:
                pyxel.text(x, y + i * line_spacing, line, col)

    def draw_hud(self, sim_state: dict):
        # 上部HUD背景
        pyxel.rect(0, 0, 320, 36, 1)
        pyxel.line(0, 36, 320, 36, 5)

        # 1. 資金・スコア・単価（全角20文字程度に収まるコンパクト配置）
        time_str = f"時間:{int(sim_state['elapsed_time'])}s"
        money_str = f"資金:¥{int(sim_state['money']):,}"
        score_str = f"スコア:¥{int(sim_state['score']):,}"
        self.draw_text(4, 3, time_str, 7)
        self.draw_text(65, 3, money_str, 11)
        self.draw_text(165, 3, score_str, 10)

        # 単価と係数
        coeff = sim_state['price_multiplier']
        price = sim_state['current_price']
        coeff_col = 8 if coeff > 1.05 else (12 if coeff < 0.95 else 7)
        self.draw_text(4, 14, f"単価:¥{price:.1f}/kWh(x{coeff:.2f})", coeff_col)

        # 需給サマリー
        p_gen = sim_state['total_gen_mw']
        p_load = sim_state['total_load_mw']
        diff = p_gen - p_load
        diff_str = f"+{diff:.1f}" if diff >= 0 else f"{diff:.1f}"
        self.draw_text(165, 14, f"供給:{p_gen:.0f}MW/需要:{p_load:.0f}MW ({diff_str})", 7)

        # 2. 周波数メーター (x: 4 ~ 220, y: 25 ~ 34)
        self._draw_frequency_meter(sim_state)

        # 3. 難易度表示
        diff_name = sim_state.get('difficulty_name', '通常')
        self.draw_text(262, 26, f"[{diff_name}]", 6)

        # 4. イベント・バナー表示（メッセージがあるときのみ上部に2行表示）
        banner = sim_state.get('banner_msg', '')
        if banner:
            b_col = sim_state.get('banner_color', 7)
            # 点滅背景
            if pyxel.frame_count % 10 < 8:
                lines = banner.split("\n")
                b_h = 13 if len(lines) <= 1 else 23
                pyxel.rect(0, 37, 320, b_h, 0)
                pyxel.rectb(0, 37, 320, b_h, b_col)
                self.draw_text(8, 39, banner, b_col, line_spacing=11)

    def _draw_frequency_meter(self, sim_state: dict):
        freq = sim_state['frequency']
        rated = sim_state['rated_freq']
        tol = sim_state['freq_tolerance']
        is_violating = sim_state['is_violating']
        is_critical = sim_state['is_critical']
        violation_ratio = sim_state['violation_ratio']

        # メーター枠
        mx, my, mw, mh = 4, 25, 130, 9
        pyxel.rect(mx, my, mw, mh, 0)
        pyxel.rectb(mx, my, mw, mh, 5)

        # 正常許容ゾーン（緑色の帯）
        span = 3.0
        center_x = mx + mw // 2
        px_per_hz = mw / span

        tol_left = int(center_x - tol * px_per_hz)
        tol_right = int(center_x + tol * px_per_hz)
        pyxel.rect(max(mx + 1, tol_left), my + 1, min(mw - 2, tol_right - tol_left), mh - 2, 3)

        # 60Hz 基準ライン (白)
        pyxel.line(center_x, my, center_x, my + mh - 1, 7)

        # 現在の周波数の針
        needle_x = int(center_x + (freq - rated) * px_per_hz)
        needle_x = max(mx + 1, min(mx + mw - 2, needle_x))

        needle_col = 8 if is_violating else 10
        pyxel.line(needle_x, my - 1, needle_x, my + mh, needle_col)
        pyxel.pset(needle_x - 1, my, needle_col)
        pyxel.pset(needle_x + 1, my, needle_col)

        # 周波数数値
        freq_str = f"{freq:.2f}Hz"
        f_col = 8 if is_violating else (11 if abs(freq - rated) < 0.1 else 7)
        self.draw_text(mx + mw + 4, my, freq_str, f_col)

        # 警報ランプ & 危機ゲージ
        lamp_x = mx + mw + 48
        if is_violating:
            blink = (pyxel.frame_count // 6) % 2 == 0
            lamp_col = 8 if (blink or is_critical) else 0
            pyxel.circ(lamp_x + 4, my + 4, 4, lamp_col)
            pyxel.circb(lamp_x + 4, my + 4, 4, 7)
            self.draw_text(lamp_x + 11, my, "周波数異常!", 8)

            gw = 32
            pyxel.rect(lamp_x + 64, my + 1, gw, mh - 2, 0)
            pyxel.rectb(lamp_x + 64, my + 1, gw, mh - 2, 8)
            fill_w = int(gw * violation_ratio)
            pyxel.rect(lamp_x + 64, my + 1, fill_w, mh - 2, 8)
        else:
            pyxel.circ(lamp_x + 4, my + 4, 3, 11)
            pyxel.circb(lamp_x + 4, my + 4, 3, 3)

    def draw_map(self, plants: list, consumers: list, grid_lines: list, selected_obj, hovered_obj):
        # 背景：薄いグリッド地形
        pyxel.rect(0, 48, 320, 134, 0)

        # 地形の飾り（川の流れ）
        self._draw_river()

        # 送電線と潮流を描画
        self._draw_power_lines(grid_lines)

        # 中央変電所
        sub_x, sub_y = 130, 115
        pyxel.rect(sub_x - 8, sub_y - 8, 16, 16, 5)
        pyxel.rectb(sub_x - 8, sub_y - 8, 16, 16, 6)
        pyxel.pset(sub_x, sub_y, 7)
        self.draw_text(sub_x - 18, sub_y + 9, "中央変電所", 6)

        # 発電所を描画
        for p in plants:
            self._draw_plant(p, is_selected=(selected_obj == p), is_hovered=(hovered_obj == p))

        # 需要家を描画
        for c in consumers:
            self._draw_consumer(c, is_selected=(selected_obj == c), is_hovered=(hovered_obj == c))

    def _draw_river(self):
        points = [(10, 48), (25, 75), (45, 100), (60, 125), (70, 150), (75, 180)]
        for i in range(len(points) - 1):
            p1 = points[i]
            p2 = points[i+1]
            for w in range(-3, 4):
                pyxel.line(p1[0] + w, p1[1], p2[0] + w, p2[1], 1)
            if (pyxel.frame_count + i * 5) % 20 < 10:
                pyxel.pset(p1[0], p1[1] + 5, 12)

    def _draw_power_lines(self, lines: list):
        for line in lines:
            col = 5  # 非通電時は暗いグレー
            flow = line.flow_mw
            abs_flow = abs(flow)

            if abs_flow > 0.1:
                ratio = abs_flow / max(1.0, line.capacity_mw)
                if flow < 0:
                    # 揚水時（逆流時）は水色/シアンで強調
                    col = 12 if ratio < 0.8 else 8
                else:
                    if ratio > 0.9:
                        col = 8  # 過負荷・赤
                    elif ratio > 0.6:
                        col = 9  # 橙
                    elif ratio > 0.3:
                        col = 10 # 黄
                    else:
                        col = 11 # 水色/緑

            pyxel.line(line.x1, line.y1, line.x2, line.y2, col)

            # 潮流粒子のパルスアニメーション
            if abs_flow > 0.5:
                dx = line.x2 - line.x1
                dy = line.y2 - line.y1
                dist = math.hypot(dx, dy)
                if dist > 0:
                    spacing = 14.0
                    count = max(1, int(dist / spacing))
                    for i in range(count):
                        # line.anim_offset が正なら A -> B へ移動
                        # line.anim_offset が負なら B -> A へ逆流移動（素早く吸い込まれる）
                        pos = (i * spacing + line.anim_offset) % dist
                        t = pos / dist
                        px = int(line.x1 + dx * t)
                        py = int(line.y1 + dy * t)

                        # 逆流時は水色(12)、通常は白(7)
                        particle_col = 12 if flow < 0 else 7
                        pyxel.pset(px, py, particle_col)

                        # 勢いのある潮流（大電力）のときは光跡をつけて速度感を強調
                        if abs_flow > 25.0:
                            dir_mult = 1.0 if flow > 0 else -1.0
                            tail_x = int(px - (dx / dist) * dir_mult * 2.0)
                            tail_y = int(py - (dy / dist) * dir_mult * 2.0)
                            pyxel.pset(tail_x, tail_y, 6)

    def _draw_plant(self, p, is_selected: bool, is_hovered: bool):
        x, y = p.x, p.y
        w, h = 24, 20

        if is_selected:
            pyxel.rectb(x - 2, y - 2, w + 4, h + 4, 10)
        elif is_hovered:
            pyxel.rectb(x - 1, y - 1, w + 2, h + 2, 7)

        if p.plant_type == "thermal":
            pyxel.rect(x, y + 6, w, h - 6, 4)
            pyxel.rect(x + 4, y, 4, 6, 9)
            if p.get_output_mw() > 5.0 and pyxel.frame_count % 12 < 8:
                pyxel.circ(x + 5 + (pyxel.frame_count % 4), y - 3 - (pyxel.frame_count % 3), 2, 7)
            self.draw_text(x - 4, y + h + 2, f"{p.name[:4]}", 7)
            self.draw_text(x - 4, y + h + 11, f"{p.current_output_mw:.0f}MW", 10)

        elif p.plant_type == "hydro":
            pyxel.rect(x, y + 4, w, h - 4, 1)
            pyxel.rectb(x, y + 4, w, h - 4, 12)
            pyxel.line(x + 4, y + 8, x + w - 4, y + 8, 7)
            self.draw_text(x - 4, y + h + 2, f"{p.name[:4]}", 7)
            self.draw_text(x - 4, y + h + 11, f"{p.current_output_mw:.0f}MW", 11)

        elif p.plant_type == "pumped_storage":
            mode_col = 10 if p.mode == "GEN" else (12 if p.mode == "PUMP" else 5)
            pyxel.rect(x, y, w, h, 2)
            pyxel.rectb(x, y, w, h, mode_col)

            ratio = p.storage_mwh / max(1.0, p.max_storage_mwh)
            bar_h = int((h - 4) * ratio)
            pyxel.rect(x + 2, y + h - 2 - bar_h, 4, bar_h, 12)

            m_text = "GEN" if p.mode == "GEN" else ("PUMP" if p.mode == "PUMP" else "OFF")
            pyxel.text(x + 8, y + 4, m_text, mode_col)
            
            self.draw_text(x - 4, y + h + 2, f"揚水", 7)
            if p.mode == "GEN":
                self.draw_text(x - 4, y + h + 11, f"+{p.current_output_mw:.0f}MW", 10)
            elif p.mode == "PUMP":
                self.draw_text(x - 4, y + h + 11, f"-{p.current_pump_load_mw:.0f}MW", 12)
            else:
                self.draw_text(x - 4, y + h + 11, "0MW", 5)

    def _draw_consumer(self, c, is_selected: bool, is_hovered: bool):
        x, y = c.x, c.y
        w, h = 20, 16

        if is_selected:
            pyxel.rectb(x - 2, y - 2, w + 4, h + 4, 10)
        elif is_hovered:
            pyxel.rectb(x - 1, y - 1, w + 2, h + 2, 7)

        if c.consumer_type == "residential":
            roof_col = 8 if c.is_connected else 5
            pyxel.tri(x, y + 6, x + w // 2, y, x + w, y + 6, roof_col)
            pyxel.rect(x + 2, y + 6, w - 4, h - 6, 9 if c.is_connected else 1)
            if c.is_connected:
                pyxel.rect(x + 5, y + 8, 3, 3, 10)
                pyxel.rect(x + 12, y + 8, 3, 3, 10)
            self.draw_text(x - 6, y + h + 2, f"{c.name[:4]}", 7)
            self.draw_text(x - 4, y + h + 11, f"{c.current_load_mw:.0f}MW" if c.is_connected else "停電", 8 if not c.is_connected else 10)

        elif c.consumer_type == "factory":
            fac_col = 6 if c.is_connected else 5
            pyxel.rect(x, y + 4, w, h - 4, fac_col)
            pyxel.tri(x, y + 4, x + 5, y, x + 10, y + 4, 5)
            pyxel.tri(x + 10, y + 4, x + 15, y, x + 20, y + 4, 5)
            if c.is_connected and pyxel.frame_count % 8 < 5:
                pyxel.pset(x + 4, y + 8, 10)
                pyxel.pset(x + 14, y + 8, 11)
            self.draw_text(x - 6, y + h + 2, f"{c.name[:4]}", 7)
            self.draw_text(x - 4, y + h + 11, f"{c.current_load_mw:.0f}MW" if c.is_connected else "停止", 8 if not c.is_connected else 10)

    def draw_inspector_and_controls(self, selected_obj, buttons: dict, plants: list, lines: list, mx: int, my: int):
        panel_y = 182
        pyxel.rect(0, panel_y, 320, 58, 1)
        pyxel.line(0, panel_y, 320, panel_y, 6)

        # 1. 選択中オブジェクトの情報 & コントロール
        if selected_obj is not None:
            self._draw_object_controls(selected_obj, buttons, panel_y)
        else:
            self.draw_text(6, panel_y + 4, "設備をクリックして選択・操作", 7)
            px = 6
            for p in plants:
                out_str = f"{p.name[:4]}:{p.get_output_mw():.0f}MW"
                self.draw_text(px, panel_y + 16, out_str, 10)
                px += 75

        # 2. 設備新設（購入）ボタン
        self.draw_text(184, panel_y + 27, "【新設】", 7)
        if "btn_buy_thermal" in buttons:
            buttons["btn_buy_thermal"].draw()
        if "btn_buy_hydro" in buttons:
            buttons["btn_buy_hydro"].draw()
        if "btn_buy_pumped" in buttons:
            buttons["btn_buy_pumped"].draw()

        # 3. 電線ホバー時の潮流ツールチップ
        self._draw_line_tooltip(lines, mx, my)

    def _draw_object_controls(self, obj, buttons: dict, panel_y: int):
        title = f"【選択: {obj.name}】"
        self.draw_text(6, panel_y + 4, title, 10)

        # 火力発電所の場合
        if hasattr(obj, "plant_type") and obj.plant_type == "thermal":
            info_str = f"出力:{obj.current_output_mw:.1f}MW (目標:{obj.target_output_mw:.0f}MW/定格:{obj.max_output_mw:.0f}MW)"
            self.draw_text(6, panel_y + 15, info_str, 7)
            for k in ["btn_dec10", "btn_dec1", "btn_inc1", "btn_inc10", "btn_min", "btn_max"]:
                if k in buttons:
                    buttons[k].draw()

        # 揚水発電所の場合
        elif hasattr(obj, "plant_type") and obj.plant_type == "pumped_storage":
            storage_str = f"貯水:{obj.storage_mwh:.0f}/{obj.max_storage_mwh:.0f}MWh (残:{int(obj.storage_mwh/obj.max_storage_mwh*100)}%)"
            self.draw_text(6, panel_y + 15, storage_str, 11)
            if "btn_pump_off" in buttons:
                buttons["btn_pump_off"].draw()
            if "btn_pump_gen" in buttons:
                buttons["btn_pump_gen"].draw()
            if "btn_pump_pump" in buttons:
                buttons["btn_pump_pump"].draw()

        # 水力発電所の場合
        elif hasattr(obj, "plant_type") and obj.plant_type == "hydro":
            info_str = f"出力:{obj.current_output_mw:.1f}MW (河川依存・ベースロード)"
            self.draw_text(6, panel_y + 15, info_str, 7)

        # 需要家の場合
        elif hasattr(obj, "consumer_type"):
            stat_str = "送電中(売電中)" if obj.is_connected else "送電停止(停電中)"
            stat_col = 11 if obj.is_connected else 8
            self.draw_text(6, panel_y + 15, f"負荷:{obj.current_load_mw:.1f}MW | {stat_str}", stat_col)
            if "btn_toggle_power" in buttons:
                buttons["btn_toggle_power"].draw()

    def _draw_line_tooltip(self, lines: list, mx: int, my: int):
        for line in lines:
            dist = self._point_to_line_dist(mx, my, line.x1, line.y1, line.x2, line.y2)
            if dist < 4.0:
                short_name = line.name.replace("中央変電所", "変電所")
                tip = f"{short_name}: {abs(line.flow_mw):.1f}/{line.capacity_mw:.0f}MW"
                tw = len(tip) * 5 + 8
                tx = min(320 - tw - 4, max(4, mx + 8))
                ty = max(40, my - 14)
                pyxel.rect(tx, ty, tw, 12, 0)
                pyxel.rectb(tx, ty, tw, 12, 7)
                self.draw_text(tx + 4, ty + 2, tip, 10)
                break

    def _point_to_line_dist(self, px, py, x1, y1, x2, y2):
        dx = x2 - x1
        dy = y2 - y1
        l2 = dx*dx + dy*dy
        if l2 == 0:
            return math.hypot(px - x1, py - y1)
        t = max(0, min(1, ((px - x1)*dx + (py - y1)*dy) / l2))
        proj_x = x1 + t * dx
        proj_y = y1 + t * dy
        return math.hypot(px - proj_x, py - proj_y)

    def draw_game_over(self, score: float, time_sec: float, energy_kwh: float):
        pyxel.rect(50, 48, 220, 144, 0)
        pyxel.rectb(50, 48, 220, 144, 8)
        
        self.draw_text(95, 58, "=== BLACKOUT ===", 8)
        self.draw_text(85, 72, "系統崩壊（大規模停電）", 8)
        
        self.draw_text(65, 92, "周波数の許容範囲逸脱により", 7)
        self.draw_text(65, 104, "電力系統が停止しました", 7)
        
        self.draw_text(65, 122, f"稼働時間  : {int(time_sec)} 秒", 7)
        self.draw_text(65, 136, f"供給電力量: {int(energy_kwh):,} kWh", 7)
        self.draw_text(65, 150, f"最終スコア: ¥{int(score):,}", 10)

        if pyxel.frame_count % 30 < 20:
            self.draw_text(90, 172, "[ R キーで再挑戦 ]", 11)
