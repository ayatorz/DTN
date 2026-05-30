import copy

class SprayAndWait:
    """
    Spray and Wait ルーティング
    バンドル単位で転送する
    - Sprayフェーズ：copies_left > 1 の間、遭遇ノードにコピーを渡す
    - Waitフェーズ：copies_left = 1 になったら親機に直接届くまで保持
    """

    def __init__(self, config):
        self.config = config

    def node_to_node(self, node_a, node_b, current_time):
        """
        子機間のバンドル交換
        双方向に転送を試みる
        """
        forwarded = []

        for bundle in list(node_a.bundle_buffer):
            if bundle.delivered or bundle.expired:
                continue

            # Waitフェーズはノード間転送しない
            if bundle.copies_left <= 1:
                continue

            # node_bがすでに同じバンドルを持っていたらスキップ
            b_ids = [b.id for b in node_b.bundle_buffer]
            if bundle.id in b_ids:
                continue

            # コピーを分割して渡す
            new_bundle = copy.deepcopy(bundle)
            give = bundle.copies_left // 2
            new_bundle.copies_left = give
            bundle.copies_left    -= give
            new_bundle.hops        = bundle.hops + 1

            node_b.bundle_buffer.append(new_bundle)
            node_a.bundles_forwarded += 1
            forwarded.append(new_bundle)

        return forwarded

    def node_to_gateway(self, node, gateway, current_time):
        """
        子機→親機へのバンドル配送
        """
        delivered = []

        for bundle in list(node.bundle_buffer):
            if bundle.delivered or bundle.expired:
                continue

            bundle.hops += 1
            gateway.receive(bundle, current_time)
            delivered.append(bundle)

        # 配送済みをバッファから削除
        node.bundle_buffer = [b for b in node.bundle_buffer if not b.delivered]

        return delivered
