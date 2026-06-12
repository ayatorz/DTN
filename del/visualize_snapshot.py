"""
スナップショット可視化スクリプト
単位時間ごとにノードの位置・状態を画像出力する

置き場所: dtn_sim/visualize_snapshot.py
出力先  : dtn_sim/snapshots/
実行方法: python3 visualize_snapshot.py

色の意味:
  青  (steelblue) : バンドルを持っているノード
  緑  (green)     : 親機に届けたノード
  灰  (gray)      : バンドルなし・未配送
  赤★             : 親機（ゲートウェイ）
"""

import os
import sys
import math
import random
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import importlib.util

# configをファイルパスで直接読み込む
_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("dtn_config", os.path.join(_HERE, "config.py"))
cfg   = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cfg)

# ==================
# 設定（ここを変える）
# ==================
SNAPSHOT_INTERVAL = 3600   # スナップショット間隔 [s]（1時間ごと）
OUTPUT_DIR        = os.path.join(_HERE, "snapshots")


# ==================
# 可視化用簡易ノード
# ==================
class SnapNode:
    def __init__(self, node_id, x, y):
        self.id         = node_id
        self.x          = x
        self.y          = y
        self.dest_x     = x
        self.dest_y     = y
        self.pause_time = 0
        self.is_pausing = False
        self.has_bundle = True   # バンドルあり（青）
        self.delivered  = False  # 配送済み（緑）

    def set_new_destination(self):
        self.dest_x = random.uniform(0, cfg.AREA_WIDTH)
        self.dest_y = random.uniform(0, cfg.AREA_HEIGHT)

    def move(self, dt):
        if self.is_pausing:
            self.pause_time -= dt
            if self.pause_time <= 0:
                self.is_pausing = False
                self.set_new_destination()
            return
        dx   = self.dest_x - self.x
        dy   = self.dest_y - self.y
        dist = math.sqrt(dx**2 + dy**2)
        if dist <= cfg.MOVE_SPEED * dt:
            self.x          = self.dest_x
            self.y          = self.dest_y
            self.is_pausing = True
            self.pause_time = random.uniform(cfg.PAUSE_TIME_MIN, cfg.PAUSE_TIME_MAX)
        else:
            self.x += (dx / dist) * cfg.MOVE_SPEED * dt
            self.y += (dy / dist) * cfg.MOVE_SPEED * dt


# ==================
# メイン処理
# ==================
def run_with_snapshots():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ノード生成
    nodes = []
    for i in range(cfg.NUM_NODES):
        if cfg.NODE_SPAWN_AREA == "spawn_points":
            base = random.choice(cfg.SPAWN_POINTS)
            x = base[0] + random.uniform(-cfg.SPAWN_RADIUS, cfg.SPAWN_RADIUS)
            y = base[1] + random.uniform(-cfg.SPAWN_RADIUS, cfg.SPAWN_RADIUS)
            x = max(0, min(cfg.AREA_WIDTH, x))
            y = max(0, min(cfg.AREA_HEIGHT, y))
        else:
            x = random.uniform(0, cfg.AREA_WIDTH)
            y = random.uniform(0, cfg.AREA_HEIGHT)
        node = SnapNode(f"N{i}", x, y)
        node.set_new_destination()
        nodes.append(node)

    gateways   = cfg.GATEWAY_POSITIONS
    t          = cfg.SIM_START
    snap_count = 0

    while t <= cfg.SIM_END:

        # スナップショットを撮る
        if int(t) % SNAPSHOT_INTERVAL == 0:
            _save_snapshot(nodes, gateways, t, snap_count)
            snap_count += 1

        # ノード移動
        for node in nodes:
            node.move(cfg.TIME_STEP)

        # 親機到達チェック
        for node in nodes:
            if not node.has_bundle:
                continue
            for gx, gy in gateways:
                dist = math.sqrt((node.x - gx)**2 + (node.y - gy)**2)
                if dist <= cfg.RANGE_NODE_TO_GATEWAY:
                    node.delivered  = True
                    node.has_bundle = False
                    break

        t += cfg.TIME_STEP

    print(f"\n[DONE] {snap_count}枚を {OUTPUT_DIR}/ に保存しました")


# ==================
# スナップショット保存
# ==================
def _save_snapshot(nodes, gateways, current_time, snap_count):
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.set_xlim(0, cfg.AREA_WIDTH)
    ax.set_ylim(0, cfg.AREA_HEIGHT)
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.2)

    hours   = int(current_time // 3600)
    minutes = int((current_time % 3600) // 60)
    ax.set_title(
        f"t = {hours:02d}:{minutes:02d}  (N={cfg.NUM_NODES}, GW={len(gateways)})",
        fontsize=12
    )
    ax.set_xlabel("x [m]")
    ax.set_ylabel("y [m]")

    # ノードを状態別に色分け
    xb = [n.x for n in nodes if n.has_bundle]
    yb = [n.y for n in nodes if n.has_bundle]
    xd = [n.x for n in nodes if n.delivered]
    yd = [n.y for n in nodes if n.delivered]
    xe = [n.x for n in nodes if not n.has_bundle and not n.delivered]
    ye = [n.y for n in nodes if not n.has_bundle and not n.delivered]

    if xb: ax.scatter(xb, yb, c='steelblue', s=15, alpha=0.7, label=f'Bundle ({len(xb)})',    zorder=3)
    if xd: ax.scatter(xd, yd, c='green',     s=15, alpha=0.7, label=f'Delivered ({len(xd)})', zorder=3)
    if xe: ax.scatter(xe, ye, c='gray',       s=10, alpha=0.4, label=f'Empty ({len(xe)})',     zorder=2)

    # 親機（赤★）と通信範囲
    for i, (gx, gy) in enumerate(gateways):
        ax.scatter(gx, gy, c='red', s=200, marker='*', zorder=5)
        ax.annotate(f'GW{i}', (gx, gy), textcoords="offset points",
                    xytext=(8, 8), fontsize=9, color='red', fontweight='bold')
        circle = plt.Circle((gx, gy), cfg.RANGE_NODE_TO_GATEWAY,
                             color='red', fill=False, alpha=0.25,
                             linewidth=1.2, linestyle='--')
        ax.add_patch(circle)

    ax.legend(loc='upper right', fontsize=8)

    total = len(nodes)
    rate  = len(xd) / total * 100 if total > 0 else 0
    ax.text(5, cfg.AREA_HEIGHT - 30, f"Delivery rate: {rate:.1f}%",
            fontsize=10, color='darkgreen',
            bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))

    fname = os.path.join(OUTPUT_DIR, f"snapshot_{snap_count:03d}_t{int(current_time):06d}.png")
    plt.savefig(fname, dpi=120, bbox_inches='tight')
    plt.close(fig)
    print(f"  [SNAP] {os.path.basename(fname)}  配送率={rate:.1f}%")


if __name__ == "__main__":
    print(f"スナップショット間隔 : {SNAPSHOT_INTERVAL}s ({SNAPSHOT_INTERVAL//3600}時間ごと)")
    print(f"出力先              : {OUTPUT_DIR}/")
    print(f"ノード数            : {cfg.NUM_NODES}")
    print(f"実行時間            : {cfg.SIM_END}s ({cfg.SIM_END//3600}時間)")
    print("-" * 40)
    run_with_snapshots()
