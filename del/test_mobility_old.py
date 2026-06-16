"""
RandomWayPoint mobility model test

Snapshots:
  - first hour : every 6 min
  - after that : every 1 hour

Assertions:
  - speed   : actual distance per step == MOVE_SPEED * DT
              (only on steps where node is moving both before and after)
  - pause   : actual pause duration is within [PAUSE_TIME_MIN, PAUSE_TIME_MAX]
              (recorded per event, summarized at the end)
"""

import os
import random
import math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import config
from models.node import Node

# ---- parameters ----
SIM_END         = config.SIM_END
DT              = config.TIME_STEP
NUM_NODES       = 20
SNAPSHOT_6MIN   = 360
SNAPSHOT_HOURLY = 3600
FIRST_HOUR_END  = 3600
TRACK_NODE_ID   = "NODE_00"
OUTPUT_DIR      = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snapshots_mobility")
SPEED_TOL       = 1e-9   # floating-point tolerance for speed check


def fmt_time(t):
    h, rem = divmod(int(t), 3600)
    m, s   = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def save_snapshot(nodes, tracked, t, snap_count):
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.set_xlim(0, config.AREA_WIDTH)
    ax.set_ylim(0, config.AREA_HEIGHT)
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.2)

    pausing_count = sum(1 for n in nodes if n.is_pausing)
    ax.set_title(f"t = {fmt_time(t)}  (N={len(nodes)}, pausing={pausing_count})", fontsize=12)
    ax.set_xlabel("x [m]")
    ax.set_ylabel("y [m]")

    for n in nodes:
        if n.id == tracked.id:
            continue
        if not n.is_pausing:
            ax.scatter(n.x, n.y, c='black', s=20, alpha=0.6, zorder=3)
            ax.annotate("", xy=(n.dest_x, n.dest_y), xytext=(n.x, n.y),
                        arrowprops=dict(arrowstyle='->', color='gray', lw=0.8, alpha=0.4))

    xp = [n.x for n in nodes if n.is_pausing and n.id != tracked.id]
    yp = [n.y for n in nodes if n.is_pausing and n.id != tracked.id]
    if xp:
        ax.scatter(xp, yp, c='black', s=40, marker='x', alpha=0.8, zorder=4,
                   label=f'pausing ({len(xp)})')

    moving_count = len(nodes) - pausing_count
    ax.scatter([], [], c='black', s=20, label=f'moving ({moving_count})')

    if tracked.is_pausing:
        ax.scatter(tracked.x, tracked.y, c='red', s=80, marker='x', zorder=5,
                   label=f'{tracked.id} (pausing)')
    else:
        ax.scatter(tracked.x, tracked.y, c='red', s=60, zorder=5,
                   label=f'{tracked.id} (moving)')
        ax.annotate("", xy=(tracked.dest_x, tracked.dest_y), xytext=(tracked.x, tracked.y),
                    arrowprops=dict(arrowstyle='->', color='red', lw=1.5))

    ax.legend(loc='upper right', fontsize=9)
    ax.text(5, config.AREA_HEIGHT - 25,
            f"moving: {moving_count}  pausing(x): {pausing_count}",
            fontsize=9, bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))

    fname = os.path.join(OUTPUT_DIR, f"snap_{snap_count:03d}_t{int(t):06d}.png")
    plt.savefig(fname, dpi=120, bbox_inches='tight')
    plt.close(fig)
    print(f"  [SNAP] {os.path.basename(fname)}  pausing={pausing_count/len(nodes)*100:.0f}%")


# ---- init ----
os.makedirs(OUTPUT_DIR, exist_ok=True)
random.seed(42)

nodes = []
for i in range(NUM_NODES):
    x = random.uniform(0, config.AREA_WIDTH)
    y = random.uniform(0, config.AREA_HEIGHT)
    node = Node(f"NODE_{i:02d}", x=x, y=y, config=config)
    node.set_new_destination()
    nodes.append(node)

tracked = next(n for n in nodes if n.id == TRACK_NODE_ID)

# prev state for speed check and pause recording
prev_pos     = {n.id: (n.x, n.y)     for n in nodes}
prev_pausing = {n.id: n.is_pausing   for n in nodes}
pause_start  = {}   # node_id -> t when pause began

speed_errors  = []  # (node_id, t, expected, actual)
pause_records = []  # (node_id, duration)

print(f"RandomWayPoint test  (nodes={NUM_NODES})")
print(f"output: {OUTPUT_DIR}/")
print(f"tracking: {TRACK_NODE_ID}  init=({tracked.x:.1f}, {tracked.y:.1f})")
print(f"expected speed: {config.MOVE_SPEED} m/s  "
      f"pause range: [{config.PAUSE_TIME_MIN}, {config.PAUSE_TIME_MAX}] s")
print("-" * 50)

snap_count = 0

for t in range(1, SIM_END + 1):
    for node in nodes:
        node.move(DT)

    for node in nodes:
        was_pausing = prev_pausing[node.id]
        px, py      = prev_pos[node.id]

        # ---- speed check ----
        # only on steps where node was moving before AND still moving after
        if not was_pausing and not node.is_pausing:
            dist     = math.sqrt((node.x - px)**2 + (node.y - py)**2)
            expected = config.MOVE_SPEED * DT
            if abs(dist - expected) > SPEED_TOL:
                speed_errors.append((node.id, t, expected, dist))

        # ---- pause duration recording ----
        if not was_pausing and node.is_pausing:
            # just arrived -> pause started
            pause_start[node.id] = t
            if node.id == TRACK_NODE_ID:
                print(f"  [{fmt_time(t)}] {node.id}: arrived -> pausing  "
                      f"pos=({node.x:.1f},{node.y:.1f})  pause={node.pause_time:.0f}s")

        elif was_pausing and not node.is_pausing:
            # pause ended
            if node.id in pause_start:
                duration = t - pause_start.pop(node.id)
                pause_records.append((node.id, duration))
                ok = config.PAUSE_TIME_MIN <= duration <= config.PAUSE_TIME_MAX
                if not ok:
                    print(f"  [PAUSE ERROR] {node.id} t={fmt_time(t)}  "
                          f"duration={duration}s  "
                          f"range=[{config.PAUSE_TIME_MIN},{config.PAUSE_TIME_MAX}]")
            if node.id == TRACK_NODE_ID:
                print(f"  [{fmt_time(t)}] {node.id}: pause end -> moving  "
                      f"dest=({node.dest_x:.1f},{node.dest_y:.1f})")

        prev_pos[node.id]     = (node.x, node.y)
        prev_pausing[node.id] = node.is_pausing

    # ---- snapshot ----
    if t <= FIRST_HOUR_END:
        if t % SNAPSHOT_6MIN == 0:
            save_snapshot(nodes, tracked, t, snap_count)
            snap_count += 1
    else:
        if t % SNAPSHOT_HOURLY == 0:
            save_snapshot(nodes, tracked, t, snap_count)
            snap_count += 1

# ---- results ----
print(f"\n{'='*50}")
print(f"[DONE] {snap_count} images saved to {OUTPUT_DIR}/")

print(f"\n--- Speed check ---")
if speed_errors:
    print(f"  FAIL: {len(speed_errors)} errors")
    for nid, t, exp, act in speed_errors[:5]:
        print(f"    {nid} t={fmt_time(t)}  expected={exp:.4f}  actual={act:.4f}")
else:
    print(f"  PASS: all moving steps matched {config.MOVE_SPEED} m/s")

print(f"\n--- Pause duration check ---")
if pause_records:
    durations = [d for _, d in pause_records]
    print(f"  samples : {len(durations)}")
    print(f"  min     : {min(durations)}s  (limit >= {config.PAUSE_TIME_MIN}s)")
    print(f"  max     : {max(durations)}s  (limit <= {config.PAUSE_TIME_MAX}s)")
    print(f"  ave    : {sum(durations)/len(durations):.1f}s")
    out_of_range = [(nid, d) for nid, d in pause_records
                    if not (config.PAUSE_TIME_MIN <= d <= config.PAUSE_TIME_MAX)]
    if out_of_range:
        print(f"  FAIL: {len(out_of_range)} out-of-range pauses")
        for nid, d in out_of_range:
            print(f"    {nid}: {d}s")
    else:
        print(f"  PASS: all pauses within [{config.PAUSE_TIME_MIN}, {config.PAUSE_TIME_MAX}] s")
else:
    print("  no completed pauses recorded")
