"""
初級ストーリーモード ステージ定義およびクリア判定ロジック
全5ステージの構成：
第1話: 新任司令塔、着任！ 〜 需給の基本と火力出力調整 〜
第2話: 谷と山の水力パワー 〜 余剰電力の揚水充電とピーク発電 〜
第3話: 町の発展と新たな力 〜 需要急増に備える発電所新設 〜
第4話: 激動の気象急変 〜 豪雨と寒波！揚水2拠点大作戦 〜
最終話: メガシティ・グリッドの夜明け 〜 大都市の繁栄と3000万円の偉業 〜
"""

STORY_STAGES = [
    {
        "stage_id": 1,
        "title": "第1話：新任司令塔、着任！",
        "subtitle": "需給の基本と火力出力調整",
        "synopsis": (
            "新緑町電力の運用司令塔へようこそ！新任主任としての初任務は、町の消費電力に"
            "合わせて中央火力の出力を微調整し、周波数60.00Hzを保つことです。\n"
            "操作パネルのスライダーやW/Sキーで火力を制御し、安定供給を維持して黒字売電を達成しましょう！"
        ),
        "events_desc": (
            "[!] 【昼下がりのひととき】(約20秒後)\n"
            "    昼下がりに住宅需要が一時低下。火力を絞って周波数上昇を防げ！\n"
            "[!] 【夕暮れの照明点灯】(約55秒後)\n"
            "    夕暮れで需要微増＆単価アップ。火力を増力して稼ぎまくれ！"
        ),
        "condition_desc": "所持金 1,800万円 達成 (初期資金: 1,500万円)",
        "initial_money": 15000000,
        "target_money": 18000000,
        "target_plants": None,
        "clear_msg": (
            "見事な火力制御です！需給バランスの基礎をしっかりと押さえ、\n"
            "新緑町の安定供給を守り抜きました。初任務クリアおめでとう！"
        ),
        "events": [
            {
                "trigger_time_sec": 20,
                "notice_time_sec": 8,
                "duration_sec": 25,
                "name": "昼下がりのひととき",
                "notice_msg": "【予告】昼下がりで住宅需要が一時低下します\n出力を下げて周波数上昇を防いでください",
                "active_msg": "【需要低下中】中央火力の出力を絞り、\n周波数が60.00Hzを超えないよう調整せよ！",
                "price_multiplier": 0.85,
                "load_multiplier": 0.75,
                "hydro_multiplier": 1.0
            },
            {
                "trigger_time_sec": 55,
                "notice_time_sec": 8,
                "duration_sec": 30,
                "name": "夕暮れの照明点灯",
                "notice_msg": "【予告】夕暮れに伴い照明需要が微増します\n火力を増力して対応してください",
                "active_msg": "【需要微増】出力を上げて60.00Hzをキープ！\n高単価で売電利益を稼ぐチャンス！",
                "price_multiplier": 1.25,
                "load_multiplier": 1.25,
                "hydro_multiplier": 1.0
            }
        ]
    },
    {
        "stage_id": 2,
        "title": "第2話：谷と山の水力パワー",
        "subtitle": "余剰電力の揚水充電とピーク発電",
        "synopsis": (
            "連休で工場が一斉休業し、電気が大幅に余る見込みです！このままでは周波数が急上昇。\n"
            "こんな時こそ「黒岳揚水所」の出番！余剰時は【揚水(PUMP)】で充電吸収し、\n"
            "その後の夕暮れピークには【発電(GEN)】へ切り替えて一気に売電利益を上げましょう！"
        ),
        "events_desc": (
            "[!] 【工場の一斉連休】(約20秒後)\n"
            "    工場休業で需要激減・単価下落。揚水(Sキー)で余剰を急速充電せよ！\n"
            "[!] 【夕暮れの帰宅ラッシュ】(約60秒後)\n"
            "    日没で需要急増＆単価高騰。揚水を発電(Wキー)へ切り替えろ！"
        ),
        "condition_desc": "所持金 2,000万円 達成 (初期資金: 1,600万円)",
        "initial_money": 16000000,
        "target_money": 20000000,
        "target_plants": None,
        "clear_msg": (
            "素晴らしい揚水オペレーション！\n"
            "電気が余る時に充電し、足りない時に売電する揚水の真価を発揮しました！"
        ),
        "events": [
            {
                "trigger_time_sec": 20,
                "notice_time_sec": 8,
                "duration_sec": 30,
                "name": "工場の一斉連休",
                "notice_msg": "【予告】工場が一斉連休に入り電気が余ります\n揚水(PUMP)で充電吸収の準備を！",
                "active_msg": "【余剰電力発生】市場単価急落中！\n揚水(Sキー)で余剰電力を充電し蓄電せよ！",
                "price_multiplier": 0.6,
                "load_multiplier": 0.7,
                "hydro_multiplier": 1.0
            },
            {
                "trigger_time_sec": 60,
                "notice_time_sec": 10,
                "duration_sec": 35,
                "name": "夕暮れの帰宅ラッシュ",
                "notice_msg": "【予告】帰宅ラッシュで需要が急増します\n揚水を発電(GEN)へ切り替えてください！",
                "active_msg": "【電力逼迫・単価高騰】揚水発電(Wキー)と\n火力増力で一気に高額売電せよ！",
                "price_multiplier": 1.6,
                "load_multiplier": 1.45,
                "hydro_multiplier": 1.0
            }
        ]
    },
    {
        "stage_id": 3,
        "title": "第3話：町の発展と新たな力",
        "subtitle": "需要急増に備える発電所新設",
        "synopsis": (
            "新緑町に新興住宅地や商業エリアが開発され、消費電力が大きく増加し始めました！\n"
            "初期3基（火力1・水力1・揚水1）だけでは電力供給が限界を迎えます。\n"
            "売電資金を使い、[＋発電所新設] ボタン（Bキー）の新設メニューから発電所を新たに1基以上建設\n"
            "（合計4基以上を保有）し、増加する需要を支えてください！"
        ),
        "events_desc": (
            "[!] 【新興住宅地の急拡大】(約25秒後)\n"
            "    町の発展によりベース需要が大幅増加。供給不足と周波数低下に警戒！\n"
            "[!] 【商業エリアの夜間営業】(約65秒後)\n"
            "    夜間も高負荷が継続。新設した発電所をフル活用せよ！"
        ),
        "condition_desc": "発電所を合計4基以上保有 ＆ 所持金 2,000万円 達成",
        "initial_money": 17000000,
        "target_money": 20000000,
        "target_plants": {"total": 4},
        "clear_msg": (
            "新発電所の建設・稼働成功！\n"
            "町の急速な拡大に合わせたインフラ拡張を見事に成し遂げました！"
        ),
        "events": [
            {
                "trigger_time_sec": 25,
                "notice_time_sec": 10,
                "duration_sec": 35,
                "name": "新興住宅地の急拡大",
                "notice_msg": "【予告】新興住宅地に入居ラッシュ！需要が激増\n新発電所を建設して供給力を強化せよ！",
                "active_msg": "【大需要発生】消費電力が急増中！\n新設発電所と既存設備を総動員して供給せよ！",
                "price_multiplier": 1.3,
                "load_multiplier": 1.4,
                "hydro_multiplier": 1.0
            },
            {
                "trigger_time_sec": 70,
                "notice_time_sec": 10,
                "duration_sec": 30,
                "name": "商業エリアの夜間営業",
                "notice_msg": "【予告】商業エリアの夜間営業がスタート\n高負荷が持続します",
                "active_msg": "【夜間需要持続】単価高値安定！\n新設発電所をフル稼働させて利益を伸ばせ！",
                "price_multiplier": 1.35,
                "load_multiplier": 1.3,
                "hydro_multiplier": 1.0
            }
        ]
    },
    {
        "stage_id": 4,
        "title": "第4話：激動の気象急変",
        "subtitle": "豪雨と寒波！揚水2拠点大作戦",
        "synopsis": (
            "上流での集中豪雨による豊水と、突発的猛烈寒波という極端な気象急変が予報されています。\n"
            "急激な余剰と不足に対応するため、【+揚水発電所】を追加新設して「揚水2か所体制」を確立してください！\n"
            "2基の揚水所を巧みに連携させ、激しい気象変動の荒波を乗り越えましょう！"
        ),
        "events_desc": (
            "[!] 【ゲリラ豪雨と豊水】(約20秒後)\n"
            "    水力発電量が急増＆市場単価暴落。2基の揚水充電で余剰電力を吸収せよ！\n"
            "[!] 【突発的猛烈寒波】(約65秒後)\n"
            "    暖房需要が爆発＆単価2.2倍！2基の揚水を全開発電させて莫大な利益を掴め！"
        ),
        "condition_desc": "揚水発電所を2か所以上保有 ＆ 所持金 2,500万円 達成",
        "initial_money": 18000000,
        "target_money": 25000000,
        "target_plants": {"pumped_storage": 2},
        "clear_msg": (
            "驚異的な危機対応力です！\n"
            "2拠点の揚水発電所をフル活用し、気象変動のピンチを大チャンスに変えました！"
        ),
        "events": [
            {
                "trigger_time_sec": 20,
                "notice_time_sec": 10,
                "duration_sec": 35,
                "name": "ゲリラ豪雨と豊水",
                "notice_msg": "【予告】上流で豪雨。水力発電量が急増します\n市場単価が暴落するため揚水充電を！",
                "active_msg": "【豊水発生・単価暴落】水力フル稼働！\n2基の揚水充電(PUMP)で余剰を飲み込め！",
                "price_multiplier": 0.5,
                "load_multiplier": 0.85,
                "hydro_multiplier": 1.8
            },
            {
                "trigger_time_sec": 65,
                "notice_time_sec": 12,
                "duration_sec": 40,
                "name": "突発的猛烈寒波",
                "notice_msg": "【予告】超強烈な寒波接近！暖房で電力逼迫！\n市場単価が超高騰する見込みです！",
                "active_msg": "【大寒波襲来・単価爆騰】電力不足の危機！\n2基の揚水を全開(GEN)にして一気に売電せよ！",
                "price_multiplier": 2.2,
                "load_multiplier": 1.6,
                "hydro_multiplier": 0.8
            }
        ]
    },
    {
        "stage_id": 5,
        "title": "最終話：メガシティ・グリッドの夜明け",
        "subtitle": "大都市の繁栄と3000万円の偉業",
        "synopsis": (
            "新緑町はついに大都市へとメガ発展！巨大ハイテク重工業団地も24時間フル操業を開始しました。\n"
            "電力需要の波は過去最大。火力・水力・揚水グリッドを総動員して周波数60.00Hzを死守し、\n"
            "電力会社司令塔としての金字塔【所持金3000万円】を達成してください！"
        ),
        "events_desc": (
            "[!] 【ハイテク工場フル稼働】(約20秒後)\n"
            "    重工業団地が一斉稼働！瞬間大負荷による周波数急低下に最大警戒！\n"
            "[!] 【真夏の猛暑ピーク】(約65秒後)\n"
            "    冷房需要爆発＆市場単価超高騰！全発電所フル稼働で3000万円を突破せよ！"
        ),
        "condition_desc": "所持金 3,000万円 達成 (初期資金: 2,000万円)",
        "initial_money": 20000000,
        "target_money": 30000000,
        "target_plants": None,
        "clear_msg": (
            "おめでとうございます！！全5ステージ完全制覇達成！\n"
            "あなたは新緑町を大都市へと導き、3000万円の偉業を成し遂げた\n"
            "名実ともに伝説の最高電力司令塔です！"
        ),
        "events": [
            {
                "trigger_time_sec": 20,
                "notice_time_sec": 10,
                "duration_sec": 35,
                "name": "ハイテク工場フル稼働",
                "notice_msg": "【予告】新鋭ハイテクコンビナートが突発稼働！\n瞬間の超負荷に備えて出力を上げよ！",
                "active_msg": "【重工業フル稼働】瞬間負荷大！\n周波数の急低下に最大級の警戒を！",
                "price_multiplier": 1.4,
                "load_multiplier": 1.5,
                "hydro_multiplier": 1.0
            },
            {
                "trigger_time_sec": 65,
                "notice_time_sec": 12,
                "duration_sec": 45,
                "name": "真夏の猛暑ピーク",
                "notice_msg": "【予告】猛暑により全域で冷房がフル稼働！\n市場単価が限界まで跳ね上がります！",
                "active_msg": "【猛暑ピーク・単価超高騰】全グリッド総力戦！\n揚水・火力をフル稼働させて3000万円を掴め！",
                "price_multiplier": 2.0,
                "load_multiplier": 1.6,
                "hydro_multiplier": 0.9
            }
        ]
    }
]


def get_stage(stage_id: int) -> dict | None:
    """stage_id (1-indexed) のステージ定義を取得"""
    for s in STORY_STAGES:
        if s["stage_id"] == stage_id:
            return s
    return None


def check_stage_clear(stage: dict, plants: list, money: float, elapsed_time: float) -> tuple[bool, str]:
    """
    ステージクリア条件を満たしているかを判定。
    戻り値: (is_cleared, progress_text)
    """
    conditions_met = True
    progress_parts = []

    # 1. 所持金条件のチェック
    target_money = stage.get("target_money")
    if target_money is not None:
        money_met = (money >= target_money)
        if not money_met:
            conditions_met = False
        progress_parts.append(f"資金: ¥{int(money):,} / ¥{int(target_money):,}")

    # 2. 発電所保有数条件のチェック
    target_plants = stage.get("target_plants")
    if target_plants:
        if "total" in target_plants:
            req_total = target_plants["total"]
            # 建設中を含む有効な発電所総数
            cur_total = len(plants)
            if cur_total < req_total:
                conditions_met = False
            progress_parts.append(f"発電所数: {cur_total}/{req_total}基")
        
        if "pumped_storage" in target_plants:
            req_pump = target_plants["pumped_storage"]
            cur_pump = sum(1 for p in plants if getattr(p, "plant_type", "") == "pumped_storage")
            if cur_pump < req_pump:
                conditions_met = False
            progress_parts.append(f"揚水所: {cur_pump}/{req_pump}基")

        if "thermal" in target_plants:
            req_th = target_plants["thermal"]
            cur_th = sum(1 for p in plants if getattr(p, "plant_type", "") in ("thermal", "advanced_thermal"))
            if cur_th < req_th:
                conditions_met = False
            progress_parts.append(f"火力所: {cur_th}/{req_th}基")

    progress_text = " | ".join(progress_parts)
    return (conditions_met, progress_text)
