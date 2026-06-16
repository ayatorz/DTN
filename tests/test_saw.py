"""
Spray and Wait (Source Spray) 動作検証

N=30, T=28800s のシミュレーションを動かし，
1本のバンドルの「一生」を追うことで S&W が正しく動いているかを確認する。

確認項目
  1. あるバンドルが L 個以下しか広がっていないか（コピー保存則）
  2. 配ったのは送信元ノードだけか（Source Spray）
  3. そのバンドルが最終的に親機に届いたか（配送確認）
  4. 全体の配送サマリ
"""

import os
import sys
import random
from collections import Counter
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import config
from simulator import Simulator
from routing.spray_and_wait import SprayAndWait
from mobility.random_waypoint import RandomWaypoint
from geography.open_field import OpenField

# ---- シミュレーション設定 ----
config.NUM_NODES       = 60
config.SIM_END         = 28800
config.SAW_L           = 6
config.NODE_SPAWN_AREA = "random"

gw_x = random.uniform(0, config.AREA_WIDTH)
gw_y = random.uniform(0, config.AREA_HEIGHT)
config.GATEWAY_POSITIONS = [(gw_x, gw_y)]

random.seed(42)

def fmt_time(t):
    h, rem = divmod(int(t), 3600)
    m, s   = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

routing   = SprayAndWait(config)
mobility  = RandomWaypoint(config)
geography = OpenField(config)

sim = Simulator(config, mobility=mobility, geography=geography, routing=routing)

print("=" * 60)
print("Spray and Wait (Source Spray) 動作検証")
print(f"  N={config.NUM_NODES}  T={config.SIM_END}s ({config.SIM_END//3600}h)")
print(f"  L={config.SAW_L}  area={config.AREA_WIDTH}x{config.AREA_HEIGHT}m")
print(f"  gateway 1台  pos=({gw_x:.1f}, {gw_y:.1f})")
print("=" * 60)

sim.run()

log     = routing.transfer_log
dlv_log = routing.delivery_log

if not log:
    print("\n転送ログが空 — ノード間接触がなかった可能性があります")
    raise SystemExit

# ============================================================
# 0. 転送ログ（最初の50件・最後の50件）
# ============================================================
def print_log_entries(entries):
    print(f"  {'時刻':<10}  {'送り元':<8}  {'受け取り':<8}  {'bundle':<10}  {'送り元残コピー'}")
    print(f"  {'-'*55}")
    for t, frm, to, bid, c in entries:
        print(f"  {fmt_time(t):<10}  {frm:<8}  {to:<8}  {bid:<10}  {c}")

print("\n" + "=" * 60)
print("0. 転送ログ")
print("=" * 60)
print(f"--- 最初の50件 ---")
print_log_entries(log[:50])
if len(log) > 50:
    print(f"\n--- 最後の50件 ---")
    print_log_entries(log[-50:])
print(f"\n  全 {len(log)} 件")

def print_bundle_trace(label, bid):
    src = next((frm for _, frm, _, b, _ in log if b == bid), None)
    if src is None:
        src = next((s for _, _, _, b, s, _, _ in dlv_log if b == bid), None)
    events = [(t, frm, to, c) for t, frm, to, b, c in log if b == bid]
    dlv = [(t, nid, gw, delay, hops)
           for t, nid, gw, b, _, delay, hops in dlv_log if b == bid]

    print("\n" + "=" * 60)
    print(f"{label}  bundle: {bid}  送信元: {src}  L={config.SAW_L}")
    print("=" * 60)

    if events:
        print(f"\n--- 転送履歴 ({len(events)} 件) ---")
        print(f"  {'時刻':<10}  {'送り元':<8}  {'受け取り':<8}  {'送り元残コピー'}")
        print(f"  {'-'*48}")
        for t, frm, to, c in events:
            print(f"  {fmt_time(t):<10}  {frm:<8}  {to:<8}  {c}")
    else:
        print(f"\n  転送履歴なし（生成後に接触がなかった）")

    print(f"\n--- 配送確認 ---")
    if dlv:
        t, nid, gw, delay, hops = dlv[0]
        print(f"  到達時刻    : {fmt_time(t)}")
        print(f"  届けたノード: {nid}  →  親機 {gw}")
        print(f"  遅延        : {delay}s  ({delay//60}分{delay%60}秒)")
        print(f"  ホップ数    : {hops}")
    else:
        print(f"  未配送 (TTL={config.MSG_TTL}s, T={config.SIM_END}s)")

# 追跡バンドル1: ログに最初に登場したバンドル（配達済みとは限らない）
first_bid = log[0][3]

# 追跡バンドル2: 配達済みのバンドルから1件選ぶ
delivered_bids = [bid for _, _, _, bid, _, _, _ in dlv_log]
delivered_bid  = next((b for b in delivered_bids if b != first_bid), None)

# ============================================================
# 1. バンドル追跡
# ============================================================
print_bundle_trace("1. 最初に転送されたバンドル", first_bid)
if delivered_bid:
    print_bundle_trace("2. 最初に親機に届いたバンドル", delivered_bid)
else:
    print("\n配達済みバンドルが見つかりませんでした")

# ============================================================
# 5. 全体サマリ
# ============================================================
print("\n" + "=" * 60)
print("全体サマリ")
print("=" * 60)

gen  = sim.total_bundles_generated
dlv  = sim.total_delivered
exp  = sim.total_expired
rate = dlv / gen * 100 if gen > 0 else 0
avg_delay = sum(sim.delay_list) / len(sim.delay_list) if sim.delay_list else 0
avg_hops  = sum(sim.hop_list)   / len(sim.hop_list)   if sim.hop_list  else 0

print(f"  生成バンドル数  : {gen}")
print(f"  親機到達数      : {dlv}  ({rate:.1f}%)")
print(f"  TTL 切れ(コピー): {exp}  (最大 {gen * config.SAW_L} コピー中)")
print(f"  平均遅延        : {avg_delay:.1f} s")
print(f"  平均ホップ数    : {avg_hops:.2f}")
print(f"  転送イベント総数: {len(log)}")
print("=" * 60)
