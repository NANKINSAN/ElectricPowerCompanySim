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

    def draw_text(self, x: int, y: int, text: str, col: int = 7, line_spacing: int = 11, max_width: int = 460):
        """改行コード(\\n)および最大幅での自動折り返しに対応したテキスト描画"""
        raw_lines = str(text).split("\n")
        lines = []
        # 各行の幅チェックと折り返し
        for r_line in raw_lines:
            curr = ""
            curr_w = 0
            for ch in r_line:
                w = 10 if ord(ch) >= 128 else 5
                if curr_w + w > max_width and curr:
                    lines.append(curr)
                    curr = ch
                    curr_w = w
                else:
                    curr += ch
                    curr_w += w
            if curr:
                lines.append(curr)

        for i, line in enumerate(lines):
            if self.font:
                pyxel.text(x, y + i * line_spacing, line, col, self.font)
            else:
                pyxel.text(x, y + i * line_spacing, line, col)

    def draw_hud(self, sim_state: dict):
        # 上部HUD背景 (幅480, 高さ42)
        pyxel.rect(0, 0, 480, 42, 1)
        pyxel.line(0, 42, 480, 42, 5)

        # 1. 時間・資金・スコア・難易度
        time_str = f"経過時間:{int(sim_state['elapsed_time'])}s"
        money_str = f"所持資金:¥{int(sim_state['money']):,}"
        score_str = f"売電スコア:¥{int(sim_state['score']):,}"
        diff_name = sim_state.get('difficulty_name', '通常')

        self.draw_text(8, 4, time_str, 7)

        # 時間進行中 / 時間停止中インジケータ
        is_paused = sim_state.get('is_paused', False)
        if is_paused:
            p_col = 9 if pyxel.frame_count % 16 < 10 else 10
            self.draw_text(76, 4, "[⏸停止]", p_col)
        else:
            r_col = 11 if pyxel.frame_count % 20 < 12 else 3
            self.draw_text(76, 4, "[▶稼働]", r_col)

        self.draw_text(118, 4, money_str, 11)
        self.draw_text(240, 4, score_str, 10)
        self.draw_text(395, 4, f"[{diff_name}]", 6)

        # 2. 単価と係数 / 需給サマリー
        coeff = sim_state['price_multiplier']
        price = sim_state['current_price']
        coeff_col = 8 if coeff > 1.05 else (12 if coeff < 0.95 else 7)
        self.draw_text(8, 16, f"市場単価:¥{price:.1f}/kWh (x{coeff:.2f})", coeff_col)

        p_gen = sim_state['total_gen_mw']
        p_load = sim_state['total_load_mw']
        diff = p_gen - p_load
        diff_str = f"+{diff:.1f}" if diff >= 0 else f"{diff:.1f}"
        self.draw_text(240, 16, f"総発電:{p_gen:.0f}MW / 総需要:{p_load:.0f}MW ({diff_str}MW)", 7)

        # 3. 周波数メーター & 状態表示 (y: 28 ~ 38)
        self._draw_frequency_meter(sim_state)

        # 4. イベント・バナー表示（発電所と重ならないよう1行固定バー: y=42〜55）
        banner = sim_state.get('banner_msg', '')
        bar_y = 42
        bar_h = 13
        is_hovered = (0 <= pyxel.mouse_x <= 480 and bar_y <= pyxel.mouse_y <= bar_y + bar_h)

        if banner:
            b_col = sim_state.get('banner_color', 7)
            # 1行用に最初の行または要約テキストを抽出
            first_line = banner.replace("\n", " | ")
            # 背景・枠線・左端バー
            pyxel.rect(0, bar_y, 480, bar_h, 0)
            pyxel.rectb(0, bar_y, 480, bar_h, 7 if is_hovered else b_col)
            pyxel.rect(0, bar_y, 4, bar_h, b_col)
            self.draw_text(8, bar_y + 2, first_line, b_col, max_width=370)
        elif is_paused:
            pyxel.rect(0, bar_y, 480, bar_h, 0)
            pyxel.rectb(0, bar_y, 480, bar_h, 7 if is_hovered else 9)
            pyxel.rect(0, bar_y, 4, bar_h, 9)
            self.draw_text(8, bar_y + 2, "⏸ 時間停止中 : 設備クリックで指令 / 空き地・右クリックで時間再開", 10, max_width=370)
        else:
            # 通常稼働時
            pyxel.rect(0, bar_y, 480, bar_h, 0)
            pyxel.rectb(0, bar_y, 480, bar_h, 7 if is_hovered else 5)
            pyxel.rect(0, bar_y, 4, bar_h, 3)
            self.draw_text(8, bar_y + 2, "系統正常運転中 (60.00Hz) - 空き地クリックで時間一時停止", 6, max_width=370)

        # 右端の [履歴ログ ▶] ボタン表示
        btn_log_col = 11 if is_hovered else 10
        pyxel.rect(384, bar_y + 1, 94, bar_h - 2, 1)
        pyxel.rectb(384, bar_y + 1, 94, bar_h - 2, btn_log_col)
        self.draw_text(388, bar_y + 2, "[履歴ログ (Click)▶]", btn_log_col)

    def _draw_frequency_meter(self, sim_state: dict):
        freq = sim_state['frequency']
        rated = sim_state['rated_freq']
        tol = sim_state['freq_tolerance']
        is_violating = sim_state['is_violating']
        is_critical = sim_state['is_critical']
        violation_ratio = sim_state['violation_ratio']

        # メーター枠
        mx, my, mw, mh = 8, 28, 160, 10
        pyxel.rect(mx, my, mw, mh, 0)

        # 異常時は外枠を赤色点滅（危険度に応じて点滅速度を短縮）
        if is_violating:
            blink_period = max(4, int(18 - 14 * violation_ratio))
            is_red_phase = (pyxel.frame_count % blink_period) < (blink_period // 2)
            border_col = 8 if is_red_phase else 7
            pyxel.rectb(mx, my, mw, mh, border_col)
            pyxel.rectb(mx - 1, my - 1, mw + 2, mh + 2, 8 if is_red_phase else 0)
        else:
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

        # 周波数数値表示（スッキリ配置）
        freq_str = f"{freq:.2f}Hz"
        f_col = 8 if is_violating else (11 if abs(freq - rated) < 0.1 else 7)
        self.draw_text(mx + mw + 8, my, freq_str, f_col)

        if is_violating:
            blink_period = max(4, int(18 - 14 * violation_ratio))
            is_red = (pyxel.frame_count % blink_period) < (blink_period // 2)
            self.draw_text(mx + mw + 56, my, "⚠ 周波数異常!", 8 if is_red else 7)
        else:
            self.draw_text(mx + mw + 56, my, "(基準 60.00Hz)", 6)

    def draw_frequency_alarm_overlay(self, violation_ratio: float, is_critical: bool):
        """周波数異常時に画面の周りの外枠を赤色点滅させ、点滅間隔を短くして危機感を演出"""
        # 危険度（violation_ratio: 0.0〜1.0）に応じて点滅周期を18フレームから4フレームまで短縮
        period = max(4, int(18 - 14 * violation_ratio))
        is_red_phase = (pyxel.frame_count % period) < (period // 2)

        if not is_red_phase:
            return

        # 画面の周りの外枠だけを赤色で点滅（画面中央の視認性を損なわずに警戒通知）
        # 危険度に応じて枠の太さを 2px 〜 4px に変化
        thickness = 2
        if violation_ratio > 0.35 or is_critical:
            thickness = 3
        if violation_ratio > 0.70 or is_critical:
            thickness = 4

        for i in range(thickness):
            pyxel.rectb(i, i, 480 - i * 2, 360 - i * 2, 8)

    def draw_map(self, plants: list, consumers: list, grid_lines: list, selected_obj, hovered_obj, next_expansion=None, substation=None):
        # 背景：薄いグリッド地形 (480x226)
        pyxel.rect(0, 42, 480, 226, 0)

        # 地形の飾り（川の流れ）
        self._draw_river()

        # 送電線と潮流を描画
        self._draw_power_lines(grid_lines)

        # 中央変電所
        sub_x = substation.x if substation else 200
        sub_y = substation.y if substation else 150
        is_sub_conn = substation.is_connected if substation else True
        is_sub_sel = (selected_obj == substation) if substation else False
        is_sub_hov = (hovered_obj == substation) if substation else False

        # 選択時の点滅太枠 (26x26)
        if is_sub_sel:
            sel_col = 10 if (pyxel.frame_count % 8 < 5) else 7
            pyxel.rectb(sub_x - 13, sub_y - 13, 26, 26, sel_col)
            pyxel.rectb(sub_x - 12, sub_y - 12, 24, 24, sel_col)

        # 変電所本体ボックス (20x20)
        bg_col = 1 if is_sub_conn else 0
        border_col = 10 if is_sub_sel else (7 if is_sub_hov else (6 if is_sub_conn else 8))
        pyxel.rect(sub_x - 10, sub_y - 10, 20, 20, bg_col)
        pyxel.rectb(sub_x - 10, sub_y - 10, 20, 20, border_col)

        # 変電所マーク（碍子・シンボル）
        if is_sub_conn:
            pyxel.circb(sub_x - 4, sub_y, 4, 11)
            pyxel.circb(sub_x + 4, sub_y, 4, 12)
            pyxel.pset(sub_x, sub_y, 7)
            label_col = 11 if is_sub_sel else 6
            label_txt = "中央変電所 [送受電中]"
        else:
            # 停止時：赤色バツ印
            pyxel.line(sub_x - 5, sub_y - 5, sub_x + 5, sub_y + 5, 8)
            pyxel.line(sub_x - 5, sub_y + 5, sub_x + 5, sub_y - 5, 8)
            label_col = 8
            label_txt = "中央変電所 [⚠送受電停止]"

        self.draw_text(sub_x - 42, sub_y + 13, label_txt, label_col)

        # 発電所を描画
        for p in plants:
            self._draw_plant(p, is_selected=(selected_obj == p), is_hovered=(hovered_obj == p))

        # 需要家を描画
        for c in consumers:
            self._draw_consumer(c, is_selected=(selected_obj == c), is_hovered=(hovered_obj == c))

        # 新設予定の需要オブジェクトの予告マーカー（事前予告中のみ表示）
        if next_expansion:
            nx, ny = next_expansion["x"], next_expansion["y"]
            n_name = next_expansion["name"]
            n_load = next_expansion["base_load"]
            # 点滅枠線
            if pyxel.frame_count % 12 < 8:
                pyxel.rectb(nx - 2, ny - 2, 24, 20, 10)
                pyxel.line(nx - 2, ny - 2, nx + 22, ny + 18, 9)
            self.draw_text(nx - 14, ny - 10, "【建設予定地】", 10)
            self.draw_text(nx - 8, ny + 22, f"{n_name}", 7)
            self.draw_text(nx - 4, ny + 33, f"約{n_load:.0f}MW", 10)

    def _draw_river(self):
        points = [(20, 42), (45, 85), (75, 135), (95, 185), (105, 230), (115, 268)]
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

        # 建設中（工事現場）の描画
        if getattr(p, "is_under_construction", False):
            # 工事用足場・フレーム
            pyxel.rect(x, y, w, h, 0)
            pyxel.rectb(x, y, w, h, 9)
            # 黄黒の建設ストライプ模様
            for i in range(0, w, 6):
                pyxel.line(x + i, y + h - 1, min(x + w - 1, x + i + 5), y, 10 if (i // 6) % 2 == 0 else 0)
            # クレーンアームのシンボル
            pyxel.line(x + 4, y + 2, x + w - 4, y + 2, 7)
            pyxel.line(x + w - 4, y + 2, x + w - 4, y + 8, 9)

            # 頭上の進捗バー
            pw = 28
            ratio = p.construction_progress
            pyxel.rect(x - 2, y - 6, pw, 4, 0)
            pyxel.rectb(x - 2, y - 6, pw, 4, 5)
            fill_w = max(0, int((pw - 2) * ratio))
            if fill_w > 0:
                pyxel.rect(x - 1, y - 5, fill_w, 2, 10)

            # ラベル表示
            self.draw_text(x - 8, y + h + 2, f"{p.name}", 7)
            rem_s = max(0.0, p.construction_timer)
            self.draw_text(x - 6, y + h + 13, f"工事中 {rem_s:.0f}s", 9)
            return

        if p.plant_type == "thermal":
            pyxel.rect(x, y + 6, w, h - 6, 4)
            pyxel.rect(x + 4, y, 4, 6, 9)
            if p.get_output_mw() > 5.0 and pyxel.frame_count % 12 < 8:
                pyxel.circ(x + 5 + (pyxel.frame_count % 4), y - 3 - (pyxel.frame_count % 3), 2, 7)
            self.draw_text(x - 8, y + h + 2, f"{p.name}", 7)
            self.draw_text(x - 4, y + h + 13, f"{p.current_output_mw:.0f}MW", 10)

        elif p.plant_type == "hydro":
            pyxel.rect(x, y + 4, w, h - 4, 1)
            pyxel.rectb(x, y + 4, w, h - 4, 12)
            pyxel.line(x + 4, y + 8, x + w - 4, y + 8, 7)
            self.draw_text(x - 8, y + h + 2, f"{p.name}", 7)
            self.draw_text(x - 4, y + h + 13, f"{p.current_output_mw:.0f}MW", 11)

        elif p.plant_type == "pumped_storage":
            mode_col = 10 if p.mode == "GEN" else (12 if p.mode == "PUMP" else 5)
            pyxel.rect(x, y, w, h, 2)
            pyxel.rectb(x, y, w, h, mode_col)

            ratio = p.storage_mwh / max(1.0, p.max_storage_mwh)
            bar_h = int((h - 4) * ratio)
            pyxel.rect(x + 2, y + h - 2 - bar_h, 4, bar_h, 12)

            m_text = "GEN" if p.mode == "GEN" else ("PUMP" if p.mode == "PUMP" else "OFF")
            pyxel.text(x + 8, y + 4, m_text, mode_col)
            
            self.draw_text(x - 8, y + h + 2, f"{p.name}", 7)
            if p.mode == "GEN":
                self.draw_text(x - 4, y + h + 13, f"+{p.current_output_mw:.0f}MW", 10)
            elif p.mode == "PUMP":
                self.draw_text(x - 4, y + h + 13, f"-{p.current_pump_load_mw:.0f}MW", 12)
            else:
                self.draw_text(x - 4, y + h + 13, "0MW", 5)

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
            self.draw_text(x - 8, y + h + 2, f"{c.name}", 7)
            self.draw_text(x - 4, y + h + 13, f"{c.current_load_mw:.0f}MW" if c.is_connected else "停電中", 8 if not c.is_connected else 10)

        elif c.consumer_type == "factory":
            fac_col = 6 if c.is_connected else 5
            pyxel.rect(x, y + 4, w, h - 4, fac_col)
            pyxel.tri(x, y + 4, x + 5, y, x + 10, y + 4, 5)
            pyxel.tri(x + 10, y + 4, x + 15, y, x + 20, y + 4, 5)
            if c.is_connected and pyxel.frame_count % 8 < 5:
                pyxel.pset(x + 4, y + 8, 10)
                pyxel.pset(x + 14, y + 8, 11)
            self.draw_text(x - 8, y + h + 2, f"{c.name}", 7)
            self.draw_text(x - 4, y + h + 13, f"{c.current_load_mw:.0f}MW" if c.is_connected else "停止中", 8 if not c.is_connected else 10)

    def draw_inspector_and_controls(self, selected_obj, buttons: dict, plants: list, lines: list, mx: int, my: int, slider=None, is_manual_paused: bool = False):
        panel_y = 268
        pyxel.rect(0, panel_y, 480, 92, 1)
        pyxel.line(0, panel_y, 480, panel_y, 6)

        # 1. 選択中オブジェクトの情報 & コントロール
        if selected_obj is not None:
            self._draw_object_controls(selected_obj, buttons, panel_y, slider)
        else:
            if is_manual_paused:
                self.draw_text(8, panel_y + 6, "【 ⏸ 全体時間停止中 】 空き地クリック / 右クリックで時間再開", 10)
            else:
                self.draw_text(8, panel_y + 6, "【 ▶ 系統運転中 】 設備選択で指令、空き地クリックで時間一時停止", 7)
            # 各発電所の現在状況サマリー一覧
            for idx, p in enumerate(plants):
                col_x = 8 + (idx % 3) * 102
                row_y = panel_y + 24 + (idx // 3) * 18
                if getattr(p, "is_under_construction", False):
                    out_str = f"・{p.name}: 工事中({int(p.construction_timer + 0.9)}s)"
                    self.draw_text(col_x, row_y, out_str, 9)
                else:
                    out_str = f"・{p.name}: {p.get_output_mw():.0f}MW"
                    self.draw_text(col_x, row_y, out_str, 10)

        # 2. 設備新設（投資）エリア (右側: x=315)
        self.draw_text(315, panel_y + 6, "【 設備新設・設備投資 】", 10)
        if "btn_buy_thermal" in buttons:
            buttons["btn_buy_thermal"].draw()
        if "btn_buy_hydro" in buttons:
            buttons["btn_buy_hydro"].draw()
        if "btn_buy_pumped" in buttons:
            buttons["btn_buy_pumped"].draw()

        # 3. 電線ホバー時の潮流ツールチップ
        self._draw_line_tooltip(lines, mx, my)

    def _draw_object_controls(self, obj, buttons: dict, panel_y: int, slider=None):
        # 建設中の場合
        if getattr(obj, "is_under_construction", False):
            title = f"【建設工事中: {obj.name}】"
            self.draw_text(8, panel_y + 5, title, 9)
            prog = int(obj.construction_progress * 100)
            rem = max(0.0, obj.construction_timer)
            info_str = f"建設工事進捗: {prog}% (完成・送電網接続まで残り約 {rem:.1f} 秒)"
            self.draw_text(8, panel_y + 22, info_str, 10)

            # 進捗バー
            pyxel.rect(8, panel_y + 38, 280, 8, 0)
            pyxel.rectb(8, panel_y + 38, 280, 8, 5)
            fill_w = int(278 * obj.construction_progress)
            if fill_w > 0:
                pyxel.rect(9, panel_y + 39, fill_w, 6, 10)

            self.draw_text(8, panel_y + 52, "※工事が完了すると自動的に中央変電所へ送電線が接続され、", 7)
            self.draw_text(8, panel_y + 64, "  電力供給・出力制御が可能になります。", 7)
            return

        can_op = getattr(obj, "can_operate", lambda: True)()
        cd = getattr(obj, "cooldown_timer", 0.0)
        max_cd = getattr(obj, "command_cooldown_sec", 1.5)

        title = f"【選択: {obj.name}】"
        self.draw_text(8, panel_y + 5, title, 10)

        # 閉じる（選択解除）ボタン
        if "btn_close" in buttons:
            buttons["btn_close"].draw()

        # クールダウン（指令待機中）インジケーター
        if cd > 0.0:
            self.draw_text(130, panel_y + 5, f"[指令応答待機中: {cd:.1f}s]", 9)
            # ミニ待機バー
            bw = 40
            pyxel.rect(205, panel_y + 7, bw, 4, 0)
            pyxel.rectb(205, panel_y + 7, bw, 4, 9)
            cd_ratio = max(0.0, min(1.0, cd / max(0.1, max_cd)))
            cd_w = int((bw - 2) * cd_ratio)
            if cd_w > 0:
                pyxel.rect(206, panel_y + 8, cd_w, 2, 9)

        # 火力発電所の場合
        if hasattr(obj, "plant_type") and obj.plant_type == "thermal":
            ramp = getattr(obj, "ramp_rate", getattr(obj, "ramp_rate_mw_per_sec", 8.0))
            info_str = f"現在出力: {obj.current_output_mw:.1f}MW / 目標: {obj.target_output_mw:.0f}MW (定格: {obj.max_output_mw:.0f}MW, 追従: ±{ramp:.1f}MW/s)"
            self.draw_text(8, panel_y + 19, info_str, 7)

            # スライダーの描画
            if slider is not None:
                slider.enabled = can_op
                slider.draw()
                # スライダー横の指令目標値表示
                self.draw_text(slider.x + slider.w + 6, panel_y + 36, f"指令値: {slider.value:.0f}MW", 10 if can_op else 5)
                # 目盛りラベル
                self.draw_text(slider.x, panel_y + 47, f"MIN({obj.min_output_mw:.0f})", 6)
                self.draw_text(slider.x + slider.w - 36, panel_y + 47, f"MAX({obj.max_output_mw:.0f})", 6)

            # 指令送信ボタン (Enter)
            if "btn_commit" in buttons:
                buttons["btn_commit"].enabled = can_op
                buttons["btn_commit"].draw()

            # 数値微調整ボタン群 (panel_y + 60)
            for k in ["btn_dec10", "btn_dec1", "btn_inc1", "btn_inc10", "btn_min", "btn_max"]:
                if k in buttons:
                    buttons[k].enabled = can_op
                    buttons[k].draw()

        # 揚水発電所の場合
        elif hasattr(obj, "plant_type") and obj.plant_type == "pumped_storage":
            ratio = obj.storage_mwh / max(1.0, obj.max_storage_mwh)
            cur_out = f"+{obj.current_output_mw:.1f}MW" if obj.mode == "GEN" else (f"-{obj.current_pump_load_mw:.1f}MW" if obj.mode == "PUMP" else "0MW")
            storage_str = f"現在: {obj.mode} ({cur_out} / 定格:{obj.max_output_mw:.0f}MW) | 貯水: {obj.storage_mwh:.0f}/{obj.max_storage_mwh:.0f}MWh ({int(ratio*100)}%)"
            self.draw_text(8, panel_y + 19, storage_str, 11)

            # モード選択ボタン
            for k in ["btn_pump_off", "btn_pump_gen", "btn_pump_pump"]:
                if k in buttons:
                    buttons[k].enabled = can_op
                    buttons[k].draw()

            # 仮選択中（pending_mode）のボタンを白枠でハイライト
            pend_m = getattr(obj, "pending_mode", obj.mode)
            active_btn_key = "btn_pump_off" if pend_m == "OFF" else ("btn_pump_gen" if pend_m == "GEN" else "btn_pump_pump")
            if active_btn_key in buttons:
                ab = buttons[active_btn_key]
                pyxel.rectb(ab.x - 1, ab.y - 1, ab.w + 2, ab.h + 2, 7)

            # 指令送信ボタン (Enter)
            if "btn_commit" in buttons:
                buttons["btn_commit"].enabled = can_op
                buttons["btn_commit"].draw()

            self.draw_text(8, panel_y + 64, "※モードを選択し [Enter] で指令送信。送信後に運転開始し時間再開", 6)

        # 水力発電所の場合
        elif hasattr(obj, "plant_type") and obj.plant_type == "hydro":
            info_str = f"現在出力: {obj.current_output_mw:.1f}MW (河川流量依存・ベースロード運転・低コスト)"
            self.draw_text(8, panel_y + 20, info_str, 7)
            self.draw_text(8, panel_y + 40, "※水力発電は出力を直接調整できません。天候に合わせて安定発電します。", 6)
            self.draw_text(8, panel_y + 62, "※右クリックまたは何もない場所をクリックして時間再開", 10)

        # 中央変電所の場合（受給個別制御・系統開閉盤）
        elif hasattr(obj, "substation_type"):
            stat_str = "全系統正常送配電中" if obj.is_connected else "全系統遮断停止中"
            self.draw_text(8, panel_y + 19, f"系統母線状態: {stat_str} (接続発電所 / 接続需要家 を個別に開閉制御可能)", 11 if obj.is_connected else 8)

            # 開閉盤ダイアログを開くボタン (Space)
            if "btn_toggle_power" in buttons:
                btn = buttons["btn_toggle_power"]
                btn.enabled = can_op
                btn.text = "系統開閉盤を開く (Space)"
                btn.col_bg = 3
                btn.col_hover = 11
                btn.draw()

            self.draw_text(8, panel_y + 64, "※[Space] またはボタンクリックで【系統開閉盤】を開き、設備ごとに接続・切断を設定できます", 10)

        # 需要家の場合（送電切替は不可・インスペクター情報表示のみ）
        elif hasattr(obj, "consumer_type"):
            stat_str = "受電中 (送電線接続)" if obj.is_connected else "送電遮断中"
            self.draw_text(8, panel_y + 19, f"需要負荷: {obj.current_load_mw:.1f}MW (基準: {obj.base_load_mw:.0f}MW) | 受電状態: {stat_str}", 11 if obj.is_connected else 8)
            self.draw_text(8, panel_y + 40, "※需要家単位での送電停止はできません。", 7)
            self.draw_text(8, panel_y + 62, "※系統全体の送受電を停止・復旧するには【中央変電所】を選択してください。", 10)

    def _draw_line_tooltip(self, lines: list, mx: int, my: int):
        for line in lines:
            dist = self._point_to_line_dist(mx, my, line.x1, line.y1, line.x2, line.y2)
            if dist < 5.0:
                short_name = line.name.replace("中央変電所", "変電所")
                tip = f"{short_name}: {abs(line.flow_mw):.1f}/{line.capacity_mw:.0f}MW"
                tw = len(tip) * 5 + 10
                tx = min(480 - tw - 6, max(6, mx + 8))
                ty = max(45, my - 16)
                pyxel.rect(tx, ty, tw, 14, 0)
                pyxel.rectb(tx, ty, tw, 14, 7)
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

    def draw_game_over(self, score: float, time_sec: float, energy_kwh: float, mx: int = 0, my: int = 0):
        gx, gy, gw, gh = 65, 42, 350, 268
        pyxel.rect(gx, gy, gw, gh, 0)
        pyxel.rectb(gx, gy, gw, gh, 8)
        
        self.draw_text(gx + 95, gy + 12, "=== BLACKOUT ===", 8)
        self.draw_text(gx + 78, gy + 28, "系統崩壊（大規模広域停電）", 8)
        
        self.draw_text(gx + 30, gy + 48, "周波数の許容範囲を長時間逸脱したため", 7)
        self.draw_text(gx + 30, gy + 62, "系統保護リレーが作動し全系統が停止しました", 7)
        
        self.draw_text(gx + 30, gy + 82, f"稼働維持時間 : {int(time_sec)} 秒", 7)
        self.draw_text(gx + 30, gy + 96, f"供給総電力量 : {int(energy_kwh):,} kWh", 7)
        self.draw_text(gx + 30, gy + 110, f"最終売電利益 : ¥{int(score):,}", 10)

        # ヒントボックス（次へのアドバイス）
        hint_y = gy + 130
        hint_w = gw - 30
        hint_x = gx + 15
        pyxel.rect(hint_x, hint_y, hint_w, 36, 1)
        pyxel.rectb(hint_x, hint_y, hint_w, 36, 10)
        self.draw_text(hint_x + 8, hint_y + 4, "💡 【 司令塔への運用ヒント 】", 10)
        self.draw_text(hint_x + 8, hint_y + 18, "制御が追い付かない時は、中央変電所での遮断操作も検討してください。", 11, max_width=305)

        # 履歴ログ確認ボタン (L / Click)
        btn_y = gy + 178
        btn_w = 230
        btn_x = gx + (gw - btn_w) // 2
        is_hover = (btn_x <= mx <= btn_x + btn_w and btn_y <= my <= btn_y + 18)
        b_col = 11 if is_hover else 10
        pyxel.rect(btn_x, btn_y, btn_w, 18, 1 if not is_hover else 5)
        pyxel.rectb(btn_x, btn_y, btn_w, 18, b_col)
        self.draw_text(btn_x + 28, btn_y + 4, "[ 通報・履歴ログ確認 (L / Click) ]", b_col)

        if pyxel.frame_count % 30 < 20:
            self.draw_text(gx + 78, gy + 210, "[ R キー / 右クリックで再挑戦 ]", 11)
        self.draw_text(gx + 98, gy + 230, "[ ESC / Q キー: メニューへ ]", 6)

    def draw_message_log_modal(self, logs: list, scroll_y: int, mx: int, my: int):
        """メッセージ履歴（ログ）モーダル画面を描画"""
        # 1. 画面全体の暗幕オーバーレイ
        for y_line in range(0, 360, 2):
            pyxel.line(0, y_line, 480, y_line, 0)

        # 2. ログウィンドウ枠 (x=30, y=20, w=420, h=320)
        wx, wy, ww, wh = 30, 20, 420, 320
        pyxel.rect(wx, wy, ww, wh, 1)
        pyxel.rectb(wx, wy, ww, wh, 7)

        # ヘッダー帯
        pyxel.rect(wx, wy, ww, 20, 0)
        pyxel.rectb(wx, wy, ww, 20, 6)
        self.draw_text(wx + 10, wy + 5, "【 通報・指令・イベント履歴ログ 】 (時間一時停止中)", 10)

        # 閉じるボタン
        close_btn_hover = (wx + ww - 65 <= mx <= wx + ww - 5 and wy + 3 <= my <= wy + 17)
        c_bg = 8 if close_btn_hover else 1
        pyxel.rect(wx + ww - 65, wy + 3, 60, 14, c_bg)
        pyxel.rectb(wx + ww - 65, wy + 3, 60, 14, 7)
        self.draw_text(wx + ww - 61, wy + 5, "[閉じる X]", 7)

        # リスト表示領域クリップ (y=44 〜 306)
        list_y = wy + 24
        list_h = wh - 38
        pyxel.clip(wx + 4, list_y, ww - 8, list_h)

        # 最新のログが上に来るように逆順で表示
        rev_logs = list(reversed(logs))
        curr_y = list_y - scroll_y

        if not rev_logs:
            self.draw_text(wx + 20, list_y + 20, "履歴ログはありません。", 6)
        else:
            for item in rev_logs:
                t_str = item.get("time_str", "00:00")
                text = item.get("text", "")
                col = item.get("color", 7)

                lines = text.split("\n")
                entry_h = len(lines) * 12 + 6

                # 画面内にある場合のみ描画
                if curr_y + entry_h > list_y and curr_y < list_y + list_h:
                    pyxel.rect(wx + 6, curr_y, ww - 24, entry_h - 2, 0)
                    pyxel.rectb(wx + 6, curr_y, ww - 24, entry_h - 2, 5)
                    self.draw_text(wx + 10, curr_y + 3, f"[{t_str}]", 11)
                    for l_idx, l_text in enumerate(lines):
                        self.draw_text(wx + 52, curr_y + 3 + l_idx * 12, l_text, col, max_width=335)

                curr_y += entry_h

        # クリップ解除
        pyxel.clip()

        # スクロールバー
        total_content_h = max(list_h, sum((len(it.get("text", "").split("\n")) * 12 + 6) for it in rev_logs))
        sb_h = list_h
        sb_x = wx + ww - 14
        pyxel.rect(sb_x, list_y, 6, sb_h, 0)
        pyxel.rectb(sb_x, list_y, 6, sb_h, 5)

        thumb_ratio = min(1.0, list_h / max(1, total_content_h))
        thumb_h = max(10, int(sb_h * thumb_ratio))
        max_scroll = max(1, total_content_h - list_h)
        thumb_y = list_y + int((sb_h - thumb_h) * min(1.0, max(0.0, scroll_y / max_scroll)))
        pyxel.rect(sb_x + 1, thumb_y, 4, thumb_h, 10)

        # フッター案内
        pyxel.rect(wx, wy + wh - 14, ww, 14, 0)
        pyxel.line(wx, wy + wh - 14, wx + ww, wy + wh - 14, 5)
        self.draw_text(wx + 10, wy + wh - 11, "※ホイール / ↑↓キーでスクロール | 右クリック / ESC / [閉じる] で復帰", 6)

    def draw_substation_modal(self, plants: list, consumers: list, tab: int, scroll_y: int, mx: int, my: int, can_commit: bool = True):
        """中央変電所：受給個別開閉盤（モーダルダイアログ）を描画"""
        # 1. 画面全体の暗幕オーバーレイ
        for y_line in range(0, 360, 2):
            pyxel.line(0, y_line, 480, y_line, 0)

        # 2. 開閉盤ウィンドウ枠 (x=25, y=15, w=430, h=330)
        wx, wy, ww, wh = 25, 15, 430, 330
        pyxel.rect(wx, wy, ww, wh, 1)
        pyxel.rectb(wx, wy, ww, wh, 7)

        # ヘッダー帯
        pyxel.rect(wx, wy, ww, 20, 0)
        pyxel.rectb(wx, wy, ww, 20, 6)
        self.draw_text(wx + 10, wy + 5, "【 中央変電所 - 系統開閉盤（受給個別制御） 】", 10)

        # 閉じるボタン
        close_btn_hover = (wx + ww - 65 <= mx <= wx + ww - 5 and wy + 3 <= my <= wy + 17)
        pyxel.rect(wx + ww - 65, wy + 3, 60, 14, 8 if close_btn_hover else 1)
        pyxel.rectb(wx + ww - 65, wy + 3, 60, 14, 7)
        self.draw_text(wx + ww - 61, wy + 5, "[閉じる X]", 7)

        # 3. タブ切り替え & 一括操作ボタン (wy + 23)
        tab_y = wy + 23
        # タブ0: 供給側 (発電所)
        is_tab0 = (tab == 0)
        t0_hover = (wx + 8 <= mx <= wx + 138 and tab_y <= my <= tab_y + 16)
        t0_bg = 3 if is_tab0 else (5 if t0_hover else 0)
        t0_fg = 7 if is_tab0 else (11 if t0_hover else 6)
        pyxel.rect(wx + 8, tab_y, 130, 16, t0_bg)
        pyxel.rectb(wx + 8, tab_y, 130, 16, 7 if is_tab0 else 5)
        self.draw_text(wx + 14, tab_y + 3, "[ 供給側: 発電所 (1) ]", t0_fg)

        # タブ1: 需要側 (町・工場)
        is_tab1 = (tab == 1)
        t1_hover = (wx + 142 <= mx <= wx + 272 and tab_y <= my <= tab_y + 16)
        t1_bg = 3 if is_tab1 else (5 if t1_hover else 0)
        t1_fg = 7 if is_tab1 else (11 if t1_hover else 6)
        pyxel.rect(wx + 142, tab_y, 130, 16, t1_bg)
        pyxel.rectb(wx + 142, tab_y, 130, 16, 7 if is_tab1 else 5)
        self.draw_text(wx + 148, tab_y + 3, "[ 需要側: 町・工場 (2) ]", t1_fg)

        # 一括ボタン [全接続] / [全切断]
        all_on_hov = (wx + ww - 98 <= mx <= wx + ww - 54 and tab_y <= my <= tab_y + 16)
        pyxel.rect(wx + ww - 98, tab_y, 44, 16, 3 if all_on_hov else 1)
        pyxel.rectb(wx + ww - 98, tab_y, 44, 16, 11 if all_on_hov else 3)
        self.draw_text(wx + ww - 94, tab_y + 3, "[全接続]", 11)

        all_off_hov = (wx + ww - 50 <= mx <= wx + ww - 6 and tab_y <= my <= tab_y + 16)
        pyxel.rect(wx + ww - 50, tab_y, 44, 16, 8 if all_off_hov else 1)
        pyxel.rectb(wx + ww - 50, tab_y, 44, 16, 7 if all_off_hov else 8)
        self.draw_text(wx + ww - 46, tab_y + 3, "[全切断]", 8)

        # 4. リスト表示領域 (y=57〜270, h=213)
        list_x = wx + 8
        list_y = wy + 42
        list_w = ww - 16
        list_h = 222
        pyxel.clip(list_x, list_y, list_w, list_h)

        items = plants if tab == 0 else consumers
        item_h = 36
        curr_y = list_y + 3 - scroll_y

        for obj in items:
            if curr_y + item_h > list_y and curr_y < list_y + list_h:
                is_under_con = getattr(obj, "is_under_construction", False)
                pend_conn = getattr(obj, "pending_connected", getattr(obj, "connected", getattr(obj, "is_connected", True)))
                curr_conn = getattr(obj, "connected", getattr(obj, "is_connected", True))

                # カード枠
                card_bg = 0
                card_border = 5 if curr_conn else 8
                pyxel.rect(list_x + 2, curr_y, list_w - 18, item_h - 4, card_bg)
                pyxel.rectb(list_x + 2, curr_y, list_w - 18, item_h - 4, card_border)

                # 左端カラーバー
                bar_col = 11 if curr_conn else 8
                pyxel.rect(list_x + 2, curr_y, 4, item_h - 4, bar_col)

                # 設備名・ステータス
                name = obj.name
                if tab == 0:
                    # 発電所情報
                    p = obj
                    self.draw_text(list_x + 10, curr_y + 3, f"{name}", 10)
                    if is_under_con:
                        self.draw_text(list_x + 10, curr_y + 17, f"【建設工事中】完成まで約{int(p.construction_timer)}秒", 9)
                    else:
                        out_val = p.current_output_mw
                        stat_detail = f"現在出力: {out_val:.1f}MW / 定格: {p.max_output_mw:.0f}MW"
                        if getattr(p, "plant_type", "") == "pumped_storage" and p.mode == "PUMP":
                            stat_detail = f"揚水負荷: {p.current_pump_load_mw:.1f}MW (定格: {p.max_output_mw:.0f}MW)"
                        self.draw_text(list_x + 10, curr_y + 17, stat_detail, 7)
                else:
                    # 需要家情報
                    c = obj
                    self.draw_text(list_x + 10, curr_y + 3, f"{name}", 11)
                    self.draw_text(list_x + 10, curr_y + 17, f"需要負荷: {c.current_load_mw:.1f}MW (基準: {c.base_load_mw:.0f}MW)", 7)

                # 現在状態ラベル
                c_lbl = "通電中" if curr_conn else "遮断中"
                c_col = 11 if curr_conn else 8
                self.draw_text(list_x + list_w - 165, curr_y + 10, f"[{c_lbl}]", c_col)

                # 切替ボタン
                btn_w = 70
                btn_h = 20
                btn_bx = list_x + list_w - 98
                btn_by = curr_y + 6
                btn_hover = (btn_bx <= mx <= btn_bx + btn_w and btn_by <= my <= btn_by + btn_h)

                if is_under_con:
                    # 建設中は切替不可
                    pyxel.rect(btn_bx, btn_by, btn_w, btn_h, 5)
                    pyxel.rectb(btn_bx, btn_by, btn_w, btn_h, 6)
                    self.draw_text(btn_bx + 12, btn_by + 5, "工事中", 6)
                else:
                    # 切替トグルボタン（予定状態を表示）
                    if pend_conn:
                        btn_col = 3 if not btn_hover else 11
                        pyxel.rect(btn_bx, btn_by, btn_w, btn_h, 1)
                        pyxel.rectb(btn_bx, btn_by, btn_w, btn_h, btn_col)
                        self.draw_text(btn_bx + 10, btn_by + 5, "接続 (ON)", btn_col)
                    else:
                        btn_col = 8 if not btn_hover else 7
                        pyxel.rect(btn_bx, btn_by, btn_w, btn_h, 8 if btn_hover else 0)
                        pyxel.rectb(btn_bx, btn_by, btn_w, btn_h, btn_col)
                        self.draw_text(btn_bx + 10, btn_by + 5, "遮断 (OFF)", 7 if btn_hover else 8)

            curr_y += item_h

        # クリップ解除
        pyxel.clip()

        # スクロールバー
        total_content_h = max(list_h, len(items) * item_h)
        sb_h = list_h
        sb_x = wx + ww - 14
        pyxel.rect(sb_x, list_y, 6, sb_h, 0)
        pyxel.rectb(sb_x, list_y, 6, sb_h, 5)

        thumb_ratio = min(1.0, list_h / max(1, total_content_h))
        thumb_h = max(10, int(sb_h * thumb_ratio))
        max_scroll = max(1, total_content_h - list_h)
        thumb_y = list_y + int((sb_h - thumb_h) * min(1.0, max(0.0, scroll_y / max_scroll)))
        pyxel.rect(sb_x + 1, thumb_y, 4, thumb_h, 10)

        # 5. フッター：需給プレビュー & アクションボタン
        foot_y = wy + wh - 62
        pyxel.rect(wx, foot_y, ww, 62, 0)
        pyxel.line(wx, foot_y, wx + ww, foot_y, 5)

        # 予定需給の計算プレビュー
        exp_gen = sum(p.get_output_mw() for p in plants if getattr(p, "pending_connected", p.connected))
        exp_load = sum(c.base_load_mw for c in consumers if getattr(c, "pending_connected", c.is_connected))
        exp_diff = exp_gen - exp_load
        diff_str = f"+{exp_diff:.1f}" if exp_diff >= 0 else f"{exp_diff:.1f}"
        diff_col = 11 if abs(exp_diff) <= 10.0 else (10 if abs(exp_diff) <= 25.0 else 8)

        self.draw_text(wx + 10, foot_y + 6, f"【開閉後 予想】総供給: {exp_gen:.0f}MW / 総需要: {exp_load:.0f}MW (需給差: {diff_str}MW)", diff_col)

        # 確定指令送信ボタン (Enter)
        commit_w = 230
        commit_h = 24
        commit_x = wx + 12
        commit_y = foot_y + 24
        com_hover = (commit_x <= mx <= commit_x + commit_w and commit_y <= my <= commit_y + commit_h)
        com_bg = 3 if com_hover else 1
        com_fg = 11 if com_hover else 7
        pyxel.rect(commit_x, commit_y, commit_w, commit_h, com_bg)
        pyxel.rectb(commit_x, commit_y, commit_w, commit_h, 11 if com_hover else 3)
        self.draw_text(commit_x + 22, commit_y + 7, "[ 指令送信・開閉操作を確定 (Enter) ]", com_fg)

        # キャンセル閉じるボタン (ESC)
        can_w = 160
        can_h = 24
        can_x = wx + ww - can_w - 12
        can_y = foot_y + 24
        can_hover = (can_x <= mx <= can_x + can_w and can_y <= my <= can_y + can_h)
        pyxel.rect(can_x, can_y, can_w, can_h, 5 if can_hover else 0)
        pyxel.rectb(can_x, can_y, can_w, can_h, 7 if can_hover else 5)
        self.draw_text(can_x + 18, can_y + 7, "[ キャンセル / 閉じる (ESC) ]", 7)
