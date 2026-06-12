import math
from models.message import Message, Bundle


class Node:
    """
    子機ノードクラス
    データ生成・バンドル化・バッファ管理・接触判定を担う
    移動ロジックは MobilityModel に委譲する
    """
    def __init__(self, node_id, x, y, config):
        self.id     = node_id
        self.x      = x
        self.y      = y
        self.config = config

        # 移動状態（MobilityModel が読み書きする）
        self.dest_x     = x
        self.dest_y     = y
        self.pause_time = 0
        self.is_pausing = False

        # データバッファ（バンドル化前の生データ）
        self.data_buffer = []

        # バンドルバッファ（SCF転送単位）
        self.bundle_buffer = []

        # 接触クールダウン管理 {相手ノードID: 最後の接触時刻}
        self.contact_log = {}

        # 統計
        self.data_generated    = 0
        self.bundles_generated = 0
        self.bundles_forwarded = 0

    # ==================
    # データ・バンドル生成
    # ==================

    def generate_data(self, current_time):
        msg = Message(
            created_at = current_time,
            source_id  = self.id,
            size       = self.config.MSG_SIZE,
            ttl        = self.config.MSG_TTL,
        )
        self.data_buffer.append(msg)
        self.data_generated += 1

    def bundle_data(self, current_time):
        while len(self.data_buffer) >= self.config.BUNDLE_SIZE:
            msgs = self.data_buffer[:self.config.BUNDLE_SIZE]
            self.data_buffer = self.data_buffer[self.config.BUNDLE_SIZE:]
            bundle = Bundle(
                created_at = current_time,
                source_id  = self.id,
                messages   = msgs,
                ttl        = self.config.MSG_TTL,
            )
            bundle.copies_left = self.config.SAW_L
            self.bundle_buffer.append(bundle)
            self.bundles_generated += 1

    def remove_expired_bundles(self, current_time):
        before = len(self.bundle_buffer)
        for b in self.bundle_buffer:
            if b.is_expired(current_time):
                b.expired = True
        self.bundle_buffer = [b for b in self.bundle_buffer if not b.expired]
        return before - len(self.bundle_buffer)

    # ==================
    # 接触関連
    # ==================

    def distance_to(self, other):
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)

    def can_contact(self, other_id, current_time):
        if other_id not in self.contact_log:
            return True
        return (current_time - self.contact_log[other_id]) >= self.config.CONTACT_COOLDOWN

    def record_contact(self, other_id, current_time):
        self.contact_log[other_id] = current_time

    def __repr__(self):
        return f"Node(id={self.id}, x={self.x:.1f}, y={self.y:.1f}, bundles={len(self.bundle_buffer)})"
