"""
周波数シミュレーションモデル
需給バランス（発電量 - 需要量）から系統周波数の動特性を計算し、
許容範囲逸脱による停電（ブラックアウト）を判定する。
"""
import random

class FrequencySystem:
    def __init__(self, rated_freq=60.0, tolerance=0.5, max_violation_sec=5.0):
        self.rated_freq = rated_freq
        self.freq = rated_freq
        self.tolerance = tolerance
        self.max_violation_sec = max_violation_sec
        
        # 系統パラメータ（慣性・ダンピング）
        self.inertia = 120.0       # 系統の慣性定数 (MW*s/Hz)
        self.damping = 10.0        # 負荷自己制御性 (MW/Hz)
        
        # 逸脱監視
        self.violation_timer = 0.0
        self.is_violating = False
        self.is_critical = False
        self.is_blackout = False
        self.violation_ratio = 0.0 # 0.0 ~ 1.0 (ゲームオーバーまでのゲージ)

    def update(self, total_gen_mw: float, total_load_mw: float, dt: float):
        """1フレーム（dt秒）あたりの周波数を更新"""
        delta_p = total_gen_mw - total_load_mw
        
        # 小さなランダム需要ゆらぎ（系統の自然な揺らぎ）
        noise = (random.random() - 0.5) * 0.8
        net_delta = delta_p + noise
        
        # スイング方程式簡略版: df/dt = (delta_p - D*(f - f0)) / M
        freq_dev = self.freq - self.rated_freq
        df = ((net_delta - self.damping * freq_dev) / self.inertia) * dt
        
        self.freq += df
        # 極端な発散防止リミット
        self.freq = max(45.0, min(75.0, self.freq))
        
        # 逸脱判定
        dev = abs(self.freq - self.rated_freq)
        if dev > self.tolerance:
            self.is_violating = True
            # 逸脱度が大きいほど早くカウントが進む
            severity = (dev / self.tolerance)
            self.violation_timer += dt * max(1.0, severity * 0.8)
            
            if self.violation_timer >= self.max_violation_sec * 0.5:
                self.is_critical = True
            else:
                self.is_critical = False
                
            if self.violation_timer >= self.max_violation_sec:
                self.is_blackout = True
        else:
            self.is_violating = False
            self.is_critical = False
            # 正常範囲に戻ればタイマーは速やかに減少
            self.violation_timer = max(0.0, self.violation_timer - dt * 2.0)
            
        self.violation_ratio = min(1.0, self.violation_timer / self.max_violation_sec)

    def set_difficulty(self, tolerance: float, max_violation_sec: float):
        self.tolerance = tolerance
        self.max_violation_sec = max_violation_sec
        self.violation_timer = 0.0
        self.is_blackout = False
        self.freq = self.rated_freq
