"""
Spray and Wait 結合テスト（pytest + 発表用ログ出力版）

単体テスト（test_saw_unit.py）が関数を1つずつ孤立して確認するのに対し，
こちらは Simulator を丸ごと回し，「移動 → 接触 → 転送 → 配送 → TTL」が
すべて組み合わさった状態で，全体を通して成り立つべき不変条件を確認する。

シミュレーションを1回だけ回し（モジュール読み込み時），その結果に対して
各テストが assert で「こうなっていれば正しく動いている」を判定する。
"""

import os
import sys
import random
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import config
from simulator import Simulator
from routing.spray_and_wait import SprayAndWait
from mobility.random_waypoint import RandomWaypoint
from geography.open_field import OpenField

results = []  # (test_name, passed)


# ============================================================
# シミュレーションを1回だけ回して結果を共有する
#   テスト用に軽め（N=30, T=2h）に設定する
# ============================================================
def _run_simulation():
    config.NUM_NODES       = 30
    config.SIM_END         = 7200
    config.SAW_L           = 6
    config.NODE_SPAWN_AREA = "random"
    config.GATEWAY_POSITIONS = [(300, 300)]

    random.seed(42)

    routing   = SprayAndWait(config)
    mobility  = RandomWaypoint(config)
    geography = OpenField(config)

    sim = Simulator(config, mobility=mobility, geography=geography, routing=routing)
    sim.run()
    return sim, routing


print("=" * 60)
print("Spray and Wait 結合テスト（シミュレーション実行中…）")
print("=" * 60)

SIM, ROUTING = _run_simulation()
TRANSFER_LOG = ROUTING.transfer_log   # (time, from_id, to_id, bundle_id, src_copies_after)
DELIVERY_LOG = ROUTING.delivery_log   # (time, node_id, gw_id, bundle_id, source_id, delay, hops)
L = config.SAW_L


def format_value(v, indent=4):
    if isinstance(v, dict):
        lines = []
        for k, vv in v.items():
            lines.append(" " * indent + f"{k}: {format_value(vv, indent + 4) if isinstance(vv, dict) else vv}")
        return "\n" + "\n".join(lines)
    return str(v)


def report(name, description, params, expected, actual, passed):
    results.append((name, passed))
    mark = "PASS" if passed else "FAIL"
    print(f"\n[{mark}] {name}")
    print(f"  確認内容: {description}")
    print(f"  パラメータ: {params}")
    print(f"  期待値    :{format_value(expected)}")
    print(f"  実際の結果:{format_value(actual)}")


def _transfers_by_bundle():
    """bundle_id ごとに転送イベントをまとめる"""
    by_bundle = defaultdict(list)
    for t, frm, to, bid, copies_after in TRANSFER_LOG:
        by_bundle[bid].append((t, frm, to, copies_after))
    return by_bundle


# ============================================================
# 0. 前提チェック
#
# 【目的】このあとのテスト1〜4が「中身のあるデータ」を検査できているか，
#         その土台を確認する。
# 【なぜ必要か】もし接触が一度も起きなければ転送ログは空になり，
#         テスト1・2は「検査対象ゼロ件」で見せかけのPASSをしてしまう。
#         それを防ぐため，まず生成と転送が実際に発生したことを保証する。
# 【確認項目】
#   - バンドルが1つ以上生成されたか（total_bundles_generated > 0）
#   - 転送が1回以上発生したか（transfer_log が空でない）
# ============================================================
def test_simulation_produced_activity():
    expected = {"バンドル生成あり": True, "転送イベントあり": True}
    actual   = {"バンドル生成あり": SIM.total_bundles_generated > 0,
                "転送イベントあり": len(TRANSFER_LOG) > 0}
    passed = (actual == expected)
    report("0. 生成・転送が起きているか",
           "シミュレーションでバンドル生成と転送が実際に発生している（テストの土台が成立しているか）",
           {"生成数": SIM.total_bundles_generated, "転送数": len(TRANSFER_LOG)},
           expected, actual, passed)
    assert SIM.total_bundles_generated > 0, "バンドルが1つも生成されていない"
    assert len(TRANSFER_LOG) > 0, "転送イベントが1件も発生していない（接触なし）"


# ============================================================
# 1. コピー保存則
#
# 【目的】Spray and Wait のコピー数制御が，シミュレーション全体を通して
#         一度も壊れていないことを確認する。
# 【なぜ正しさが言えるか】送信元は L 個のコピーを持って始まり，1回配るごとに
#         手元の残コピーが1ずつ減る。だから1つのバンドルを配れるのは最大 L-1 回，
#         配るたびの残コピーは L-1, L-2, ... と1ずつ下がり，1未満には絶対ならない。
#         この列が崩れていれば，コピーが増殖した／二重に配った等のバグを意味する。
# 【確認項目】各バンドル（bundle_id 単位）ごとに，
#   - 配った回数が L-1 を超えていないか
#   - 残コピーの列が [L-1, L-2, ...] と1ずつ減る連続列になっているか
#   - 残コピーが1未満（0以下）になっていないか
# ============================================================
def test_copy_conservation():
    by_bundle = _transfers_by_bundle()
    violations = []   # (bundle_id, 理由)

    for bid, events in by_bundle.items():
        copies_after = [c for _, _, _, c in events]
        # 配った回数は L-1 を超えない
        if len(events) > L - 1:
            violations.append((bid, f"配布回数{len(events)} > L-1={L-1}"))
        # 残コピーは L-1 から1ずつ減る連続列のはず
        expected_seq = list(range(L - 1, L - 1 - len(events), -1))
        if copies_after != expected_seq:
            violations.append((bid, f"残コピー列{copies_after} != {expected_seq}"))
        # 残コピーが1未満になっていない
        if any(c < 1 for c in copies_after):
            violations.append((bid, f"残コピーが1未満: {copies_after}"))

    expected = {"保存則に違反したバンドル数": 0}
    actual   = {"保存則に違反したバンドル数": len(violations)}
    passed = (actual == expected)
    report("1. コピー上限Lを守れているか",
           f"各バンドルは最大L-1={L-1}回しか配られず，送信元の残コピーはL-1から1ずつ減って最小1",
           {"L": L, "検査したバンドル数": len(by_bundle)},
           expected, actual, passed)
    assert not violations, f"コピー保存則違反: {violations[:5]}"


# ============================================================
# 2. Source Spray 検証
#
# 【目的】「Source（送信元集中型）Spray and Wait」になっているかを確認する。
#         数あるSpray方式のうち，本実装は "配る権利を送信元だけが持つ" 方式。
# 【なぜ正しさが言えるか】送信元だけが copies_left > 1 を持ち，コピーを
#         受け取った側は copies_left = 1（Waitフェーズ）になる。Waitのノードは
#         他人に配れない。よって1つのバンドルを「配った側(from_id)」として
#         ログに現れるノードは，正しく動いていれば送信元ただ1つに限られる。
#         2ノード以上が配っていたら，受信側が勝手に再配布した＝方式違反。
# 【確認項目】各バンドル（bundle_id 単位）で，
#   - 転送ログ上の from_id（配った側）が1種類だけか
#     （2種類以上あれば送信元以外も配ったことになり違反）
# ============================================================
def test_source_spray_only():
    by_bundle = _transfers_by_bundle()
    multi_sender = []   # 複数ノードが配ってしまったバンドル

    for bid, events in by_bundle.items():
        senders = {frm for _, frm, _, _ in events}
        if len(senders) != 1:
            multi_sender.append((bid, sorted(senders)))

    expected = {"複数ノードが配ったバンドル数": 0}
    actual   = {"複数ノードが配ったバンドル数": len(multi_sender)}
    passed = (actual == expected)
    report("2. 配るのは送信元だけか",
           "1つのバンドルを配るのは送信元1ノードだけ（受信側はWaitに入り転送しない）",
           {"検査したバンドル数": len(by_bundle)},
           expected, actual, passed)
    assert not multi_sender, f"送信元以外も転送している: {multi_sender[:5]}"


# ============================================================
# 3. 配送整合性
#
# 【目的】配送の集計値が物理的にありえる範囲に収まっているかを確認する。
#         統計値（配送率・平均遅延・平均ホップ）の信頼性を担保するための検査。
# 【なぜ正しさが言えるか】
#   - 配送数が生成数を超えるのは不可能（無いものは届かない）。超えたら二重計上。
#   - 遅延 = 配送時刻 - 生成時刻。生成より前に届くことはないので必ず非負。
#   - ホップ数は最低でも1（送信元→親機の1ホップ）。0以下なら計上ミス。
# 【確認項目】
#   - 配送数 <= 生成数
#   - 負の遅延が1件もないか
#   - ホップ数1未満が1件もないか
# ============================================================
def test_delivery_consistency():
    gen = SIM.total_bundles_generated
    dlv = SIM.total_delivered
    bad_delay = [d for d in SIM.delay_list if d < 0]
    bad_hops  = [h for h in SIM.hop_list if h < 1]

    expected = {"配送数<=生成数": True, "負の遅延の件数": 0, "ホップ数1未満の件数": 0}
    actual   = {"配送数<=生成数": dlv <= gen,
                "負の遅延の件数": len(bad_delay),
                "ホップ数1未満の件数": len(bad_hops)}
    passed = (actual == expected)
    report("3. 配送整合性",
           "配送数は生成数を超えず，配送遅延は非負，ホップ数は1以上",
           {"生成数": gen, "配送数": dlv},
           expected, actual, passed)
    assert dlv <= gen, f"配送数{dlv} > 生成数{gen}"
    assert not bad_delay, f"負の遅延が存在: {bad_delay[:5]}"
    assert not bad_hops,  f"ホップ数1未満が存在: {bad_hops[:5]}"


# ============================================================
# 4. コピー総量の上限
#
# 【目的】ネットワーク全体に出回ったコピーの総量が，理論上限を超えていないか
#         を確認する。テスト1がバンドル単位の局所チェックなのに対し，
#         こちらはシステム全体の総量という大局的なチェック。
# 【なぜ正しさが言えるか】1つのバンドルは最大 L 個のコピーしか生まない。
#         よって生成バンドル数 gen に対し，全コピー数の上限は gen * L。
#         各コピーは最終的に「親機に配送される」か「TTLで消える」かのどちらか。
#         その合計（配送 + TTL切れ）が gen * L を超えたら，コピーが
#         どこかで増殖したことになり矛盾する。
# 【確認項目】
#   - (配送数 + TTL切れ数) <= 生成バンドル数 * L
# ============================================================
def test_total_copies_within_bound():
    ban = SIM.total_bundles_generated
    max_copies = ban * L
    consumed = SIM.total_delivered + SIM.total_expired

    expected = {"消費コピー<=生成コピー総数": True}
    actual   = {"消費コピー<=生成コピー総数": consumed <= max_copies}
    passed = (actual == expected)
    report("4. コピー総量の上限",
           f"配送+TTL切れのコピー数は生成コピー総数(ban*L)を超えない",
           {"生成バンドル数(ban)": ban, "生成コピー総数(ban*L)": max_copies,
            "配送": SIM.total_delivered, "TTL切れ": SIM.total_expired},
           expected, actual, passed)
    assert consumed <= max_copies, f"消費コピー{consumed} > 上限{max_copies}"


# ============================================================
# 実行（python3 単体でも動かせるように）
# ============================================================
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Spray and Wait 結合テスト")
    print("=" * 60)

    test_simulation_produced_activity()
    test_copy_conservation()
    test_source_spray_only()
    test_delivery_consistency()
    test_total_copies_within_bound()

    print("\n" + "=" * 60)
    passed_count = sum(1 for _, p in results if p)
    print(f"結果: {passed_count}/{len(results)} 件 PASS")
    for name, p in results:
        print(f"  [{'PASS' if p else 'FAIL'}] {name}")
    print("=" * 60)
