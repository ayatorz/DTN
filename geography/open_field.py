import random

from geography.base import Geography


class OpenField(Geography):
    """
    障害物のない2次元平面
    ノードはエリア内を自由に移動できる
    生成位置は spawn_points またはエリア全体からランダムに決まる
    """

    def __init__(self, config):
        self.config = config

    def get_spawn_position(self):
        if self.config.NODE_SPAWN_AREA == "spawn_points":
            base = random.choice(self.config.SPAWN_POINTS)
            x = base[0] + random.uniform(-self.config.SPAWN_RADIUS, self.config.SPAWN_RADIUS)
            y = base[1] + random.uniform(-self.config.SPAWN_RADIUS, self.config.SPAWN_RADIUS)
            return self.clamp(x, y)
        else:
            x = random.uniform(0, self.config.AREA_WIDTH)
            y = random.uniform(0, self.config.AREA_HEIGHT)
            return x, y

    def clamp(self, x, y):
        x = max(0, min(self.config.AREA_WIDTH,  x))
        y = max(0, min(self.config.AREA_HEIGHT, y))
        return x, y
