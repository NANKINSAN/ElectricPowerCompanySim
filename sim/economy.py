"""
経済・スコアモデル
売電収入、電力単価（基準30円×係数）、所持資金、発電所建設コスト
"""

class EconomySystem:
    def __init__(self, base_price: float = 30.0, initial_money: float = 100000.0):
        self.base_price = base_price          # 円/kWh
        self.price_multiplier = 1.0           # イベントによる変動係数
        self.current_price = base_price       # 現在の単価 (円/kWh)
        
        self.money = initial_money             # プレイヤーの所持資金（建設・運用用）
        self.total_sales_revenue = 0.0         # 累計販売金額（＝ゲームのスコア）
        self.total_energy_kwh = 0.0            # 累計供給電力量 (kWh)
        
        # 1秒あたりの売電額（レート監視用）
        self.revenue_per_sec = 0.0
        self.expense_per_sec = 0.0

    def set_price_multiplier(self, multiplier: float):
        self.price_multiplier = multiplier
        self.current_price = self.base_price * self.price_multiplier

    def update(self, supplied_mw: float, pumped_mw: float, dt: float):
        """
        1フレーム分の電力売上と揚水費用を計算
        1 MW * 1s = 1000 kW * (1/3600) h = 0.27778 kWh
        ゲーム進行感向上のため、1秒=1分相当（60倍スケール）のエネルギー換算を行う
        """
        energy_scale = 60.0
        supplied_kwh = (supplied_mw * 1000.0 / 3600.0) * dt * energy_scale
        pumped_kwh = (pumped_mw * 1000.0 / 3600.0) * dt * energy_scale

        # 売電収入
        revenue = supplied_kwh * self.current_price
        self.total_sales_revenue += revenue
        self.money += revenue
        self.total_energy_kwh += supplied_kwh
        self.revenue_per_sec = revenue / dt if dt > 0 else 0.0

        # 揚水消費電力のコスト（市場から買電して蓄電するコスト）
        pump_cost = pumped_kwh * self.current_price
        self.money = max(0.0, self.money - pump_cost)
        self.expense_per_sec = pump_cost / dt if dt > 0 else 0.0

    def can_afford(self, amount: float) -> bool:
        return self.money >= amount

    def spend_money(self, amount: float) -> bool:
        if self.can_afford(amount):
            self.money -= amount
            return True
        return False
