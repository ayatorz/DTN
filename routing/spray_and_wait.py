class SprayAndWait:
    """
    Spray and Wait ルーティング
    - Sprayフェーズ：コピー数Lが1より多い間、遭遇したノードにコピーを渡す
    - Waitフェーズ：コピー数が1になったら親機に直接届くまで保持
    """

    def __init__(self, config):
        self.config = config

    def node_to_node(self, node_a, node_b, current_time):
        """
        子機間のメッセージ交換
        node_aのバッファからnode_bに転送できるメッセージを渡す
        """
        forwarded = []

        for msg in list(node_a.buffer):
            # すでに配送済み・TTL切れはスキップ
            if msg.delivered or msg.expired:
                continue

            # Waitフェーズ（コピー1個）はノード間転送しない
            if msg.copies_left <= 1:
                continue

            # 同じメッセージをnode_bがすでに持っていたらスキップ
            b_ids = [m.id for m in node_b.buffer]
            if msg.id in b_ids:
                continue

            # コピーを分割して渡す
            import copy
            new_msg = copy.deepcopy(msg)
            give    = msg.copies_left // 2
            new_msg.copies_left = give
            msg.copies_left    -= give
            new_msg.hops        = msg.hops + 1

            node_b.buffer.append(new_msg)
            node_a.messages_forwarded += 1
            forwarded.append(new_msg)

        return forwarded

    def node_to_gateway(self, node, gateway, current_time):
        """
        子機→親機へのメッセージ配送
        """
        delivered = []

        for msg in list(node.buffer):
            if msg.delivered or msg.expired:
                continue

            msg.hops += 1
            gateway.receive(msg, current_time)
            delivered.append(msg)

        # 配送済みメッセージをバッファから削除
        node.buffer = [m for m in node.buffer if not m.delivered]

        return delivered
