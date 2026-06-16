import math

class Gateway:
    """
    親機（ゲートウェイ）クラス
    子機からメッセージを受信してサーバに送る役割
    """
    def __init__(self, gateway_id, x, y, config):
        self.id     = gateway_id
        self.x      = x
        self.y      = y
        self.config = config

        # 受信したメッセージ
        self.received_messages = []

    def distance_to_node(self, node):
        """子機との距離を計算"""
        return math.sqrt((self.x - node.x)**2 + (self.y - node.y)**2)

    def in_range(self, node):
        """子機が通信範囲内かどうか判定"""
        return self.distance_to_node(node) <= self.config.RANGE_NODE_TO_GATEWAY

    def receive(self, msg, current_time):
        """メッセージを受信する"""
        msg.delivered    = True
        msg.delivered_at = current_time
        self.received_messages.append(msg)

    def __repr__(self):
        return f"Gateway(id={self.id}, x={self.x}, y={self.y}, received={len(self.received_messages)})"
