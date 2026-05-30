import uuid

class Message:
    """
    メッセージクラス
    各ノードが生成・運搬するデータ
    """
    def __init__(self, created_at, source_id, size, ttl):
        self.id          = str(uuid.uuid4())[:8]  # ユニークID
        self.created_at  = created_at             # 生成時刻 [s]
        self.source_id   = source_id              # 送信元ノードID
        self.size        = size                   # メッセージサイズ [byte]
        self.ttl         = ttl                    # 生存時間 [s]
        self.copies_left = 1                      # 残りコピー数（Spray and Wait用）
        self.hops        = 0                      # 中継回数
        self.delivered   = False                  # 配送完了フラグ
        self.delivered_at = None                  # 配送時刻 [s]
        self.expired     = False                  # TTL切れフラグ

    def is_expired(self, current_time):
        """TTL切れかどうか判定"""
        return (current_time - self.created_at) > self.ttl

    def __repr__(self):
        return f"Message(id={self.id}, src={self.source_id}, copies={self.copies_left})"

class Bundle:
    """
    バンドルクラス
    複数のメッセージをまとめたもの
    """
    def __init__(self, created_at, source_id, messages, ttl):
        self.id          = str(uuid.uuid4())[:8]
        self.created_at  = created_at
        self.source_id   = source_id
        self.messages    = messages      # まとめたメッセージリスト
        self.ttl         = ttl
        self.copies_left = 1
        self.hops        = 0
        self.delivered   = False
        self.delivered_at = None
        self.expired     = False

    def is_expired(self, current_time):
        return (current_time - self.created_at) > self.ttl