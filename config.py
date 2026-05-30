# ===========================
# シミュレーションパラメータ設定
# ===========================

# --- エリア設定 ---
AREA_WIDTH  = 600       # エリア横幅 [m]
AREA_HEIGHT = 600       # エリア縦幅 [m]

# --- 時間設定 ---
SIM_START   = 0         # シミュレーション開始時刻 [s]
SIM_END     = 28800     # シミュレーション終了時刻 [s] (8時間)
TIME_STEP   = 1         # シミュレーションのステップ時間 [s]

# --- ノード設定 ---
NUM_NODES   = 200       # 子機（ノード）の数

# ノード生成方法: "all_at_once" or "time_based"
NODE_SPAWN_MODE = "all_at_once"

# time_basedの場合：時間帯ごとの生成数
# 例: {0: 50, 3600: 50, 7200: 50, 10800: 50} → 1時間ごとに50台
NODE_SPAWN_SCHEDULE = {
    0:     20,
    3600:  60,
    7200:  100,
    10800: 20,
}

# ノード生成場所
# "random": エリア全体にランダム生成
# "spawn_points": 指定座標付近に生成
NODE_SPAWN_AREA = "random"

# 生成座標リスト（バスロータリー・駐車場付近を想定）
SPAWN_POINTS = [
    (30, 500),   # バスロータリー付近
    (500,500 ),  # 駐車場付近
]
SPAWN_RADIUS = 30  # 生成座標からのばらつき半径 [m]

# --- 移動モデル設定 ---
MOVE_SPEED      = 1.1    # 移動速度 [m/s]
PAUSE_TIME_MIN  = 300    # 目的地での最小停止時間 [s] (5分)
PAUSE_TIME_MAX  = 2400   # 目的地での最大停止時間 [s] (40分)

# --- 通信範囲設定 ---
RANGE_NODE_TO_NODE    = 10   # 子機間通信範囲 [m]
RANGE_NODE_TO_GATEWAY = 100  # 子機→親機通信範囲 [m]

# 接触クールダウン（同じノード同士の再接触を防ぐ時間）[s]
CONTACT_COOLDOWN = 60


## パターンA：中央1台
GATEWAY_PATTERN_A = [
    (300, 300),
]

# パターンB：入口付近2台（現在使用中）
GATEWAY_PATTERN_B = [
    (550,300),  # 6号館入口付近
    (30,550),   # 8号館入口付近
]

# 生成パターンの切り替え
GATEWAY_POSITIONS = GATEWAY_PATTERN_B


# --- メッセージ設定 ---
MSG_GENERATION_INTERVAL = 10    # メッセージ発生頻度 [s]
MSG_SIZE                = 120   # メッセージサイズ [byte]
MSG_TTL                 = 1500  # メッセージ生存時間 [s] (25分)

# --- Spray and Wait設定 ---
SAW_L = 6  # コピー数上限

# --- 出力設定 ---
OUTPUT_TERMINAL = True   # ターミナルへの出力
# csvの保存
# OUTPUT_CSV      = True   # CSV出力
# OUTPUT_CSV_PATH = "result.csv"
