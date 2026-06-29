"""
親機接触回数のノード別分布テスト（ランダム移動でばらつくか）

【このテストの目的】
  「親機によく出会うノードを見分けて，そこにコピーを集中させる」という
  ルーティング改善案が成立するかどうかは，次の一点にかかっている：

      ── ランダム移動で，親機への接触回数にノード間の差が生まれるか ──

  もし全ノードが完全ランダムに動いて接触回数がほぼ均一なら，
  「よく出会うノード」を選ぶ意味がない（みんな同じなら選びようがない）。
  逆に接触回数の分布が大きく広がるなら（一部のノードが親機近くをよく通る／
  長く滞在する），その一部を見分けてコピーを集中できる＝改善案が効く。

  これは机上では断定できず，シミュレーションで分布を見るしかない。
  本テストは Random Waypoint 下での「親機接触回数のノード別分布」を出し，
  どれだけ広がるか（ばらつくか）を定量化する。

【接触回数の定義】
  ノードが親機の通信範囲に「入った瞬間」を1回と数える（接触セッション）。
  範囲内に留まり続ける間は1回のまま，一度出てまた入れば2回目。
  ＝「そのノードが親機のそばに何回来たか」。バンドルを運んでいるかは無関係で，
    純粋に移動の性質として親機への出会いやすさを測る。

【見方】
  - 接触回数ごとのノード数ヒストグラム（横棒）で分布の形を見る
  - 平均・中央値・標準偏差・変動係数(CV)で「広がり」を数値化する
    （CV = 標準偏差/平均。大きいほどノード間の差が大きい＝改善案に有望）

【実行】
  python3 tests/test_gateway_contact_distribution.py
  python3 -m pytest tests/test_gateway_contact_distribution.py -s
"""

import os
import io
import sys
import random
import statistics
import contextlib
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import config
from simulator import Simulator
from routing.spray_and_wait import SprayAndWait
from mobility.random_waypoint import RandomWaypoint
from geography.open_field import OpenField


# ============================================================
# 検証パラメータ
# ============================================================
NUM_NODES   = 50
SIM_END     = 14400     # 4h（接触回数を安定させるため長めに）
SAW_L       = 6
SEED        = 42
GATEWAY_POS = (300, 300)   # 親機は中心に1台


class _CountingSimulator(Simulator):
    """親機への接触セッション数をノード別に数える Simulator。
    ルーティングは通常どおり動かしつつ，各移動ステップで
    『範囲外→範囲内』に変わった瞬間を1接触として記録する。"""

    def __init__(self, *args, **kwargs):
        self.gw_contacts = defaultdict(int)        # node_id -> 接触セッション数
        self._was_in_range = defaultdict(bool)     # (node_id, gw_id) -> 直前の在圏状態
        super().__init__(*args, **kwargs)

    def _handle_contacts(self):
        # --- 親機接触セッションのカウント（在圏の立ち上がりを数える）---
        for node in self.nodes:
            for gw in self.gateways:
                key = (node.id, gw.id)
                in_range = gw.in_range(node)
                if in_range and not self._was_in_range[key]:
                    self.gw_contacts[node.id] += 1   # 範囲に入った瞬間＝1接触
                self._was_in_range[key] = in_range
        # --- 通常のルーティング処理（転送・配送）はそのまま実行 ---
        super()._handle_contacts()


def _run():
    config.NUM_NODES       = NUM_NODES
    config.SIM_END         = SIM_END
    config.SAW_L           = SAW_L
    config.NODE_SPAWN_AREA = "random"
    config.GATEWAY_POSITIONS = [GATEWAY_POS]
    random.seed(SEED)

    routing   = SprayAndWait(config)
    mobility  = RandomWaypoint(config)
    geography = OpenField(config)

    with contextlib.redirect_stdout(io.StringIO()):
        sim = _CountingSimulator(config, mobility=mobility, geography=geography, routing=routing)
        sim.run()

    # 全ノード分の接触回数（一度も接触しなかったノードは0として埋める）
    counts = [sim.gw_contacts.get(n.id, 0) for n in sim.nodes]
    return counts


def _histogram(counts, n_bins=12):
    """接触回数 -> ノード数 のヒストグラム（横棒）を文字列で返す"""
    hi = max(counts)
    lo = min(counts)
    if hi == lo:
        return [f"  全ノードが {hi} 回（差なし）"]

    width = max(1, -(-(hi - lo + 1) // n_bins))   # ceil
    bins = defaultdict(int)
    for c in counts:
        b = (c - lo) // width
        bins[b] += 1

    n_bins_actual = (hi - lo) // width + 1
    max_nodes = max(bins.values())
    bar_scale = 40 / max_nodes

    lines = []
    for b in range(n_bins_actual):
        b_lo = lo + b * width
        b_hi = b_lo + width - 1
        n = bins.get(b, 0)
        bar = "#" * int(round(n * bar_scale))
        rng = f"{b_lo:>3}-{b_hi:<3}" if width > 1 else f"{b_lo:>5}  "
        lines.append(f"  接触{rng}回 | {bar} {n}")
    return lines


def _report(counts):
    n = len(counts)
    total = sum(counts)
    mean = statistics.mean(counts)
    median = statistics.median(counts)
    std = statistics.pstdev(counts)
    cv = std / mean if mean else 0
    zero = sum(1 for c in counts if c == 0)
    q = statistics.quantiles(counts, n=4) if n >= 4 else [median, median, median]

    print("\n" + "=" * 60)
    print("  親機接触回数のノード別分布（ランダム移動でばらつくか）")
    print("=" * 60)
    print(f"  設定: N={NUM_NODES}  T={SIM_END}s  親機=中心{GATEWAY_POS}  seed={SEED}")
    print("-" * 60)

    print("\n[分布ヒストグラム]  横軸=ノード数 / 縦の各行=接触回数の帯")
    for line in _histogram(counts):
        print(line)

    print("\n[ばらつきの要約]")
    print(f"    ノード数            : {n}")
    print(f"    総接触回数          : {total}")
    print(f"    平均                : {mean:.1f} 回")
    print(f"    中央値              : {median:.1f} 回")
    print(f"    第1四分位 / 第3四分位 : {q[0]:.1f} / {q[2]:.1f} 回")
    print(f"    最小 / 最大         : {min(counts)} / {max(counts)} 回")
    print(f"    標準偏差            : {std:.1f}")
    print(f"    変動係数(CV=σ/平均) : {cv:.2f}   ← 大きいほどノード間の差が大きい")
    print(f"    一度も接触なしのノード: {zero} / {n}")
    print("=" * 60)
    return {"mean": mean, "median": median, "std": std, "cv": cv, "max": max(counts)}


# ============================================================
# pytest 用：分布が取得でき，計算が破綻していないことの担保
#   （CVの大小そのものは合否にしない。分布を見るのが目的）
# ============================================================
def test_gateway_contact_distribution():
    counts = _run()
    _report(counts)
    assert len(counts) == NUM_NODES
    assert sum(counts) > 0, "誰も親機に接触していない（設定を見直す）"
    assert all(c >= 0 for c in counts)


if __name__ == "__main__":
    _report(_run())


# ============================================================
# 【結果から言えること】（N=50, T=4h, 親機=中心(300,300), seed=42 の実測）
# ------------------------------------------------------------
#  分布は中央値3回の山に固まり，ほぼ均一だった。
#    平均3.3 / 中央値3.0 / 最大6 / 標準偏差1.2 / 変動係数CV=0.38
#
#  期待された「最大20・中央値2」のような大きな広がりは出ていない。
#  むしろ純粋なランダム(ポアソン)より均一：平均3.3なら理論CVは
#  1/√3.3≈0.55 のはずだが，実測CV=0.38はそれより小さい
#  ＝ノード同士が偶然以上に似ている。
#
#  理由：Random Waypoint は記憶のない移動モデルで，どのノードも
#  「親機の近くに住む」ような持続的な偏りを持たない。よって時間が経つほど
#  全ノードの接触率は同じ値に収束し，見えている差は一時的なノイズにすぎない。
#  ＝「親機によく出会うノード」は安定した個性ではなく，たまたまの運。
#
# 【結論（暫定）】
#   純粋な RWP を使う限り「よく出会うノードを選んでコピーを集中させる」案は
#   効きにくい。選ぶ根拠（接触頻度）が持続せず，長く回すほど差が消えるため。
#   案が成立する条件は，移動モデルにノードごとの持続的な空間的偏りが
#   あること。次の検証として「前半によく接触したノードが後半もよく接触するか
#   （接触頻度の時間的安定性／相関）」を測れば，案の生死を直接判定できる。
# ============================================================
