"""
発電所モデル
火力発電所、流れ込み式水力発電所、揚水発電所
"""

class BasePlant:
    def __init__(self, plant_id: str, name: str, plant_type: str, x: int, y: int,
                 max_output_mw: float, min_output_mw: float, ramp_rate: float):
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
        self.is_active = True

    def update(self, dt: float, weather_multiplier: float = 1.0):
        if not self.is_active or not self.connected:
            self.current_output_mw = 0.0
            return
            
        # ランプ速度に応じた追従
        if self.current_output_mw < self.target_output_mw:
            self.current_output_mw = min(self.target_output_mw, self.current_output_mw + self.ramp_rate * dt)
        elif self.current_output_mw > self.target_output_mw:
            self.current_output_mw = max(self.target_output_mw, self.current_output_mw - self.ramp_rate * dt)

    def set_target(self, target_mw: float):
        self.target_output_mw = max(self.min_output_mw, min(self.max_output_mw, target_mw))

    def get_output_mw(self) -> float:
        if not self.connected or not self.is_active:
            return 0.0
        return self.current_output_mw

    def get_load_mw(self) -> float:
        """発電所自体が消費する電力（揚水運転時など）"""
        return 0.0


class ThermalPlant(BasePlant):
    """火力発電所：応答速度（ランプ速度）に限界があるが、広い範囲で柔軟に出力調整可能"""
    def __init__(self, plant_id: str, name: str, x: int, y: int, config: dict):
        super().__init__(
            plant_id=plant_id,
            name=name,
            plant_type="thermal",
            x=x,
            y=y,
            max_output_mw=config.get("max_output_mw", 80.0),
            min_output_mw=config.get("min_output_mw", 10.0),
            ramp_rate=config.get("ramp_rate_mw_per_sec", 8.0)
        )
        self.current_output_mw = (self.max_output_mw + self.min_output_mw) / 2.0
        self.target_output_mw = self.current_output_mw
        # 燃料費 (円/MWh)
        self.fuel_cost_per_mwh = 8000.0


class HydroPlant(BasePlant):
    """流れ込み式水力発電所：天候（降水量・豊水係数）に依存するクリーンなベースロード"""
    def __init__(self, plant_id: str, name: str, x: int, y: int, config: dict):
        super().__init__(
            plant_id=plant_id,
            name=name,
            plant_type="hydro",
            x=x,
            y=y,
            max_output_mw=config.get("max_output_mw", 40.0),
            min_output_mw=config.get("min_output_mw", 20.0),
            ramp_rate=config.get("ramp_rate_mw_per_sec", 4.0)
        )
        self.base_output_mw = 30.0
        self.current_output_mw = self.base_output_mw
        self.target_output_mw = self.base_output_mw

    def update(self, dt: float, weather_multiplier: float = 1.0):
        # 豊水係数により自然発生可能電力が変化
        avail_mw = max(10.0, min(self.max_output_mw * 1.5, self.base_output_mw * weather_multiplier))
        self.target_output_mw = avail_mw
        super().update(dt, weather_multiplier)


class PumpedStoragePlant(BasePlant):
    """
    揚水発電所：
    - モード: "OFF", "GEN" (発電), "PUMP" (揚水)
    - PUMP時は系統から電力を消費して上部調整池に水を汲み上げる（需要家として振る舞う）
    - GEN時は水を落として急激に大出力発電を行う
    """
    def __init__(self, plant_id: str, name: str, x: int, y: int, config: dict):
        super().__init__(
            plant_id=plant_id,
            name=name,
            plant_type="pumped_storage",
            x=x,
            y=y,
            max_output_mw=config.get("max_output_mw", 70.0),
            min_output_mw=0.0,
            ramp_rate=config.get("ramp_rate_mw_per_sec", 25.0) # 高速応答
        )
        self.pump_load_mw = config.get("pump_load_mw", 75.0)
        self.max_storage_mwh = config.get("max_storage_mwh", 350.0)
        init_ratio = config.get("initial_storage_ratio", 0.5)
        self.storage_mwh = self.max_storage_mwh * init_ratio
        self.round_trip_eff = config.get("round_trip_efficiency", 0.75)
        
        self.mode = "OFF"  # "OFF", "GEN", "PUMP"
        self.current_output_mw = 0.0
        self.current_pump_load_mw = 0.0

    def toggle_mode(self):
        """OFF -> GEN -> PUMP -> OFF"""
        if self.mode == "OFF":
            self.mode = "GEN" if self.storage_mwh > 10.0 else "PUMP"
        elif self.mode == "GEN":
            self.mode = "PUMP"
        elif self.mode == "PUMP":
            self.mode = "OFF"

    def set_mode(self, mode: str):
        if mode in ("OFF", "GEN", "PUMP"):
            self.mode = mode

    def update(self, dt: float, weather_multiplier: float = 1.0):
        if not self.is_active or not self.connected:
            self.mode = "OFF"
            self.current_output_mw = 0.0
            self.current_pump_load_mw = 0.0
            return

        dt_hours = dt / 3600.0

        if self.mode == "GEN":
            self.current_pump_load_mw = 0.0
            # 発電：貯水残量があれば発電出力へランプアップ
            if self.storage_mwh > 0.5:
                target = self.max_output_mw
                if self.current_output_mw < target:
                    self.current_output_mw = min(target, self.current_output_mw + self.ramp_rate * dt)
                # 水を消費
                water_used_mwh = self.current_output_mw * dt_hours
                self.storage_mwh = max(0.0, self.storage_mwh - water_used_mwh)
                if self.storage_mwh <= 0.1:
                    # 水が尽きたらOFF
                    self.mode = "OFF"
                    self.current_output_mw = 0.0
            else:
                self.mode = "OFF"
                self.current_output_mw = 0.0

        elif self.mode == "PUMP":
            self.current_output_mw = 0.0
            # 揚水：貯水槽に空きがあればポンプ稼働
            if self.storage_mwh < self.max_storage_mwh:
                target = self.pump_load_mw
                if self.current_pump_load_mw < target:
                    self.current_pump_load_mw = min(target, self.current_pump_load_mw + self.ramp_rate * dt)
                # 揚水による蓄電
                water_added = self.current_pump_load_mw * dt_hours * self.round_trip_eff
                self.storage_mwh = min(self.max_storage_mwh, self.storage_mwh + water_added)
                if self.storage_mwh >= self.max_storage_mwh:
                    # 満水になったら自動OFF
                    self.mode = "OFF"
                    self.current_pump_load_mw = 0.0
            else:
                self.mode = "OFF"
                self.current_pump_load_mw = 0.0

        else: # OFF
            # 出力・負荷ともに0へ戻す
            if self.current_output_mw > 0:
                self.current_output_mw = max(0.0, self.current_output_mw - self.ramp_rate * dt)
            if self.current_pump_load_mw > 0:
                self.current_pump_load_mw = max(0.0, self.current_pump_load_mw - self.ramp_rate * dt)

    def get_output_mw(self) -> float:
        if not self.connected or not self.is_active:
            return 0.0
        return self.current_output_mw

    def get_load_mw(self) -> float:
        if not self.connected or not self.is_active:
            return 0.0
        return self.current_pump_load_mw
