import uuid


class Message:
    """
    メッセージクラス
    各ノードが生成する1件のデータ（バンドル化前）
    """
    def __init__(self, created_at, source_id, size, ttl):
        self.id          = str(uuid.uuid4())[:8]
        self.created_at  = created_at
        self.source_id   = source_id
        self.size        = size
        self.ttl         = ttl

    def is_expired(self, current_time):
        return (current_time - self.created_at) > self.ttl

    def __repr__(self):
        return f"Message(id={self.id}, src={self.source_id})"


class Bundle:
    """
    バンドルクラス
    複数のメッセージをまとめてSCFで転送する単位
    """
    def __init__(self, created_at, source_id, messages, ttl):
        self.id           = str(uuid.uuid4())[:8]
        self.created_at   = created_at
        self.source_id    = source_id
        self.messages     = messages     # まとめたMessageのリスト
        self.ttl          = ttl
        self.copies_left  = 1            # 残りコピー数（Spray and Wait用）
        self.hops         = 0            # 中継回数
        self.delivered    = False        # 配送完了フラグ
        self.delivered_at = None         # 配送時刻 [s]
        self.expired      = False        # TTL切れフラグ

    def is_expired(self, current_time):
        return (current_time - self.created_at) > self.ttl

    def __repr__(self):
        return f"Bundle(id={self.id}, src={self.source_id}, msgs={len(self.messages)}, copies={self.copies_left})"
