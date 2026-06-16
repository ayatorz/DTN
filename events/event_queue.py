import heapq

class Event:
    """
    イベントクラス
    シミュレーション中に発生するイベントを表す
    """
    # イベントの種類
    MSG_GENERATE  = "MSG_GENERATE"   # メッセージ生成
    NODE_MOVE     = "NODE_MOVE"      # ノード移動
    NODE_CONTACT  = "NODE_CONTACT"   # ノード間接触
    GW_CONTACT    = "GW_CONTACT"     # 親機との接触
    TTL_CHECK     = "TTL_CHECK"      # TTL確認

    def __init__(self, time, event_type, data=None):
        self.time       = time        # 発生時刻
        self.event_type = event_type  # イベント種別
        self.data       = data        # 付随データ

    def __lt__(self, other):
        """優先度キュー用の比較（時刻が早い順）"""
        return self.time < other.time

    def __repr__(self):
        return f"Event(t={self.time}, type={self.event_type})"


class EventQueue:
    """
    イベントキュー
    時刻順にイベントを管理する優先度キュー
    """
    def __init__(self):
        self._queue = []

    def push(self, event):
        """イベントを追加"""
        heapq.heappush(self._queue, event)

    def pop(self):
        """最も早いイベントを取り出す"""
        return heapq.heappop(self._queue)

    def is_empty(self):
        return len(self._queue) == 0

    def __len__(self):
        return len(self._queue)
