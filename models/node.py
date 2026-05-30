import math
import random
from models.message import Message

class Node:
    """
    子機ノードクラス
    移動・メッセージ生成・バッファ管理を担う
    """
    def __init__(self, node_id, x, y, config):
        self.id       = node_id
        self.x        = x
        self.y        = y
        self.config   = config

        # 移動関連
        self.dest_x        = x
        self.dest_y        = y
        self.speed         = config.MOVE_SPEED
        self.pause_time    = 0      # 残り停止時間 [s]
        self.is_pausing    = False

        # バッファ（運搬中のメッセージ）
        self.buffer = []

        # 接触クールダウン管理 {相手ノードID: 最後の接触時刻}
        self.contact_log = {}

        # 統計
        self.messages_generated  = 0
        self.messages_forwarded  = 0

    # ==================
    # 移動関連
    # ==================

    def set_new_destination(self):
        """ランダムな目的地を設定（Random Waypoint）"""
        self.dest_x = random.uniform(0, self.config.AREA_WIDTH)
        self.dest_y = random.uniform(0, self.config.AREA_HEIGHT)

    def move(self, dt):
        """1ステップ分移動する"""
        # 停止中
        if self.is_pausing:
            self.pause_time -= dt
            if self.pause_time <= 0:
                self.is_pausing = False
                self.set_new_destination()
            return

        # 目的地までの距離
        dx   = self.dest_x - self.x
        dy   = self.dest_y - self.y
        dist = math.sqrt(dx**2 + dy**2)

        # 目的地に到着
        if dist <= self.speed * dt:
            self.x = self.dest_x
            self.y = self.dest_y
            self.is_pausing = True
            self.pause_time = random.uniform(
                self.config.PAUSE_TIME_MIN,
                self.config.PAUSE_TIME_MAX
            )
        else:
            # 目的地に向かって移動
            self.x += (dx / dist) * self.speed * dt
            self.y += (dy / dist) * self.speed * dt

    # ==================
    # メッセージ関連
    # ==================

    def generate_message(self, current_time):
        """メッセージを生成してバッファに追加"""
        msg = Message(
            created_at = current_time,
            source_id  = self.id,
            size       = self.config.MSG_SIZE,
            ttl        = self.config.MSG_TTL,
        )
        msg.copies_left = self.config.SAW_L
        self.buffer.append(msg)
        self.messages_generated += 1
        return msg

    def remove_expired_messages(self, current_time):
        """TTL切れメッセージをバッファから削除"""
        before = len(self.buffer)
        for msg in self.buffer:
            if msg.is_expired(current_time):
                msg.expired = True
        self.buffer = [m for m in self.buffer if not m.expired]
        return before - len(self.buffer)

    # ==================
    # 接触関連
    # ==================

    def distance_to(self, other):
        """他ノードとの距離を計算"""
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)

    def can_contact(self, other_id, current_time):
        """クールダウン中かどうか確認"""
        if other_id not in self.contact_log:
            return True
        elapsed = current_time - self.contact_log[other_id]
        return elapsed >= self.config.CONTACT_COOLDOWN

    def record_contact(self, other_id, current_time):
        """接触時刻を記録"""
        self.contact_log[other_id] = current_time

    def __repr__(self):
        return f"Node(id={self.id}, x={self.x:.1f}, y={self.y:.1f}, buf={len(self.buffer)})"

# __init__に追加
self.data_buffer  = []   # 生成したデータ（バンドル化前）
self.bundle_buffer = []  # バンドル化済み（SCF転送用）

# メソッドを追加
def generate_data(self, current_time):
    """データを1件生成してdata_bufferに追加"""
    from models.message import Message
    msg = Message(created_at=current_time, source_id=self.id,
                  size=self.config.MSG_SIZE, ttl=self.config.MSG_TTL)
    self.data_buffer.append(msg)

def bundle_data(self, current_time):
    """data_bufferからBUNDLE_SIZE件まとめてバンドル化"""
    from models.message import Bundle
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