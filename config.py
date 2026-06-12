# ===========================
# 固定パラメータ（実験間で変わらないもの）
# 実験変数（ノード数・時間・モデル等）は main.py の引数で指定する
# ===========================

# --- エリア設定 ---
AREA_WIDTH  = 600
AREA_HEIGHT = 600

# --- 時間設定 ---
SIM_START = 0
TIME_STEP = 1

# --- ノード生成設定 ---
NODE_SPAWN_MODE = "all_at_once"   # "all_at_once" or "time_based"
NODE_SPAWN_AREA = "spawn_points"  # "random" or "spawn_points"

SPAWN_POINTS = [
    (300, 50),
    (100, 300),
]
SPAWN_RADIUS = 30

# --- 移動パラメータ ---
MOVE_SPEED     = 1.1
PAUSE_TIME_MIN = 300
PAUSE_TIME_MAX = 2400

# --- 通信範囲 ---
RANGE_NODE_TO_NODE    = 10
RANGE_NODE_TO_GATEWAY = 100
CONTACT_COOLDOWN      = 60

# --- 親機位置 ---
GATEWAY_PATTERN_A = [(300, 300)]
GATEWAY_PATTERN_B = [(150, 100), (450, 100)]
GATEWAY_POSITIONS = GATEWAY_PATTERN_B

# --- メッセージ・バンドル ---
MSG_GENERATION_INTERVAL = 10
BUNDLE_INTERVAL         = 30
BUNDLE_SIZE             = 3
MSG_SIZE                = 120
MSG_TTL                 = 1500
