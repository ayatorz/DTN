class Geography:
    """
    地理モデルの基底クラス
    サブクラスで get_spawn_position / clamp を実装する
    """

    def get_spawn_position(self):
        """ノード生成位置を返す (x, y)"""
        raise NotImplementedError

    def clamp(self, x, y):
        """座標をエリア内に収める"""
        raise NotImplementedError
