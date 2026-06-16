import math
import random

from mobility.base import MobilityModel


class RandomWaypoint(MobilityModel):
    """
    Random Waypoint 移動モデル
    - ランダムな目的地に向かって一定速度で移動
    - 到着後はランダムな時間だけ停止し、次の目的地を決める
    """

    def __init__(self, config):
        self.config = config

    def init_node(self, node):
        """ノード生成時に最初の目的地を設定する"""
        self._set_new_destination(node)

    def move(self, node, dt):
        if node.is_pausing:
            node.pause_time -= dt
            if node.pause_time <= 0:
                node.is_pausing = False
                self._set_new_destination(node)
            return

        dx   = node.dest_x - node.x
        dy   = node.dest_y - node.y
        dist = math.sqrt(dx**2 + dy**2)

        if dist <= self.config.MOVE_SPEED * dt:
            node.x          = node.dest_x
            node.y          = node.dest_y
            node.is_pausing = True
            node.pause_time = random.uniform(
                self.config.PAUSE_TIME_MIN,
                self.config.PAUSE_TIME_MAX
            )
        else:
            node.x += (dx / dist) * self.config.MOVE_SPEED * dt
            node.y += (dy / dist) * self.config.MOVE_SPEED * dt

    def _set_new_destination(self, node):
        node.dest_x = random.uniform(0, self.config.AREA_WIDTH)
        node.dest_y = random.uniform(0, self.config.AREA_HEIGHT)
