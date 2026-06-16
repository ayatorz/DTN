class RoutingProtocol:
    """
    ルーティングプロトコルの基底クラス
    サブクラスで node_to_node / node_to_gateway を実装する
    """

    def node_to_node(self, node_a, node_b, current_time):
        """子機間のバンドル交換"""
        raise NotImplementedError

    def node_to_gateway(self, node, gateway, current_time):
        """子機から親機へのバンドル配送"""
        raise NotImplementedError
