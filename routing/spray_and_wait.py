import copy

from routing.base import RoutingProtocol


class SprayAndWait(RoutingProtocol):
    """
    Source Spray and Wait ルーティング

    - Spray フェーズ: 送信元ノードが copies_left > 1 の間，
                     出会ったノードに 1 コピーずつ渡す
                     受け取ったノードは copies_left=1 で即 Wait フェーズ
    - Wait フェーズ: copies_left=1 になったら親機に直接届くまで保持
    """

    def __init__(self, config):
        self.config       = config
        self.transfer_log = []   # (time, from_id, to_id, bundle_id, src_copies_after)
        self.delivery_log = []   # (time, node_id, gw_id, bundle_id, source_id, delay, hops)

    def node_to_node(self, node_a, node_b, current_time):
        forwarded = []

        for bundle in list(node_a.bundle_buffer):
            if bundle.delivered or bundle.expired:
                continue

            if bundle.copies_left <= 1:
                continue

            b_ids = [b.id for b in node_b.bundle_buffer]
            if bundle.id in b_ids:
                continue

            # Source Spray: 1 コピーずつ渡す，受け取り側は copies=1
            new_bundle             = copy.deepcopy(bundle)
            new_bundle.copies_left = 1
            new_bundle.hops        = bundle.hops + 1
            bundle.copies_left    -= 1

            node_b.bundle_buffer.append(new_bundle)
            node_a.bundles_forwarded += 1
            forwarded.append(new_bundle)

            self.transfer_log.append(
                (current_time, node_a.id, node_b.id, bundle.id, bundle.copies_left)
            )

        return forwarded

    def node_to_gateway(self, node, gateway, current_time):
        delivered = []

        for bundle in list(node.bundle_buffer):
            if bundle.delivered or bundle.expired:
                continue

            bundle.hops += 1
            gateway.receive(bundle, current_time)
            delivered.append(bundle)
            self.delivery_log.append((
                current_time, node.id, gateway.id, bundle.id,
                bundle.source_id, current_time - bundle.created_at, bundle.hops
            ))

        node.bundle_buffer = [b for b in node.bundle_buffer if not b.delivered]
        return delivered
