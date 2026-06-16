"""
シミュレーション可視化スクリプト
ノードの初期配置と親機の位置を表示する
"""
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import random
import math
import sys
sys.path.insert(0, '.')
import config

def visualize_initial(config):
    """初期配置を可視化"""
    fig, ax = plt.subplots(1, 1, figsize=(8, 8))

    # エリア
    ax.set_xlim(0, config.AREA_WIDTH)
    ax.set_ylim(0, config.AREA_HEIGHT)
    ax.set_aspect('equal')
    ax.set_title('DTN Simulation - Initial Placement', fontsize=14)
    ax.set_xlabel('x [m]')
    ax.set_ylabel('y [m]')
    ax.grid(True, alpha=0.3)

    # ノードを生成・配置
    node_x, node_y = [], []
    for _ in range(config.NUM_NODES):
        if config.NODE_SPAWN_AREA == "spawn_points":
            base = random.choice(config.SPAWN_POINTS)
            x = base[0] + random.uniform(-config.SPAWN_RADIUS, config.SPAWN_RADIUS)
            y = base[1] + random.uniform(-config.SPAWN_RADIUS, config.SPAWN_RADIUS)
            x = max(0, min(config.AREA_WIDTH, x))
            y = max(0, min(config.AREA_HEIGHT, y))
        else:
            x = random.uniform(0, config.AREA_WIDTH)
            y = random.uniform(0, config.AREA_HEIGHT)
        node_x.append(x)
        node_y.append(y)

    # 子機をプロット
    ax.scatter(node_x, node_y, c='steelblue', s=20, alpha=0.6,
               label=f'Node (N={config.NUM_NODES})', zorder=3)

    # 子機の通信範囲（数台だけ表示）
    for i in range(min(5, len(node_x))):
        circle = plt.Circle(
            (node_x[i], node_y[i]),
            config.RANGE_NODE_TO_NODE,
            color='steelblue', fill=False, alpha=0.3, linewidth=0.8
        )
        ax.add_patch(circle)

    # 親機をプロット
    for i, (gx, gy) in enumerate(config.GATEWAY_POSITIONS):
        ax.scatter(gx, gy, c='red', s=200, marker='*',
                   label=f'Gateway{i} ({gx},{gy})', zorder=5)
        # 親機の通信範囲
        circle = plt.Circle(
            (gx, gy),
            config.RANGE_NODE_TO_GATEWAY,
            color='red', fill=False, alpha=0.3,
            linewidth=1.5, linestyle='--'
        )
        ax.add_patch(circle)
        ax.annotate(f'GW{i}', (gx, gy),
                    textcoords="offset points", xytext=(10, 10),
                    fontsize=10, color='red', fontweight='bold')

    # 生成場所を表示
    if config.NODE_SPAWN_AREA == "spawn_points":
        for sp in config.SPAWN_POINTS:
            circle = plt.Circle(
                sp, config.SPAWN_RADIUS,
                color='green', fill=True, alpha=0.15,
                linewidth=1, linestyle=':'
            )
            ax.add_patch(circle)
            ax.annotate('Spawn Area', sp,
                        textcoords="offset points", xytext=(5, 5),
                        fontsize=8, color='green')

    ax.legend(loc='upper right', fontsize=9)
    plt.tight_layout()
    # plt.savefig('initial_placement.png', dpi=150)  # 保存する場合はコメントアウトを外す
    plt.show()
    # print("[VIZ] initial_placement.png を保存しました")


if __name__ == "__main__":
    visualize_initial(config)
