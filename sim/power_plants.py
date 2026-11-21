"""
発電所モデル
火力発電所、流れ込み式水力発電所、揚水発電所
"""

class BasePlant:
    def __init__(self, plant_id: str, name: str, plant_type: str, x: int, y: int,
                 max_output_mw: float, min_output_mw: float, ramp_rate: float,
                 construction_time_sec: float = 0.0, command_cooldown_sec: float = 1.5):
        self.id = plant_id
        self.name = name
        self.plant_type = plant_type
        self.x = x
        self.y = y
        self.max_output_mw = max_output_mw
        self.min_output_mw = min_output_mw
        self.ramp_rate = ramp_rate  # MW/sec
        
        self.current_output_mw = min_output_mw
        self.target_output_mw = min_output_mw
        self.connected = True
        self.pending_connected = True
        self.is_active = True

        # 建設中管理
        self.is_under_construction = (construction_time_sec > 0.0)
        self.total_construction_time = max(0.0, construction_time_sec)
        self.construction_timer = self.total_construction_time
        self.just_completed = False

        # 指令操作クールダウン制限
        self.command_cooldown_sec = command_cooldown_sec
        self.cooldown_timer = 0.0
        self.pending_target_mw = self.target_output_mw

        if self.is_under_construction:
            self.is_active = False
            self.current_output_mw = 0.0

    @property
    def ramp_rate_mw_per_sec(self) -> float:
        return self.ramp_rate

    @property
    def construction_progress(self) -> float:
        if self.total_construction_time <= 0.0:
            return 1.0
        return max(0.0, min(1.0, 1.0 - (self.construction_timer / self.total_construction_time)))

    def can_operate(self) -> bool:
        """操作コマンドを発行可能か（建設中ではなく、クールダウンが明けているか）"""
        return (not self.is_under_construction) and (self.cooldown_timer <= 0.0)

    def trigger_cooldown(self):
        """指令受理後のクールダウンを開始"""
        self.cooldown_timer = self.command_cooldown_sec

    def update(self, dt: float, weather_multiplier: float = 1.0):
        # 完成通知フラグを毎フレームリセット（ビープ音連続発生を防止）
        self.just_completed = False

        # 操作制限クールダウンタイマーの更新
        if self.cooldown_timer > 0.0:
            self.cooldown_timer = max(0.0, self.cooldown_timer - dt)

        # 建設中のカウントダウン処理
        if self.is_under_construction:
            self.construction_timer -= dt
            if self.construction_timer <= 0.0:
                self.is_under_construction = False
                self.construction_timer = 0.0
                self.is_active = True
                self.just_completed = True
                self.current_output_mw = self.min_output_mw
                self.target_output_mw = (self.max_output_mw + self.min_output_mw) / 2.0
                self.pending_target_mw = self.target_output_mw
            else:
                self.current_output_mw = 0.0
                return

        if not self.is_active or not self.connected:
            self.current_output_mw = 0.0
            return
            
        # ランプ速度に応じた追従
        if self.current_output_mw < self.target_output_mw:
            self.current_output_mw = min(self.target_output_mw, self.current_output_mw + self.ramp_rate * dt)
        elif self.current_output_mw > self.target_output_mw:
            self.current_output_mw = max(self.target_output_mw, self.current_output_mw - self.ramp_rate * dt)

    def set_target(self, target_mw: float) -> bool:
        """指令目標値を仮設定（送信前に調整）"""
        clamped = max(self.min_output_mw, min(self.max_output_mw, target_mw))
        self.pending_target_mw = clamped
        return True

    def commit_command(self) -> bool:
        """指令送信：仮設定された目標出力を確定しクールダウンを開始"""
        if not self.can_operate():
            return False
        self.target_output_mw = self.pending_target_mw
        self.trigger_cooldown()
        return True

    def toggle_pending_connection(self):
        """変電所開閉盤での仮接続状態反転"""
        self.pending_connected = not self.pending_connected
        return self.pending_connected

    def commit_connection(self):
        """変電所からの送電線接続・遮断指令を確定"""
        self.connected = self.pending_connected

    def get_output_mw(self) -> float:
        if self.is_under_construction or not self.connected or not self.is_active:
            return 0.0
        return self.current_output_mw

    def get_load_mw(self) -> float:
        """発電所自体が消費する電力（揚水運転時など）"""
        return 0.0


class ThermalPlant(BasePlant):
    """火力発電所：応答速度（ランプ速度）に限界があるが、広い範囲で柔軟に出力調整可能"""
    def __init__(self, plant_id: str, name: str, x: int, y: int, config: dict, construction_time_sec: float = 0.0, command_cooldown_sec: float = 1.5):
        super().__init__(
            plant_id=plant_id,
            name=name,
            plant_type="thermal",
            x=x,
            y=y,
            max_output_mw=config.get("max_output_mw", 80.0),
            min_output_mw=config.get("min_output_mw", 10.0),
            ramp_rate=config.get("ramp_rate_mw_per_sec", 3.5),
            construction_time_sec=construction_time_sec,
            command_cooldown_sec=command_cooldown_sec
        )
        if not self.is_under_construction:
            self.current_output_mw = (self.max_output_mw + self.min_output_mw) / 2.0
            self.target_output_mw = self.current_output_mw
            self.pending_target_mw = self.current_output_mw
        # 燃料費 (円/MWh)
        self.fuel_cost_per_mwh = 8000.0


class HydroPlant(BasePlant):
    """流れ込み式水力発電所：天候（降水量・豊水係数）に依存するクリーンなベースロード"""
    def __init__(self, plant_id: str, name: str, x: int, y: int, config: dict, construction_time_sec: float = 0.0, command_cooldown_sec: float = 1.5):
        super().__init__(
            plant_id=plant_id,
            name=name,
            plant_type="hydro",
            x=x,
            y=y,
            max_output_mw=config.get("max_output_mw", 40.0),
            min_output_mw=config.get("min_output_mw", 20.0),
            ramp_rate=config.get("ramp_rate_mw_per_sec", 4.0),
            construction_time_sec=construction_time_sec,
            command_cooldown_sec=command_cooldown_sec
        )
        self.base_output_mw = 30.0
        if not self.is_under_construction:
            self.current_output_mw = self.base_output_mw
            self.target_output_mw = self.base_output_mw
            self.pending_target_mw = self.base_output_mw

    def update(self, dt: float, weather_multiplier: float = 1.0):
        # 毎フレーム必ず super().update を呼び、just_completed のリセットと建設カウントダウンを行う
        super().update(dt, weather_multiplier)
        if self.is_under_construction or not self.is_active or not self.connected:
            return

        # 豊水係数により自然発生可能電力が変化
        avail_mw = max(10.0, min(self.max_output_mw * 1.5, self.base_output_mw * weather_multiplier))
        self.target_output_mw = avail_mw
        self.pending_target_mw = avail_mw
        # ランプ速度追従は super() 側で行われているが、念のため再度追従
        if self.current_output_mw < self.target_output_mw:
            self.current_output_mw = min(self.target_output_mw, self.current_output_mw + self.ramp_rate * dt)
        elif self.current_output_mw > self.target_output_mw:
            self.current_output_mw = max(self.target_output_mw, self.current_output_mw - self.ramp_rate * dt)


class PumpedStoragePlant(BasePlant):
    """
    揚水発電所：
    - モード: "OFF", "GEN" (発電), "PUMP" (揚水)
    - PUMP時は系統から電力を消費して上部調整池に水を汲み上げる（需要家として振る舞う）
    - GEN時は水を落として急激に大出力発電を行う
    """
    def __init__(self, plant_id: str, name: str, x: int, y: int, config: dict, construction_time_sec: float = 0.0, command_cooldown_sec: float = 1.5):
        super().__init__(
            plant_id=plant_id,
            name=name,
            plant_type="pumped_storage",
            x=x,
            y=y,
            max_output_mw=config.get("max_output_mw", 70.0),
            min_output_mw=0.0,
            ramp_rate=config.get("ramp_rate_mw_per_sec", 25.0), # 高速応答
            construction_time_sec=construction_time_sec,
            command_cooldown_sec=command_cooldown_sec
        )
        self.pump_load_mw = config.get("pump_load_mw", 75.0)
        self.max_storage_mwh = config.get("max_storage_mwh", 350.0)
        init_ratio = config.get("initial_storage_ratio", 0.5)
        self.storage_mwh = self.max_storage_mwh * init_ratio
        self.round_trip_eff = config.get("round_trip_efficiency", 0.75)
        
        self.mode = "OFF"  # "OFF", "GEN", "PUMP"
        self.pending_mode = "OFF"
        self.current_output_mw = 0.0
        self.current_pump_load_mw = 0.0
        self.target_output_mw = 0.0
        self.pending_target_mw = 0.0

    def set_pending_mode(self, mode: str) -> bool:
        """仮モードを設定"""
        if mode in ("OFF", "GEN", "PUMP"):
            self.pending_mode = mode
            return True
        return False

    def toggle_pending_mode(self) -> bool:
        """仮モードを OFF -> GEN -> PUMP -> OFF の順で切替"""
        if self.pending_mode == "OFF":
            self.pending_mode = "GEN" if self.storage_mwh > 10.0 else "PUMP"
        elif self.pending_mode == "GEN":
            self.pending_mode = "PUMP"
        elif self.pending_mode == "PUMP":
            self.pending_mode = "OFF"
        else:
            self.pending_mode = "OFF"
        return True

    def commit_command(self) -> bool:
        """指令確定：仮モードを適用しクールダウン開始"""
        if not self.can_operate():
            return False
        self.mode = self.pending_mode
        if self.mode == "GEN":
            self.target_output_mw = self.max_output_mw
        else:
            self.target_output_mw = 0.0
        self.trigger_cooldown()
        return True

    def toggle_mode(self) -> bool:
        """即時トグル（互換性用）"""
        self.toggle_pending_mode()
        return self.commit_command()

    def set_mode(self, mode: str) -> bool:
        """即時モード設定（互換性用）"""
        self.set_pending_mode(mode)
        return self.commit_command()

    def update(self, dt: float, weather_multiplier: float = 1.0):
        if self.is_under_construction:
            super().update(dt, weather_multiplier)
            return

        if not self.is_active or not self.connected:
            self.mode = "OFF"
            self.pending_mode = "OFF"
            self.target_output_mw = 0.0
            self.current_output_mw = 0.0
            self.current_pump_load_mw = 0.0
            super().update(dt, weather_multiplier)
            return

        dt_hours = dt / 3600.0

        if self.mode == "GEN":
            self.current_pump_load_mw = 0.0
            # 発電：貯水残量があれば発電目標を定格(70MW)に設定
            if self.storage_mwh > 0.5:
                self.target_output_mw = self.max_output_mw
            else:
                self.mode = "OFF"
                self.pending_mode = "OFF"
                self.target_output_mw = 0.0

        elif self.mode == "PUMP":
            self.target_output_mw = 0.0
            # 揚水：貯水槽に空きがあればポンプ負荷をランプアップ
            if self.storage_mwh < self.max_storage_mwh:
                target = self.pump_load_mw
                if self.current_pump_load_mw < target:
                    self.current_pump_load_mw = min(target, self.current_pump_load_mw + self.ramp_rate * dt)
                # 揚水による蓄電
                water_added = self.current_pump_load_mw * dt_hours * self.round_trip_eff
                self.storage_mwh = min(self.max_storage_mwh, self.storage_mwh + water_added)
                if self.storage_mwh >= self.max_storage_mwh:
                    self.mode = "OFF"
                    self.pending_mode = "OFF"
                    self.current_pump_load_mw = 0.0
            else:
                self.mode = "OFF"
                self.pending_mode = "OFF"
                self.current_pump_load_mw = 0.0

        else: # OFF
            self.target_output_mw = 0.0
            if self.current_pump_load_mw > 0:
                self.current_pump_load_mw = max(0.0, self.current_pump_load_mw - self.ramp_rate * dt)

        # super().update() で target_output_mw に向かって current_output_mw が ramp_rate で追従
        super().update(dt, weather_multiplier)

        # 水の消費計算
        if self.mode == "GEN" and self.current_output_mw > 0.0:
            water_used_mwh = self.current_output_mw * dt_hours
            self.storage_mwh = max(0.0, self.storage_mwh - water_used_mwh)
            if self.storage_mwh <= 0.1:
                self.mode = "OFF"
                self.pending_mode = "OFF"
                self.target_output_mw = 0.0

    def toggle_pending_connection(self):
        """変電所開閉盤での仮接続状態反転"""
        self.pending_connected = not self.pending_connected
        return self.pending_connected

    def commit_connection(self):
        """変電所からの送電線接続・遮断指令を確定"""
        self.connected = self.pending_connected

    def get_output_mw(self) -> float:
        if self.is_under_construction or not self.connected or not self.is_active:
            return 0.0
        return self.current_output_mw

    def get_load_mw(self) -> float:
        if self.is_under_construction or not self.connected or not self.is_active:
            return 0.0
        return self.current_pump_load_mw
