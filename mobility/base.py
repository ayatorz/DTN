class MobilityModel:
    """
    移動モデルの基底クラス
    サブクラスで init_node / move を実装する
    """

    def init_node(self, node):
        """ノード生成時に呼ぶ（初期目的地の設定など）"""
        pass

    def move(self, node, dt):
        """1ステップ分ノードを移動させる"""
        pass
