"""
Spray and Wait「弱点：Waitフェーズの受動性」影響度検証テスト
（親機の設置位置による比較つき）

【このテストは何を見るか】
  Spray and Wait では，コピーが L=1（Waitフェーズ）になったバンドルは
  あとは「自分が親機に直接出会うまで，ただ待つ」しかない。
  広域・低密度・親機固定の環境では親機に偶然出会える確率が低く，
  ばら撒いたコピーの多くが Wait のまま TTL切れで死ぬ。
  この弱点が実際どれだけ配送効率を削っているかを，数字で定量化する。

  さらに本テストでは「親機の設置位置」を変えて比較する。
  親機が中心(300,300)にある場合と，端の隅(600,600)にある場合とで，
  弱点がどれだけ深刻化するかを並べて見る。
  ＝ 親機に出会いにくい配置ほど Wait の受動性が効く，という仮説の検証。

【測定の原理】
  Bundle.hops の数え方（生成時0／中継で+1／親機配送で+1）を利用する。
    - 配送ログ hops == 1 … 生成ノード自身が親機に直接届けた（自力配送）
                           ＝ そもそも Spray でばら撒かなくても届いた分
    - 配送ログ hops >= 2 … ばら撒かれたコピー（Wait中のコピー）が中継して
                           親機に届いた ＝ Spray が配送に本当に貢献した分

  「ばら撒いたコピー総数」は転送ログの件数（1転送＝Wait中コピーが1つ誕生）。
  そのうち届いた数（hops>=2）との比が，ばら撒きコピーの生存率。
  生存率が低いほど「撒いた先が Wait のまま死んだ」＝弱点が強く効いている。

  ※ 親機位置以外の条件（ノード配置・移動）は seed を固定して全ケース共通に
    するので，差は純粋に「親機の位置」だけから生じる。

【実行】
  python3 tests/test_wait_weakness.py                  # 結果を表示
  python3 -m pytest tests/test_wait_weakness.py -s     # 合否判定つきで表示
"""

import os
import io
import sys
import random
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
NUM_NODES = 30
SIM_END   = 7200      # 2h
SAW_L     = 6
SEED      = 42

# 比較する親機の設置位置（ラベル, 座標）。エリアは 600x600。
GATEWAY_CASES = [
    ("中心(300,300)", (300, 300)),
    ("端の隅(600,600)", (600, 600)),
]


def _run_simulation(gateway_pos):
    """指定した親機位置でシミュレーションを1回回す。進捗ログは抑制する。
    seed は毎回同じに固定するので，親機位置以外は全ケース共通になる。"""
    config.NUM_NODES       = NUM_NODES
    config.SIM_END         = SIM_END
    config.SAW_L           = SAW_L
    config.NODE_SPAWN_AREA = "random"
    config.GATEWAY_POSITIONS = [gateway_pos]
    random.seed(SEED)

    routing   = SprayAndWait(config)
    mobility  = RandomWaypoint(config)
    geography = OpenField(config)

    # Simulator が出す大量の進捗ログ（[INIT] / 10% / Results …）は捨てる
    with contextlib.redirect_stdout(io.StringIO()):
        sim = Simulator(config, mobility=mobility, geography=geography, routing=routing)
        sim.run()
    return sim, routing


def _analyze(sim, routing):
    """ログから弱点の影響指標を計算してまとめる"""
    transfer_log = routing.transfer_log   # (time, from, to, bid, src_copies_after)
    delivery_log = routing.delivery_log   # (time, node, gw, bid, src, delay, hops)
    L = config.SAW_L

    gen         = sim.total_bundles_generated
    total_deliv = len(delivery_log)
    self_deliv  = sum(1 for d in delivery_log if d[6] == 1)   # 自力配送(1ホップ)
    relay_deliv = sum(1 for d in delivery_log if d[6] >= 2)   # 中継配送(2ホップ+)

    sprayed_copies = len(transfer_log)                        # ばら撒いたコピー数
    sprayed_landed = relay_deliv                              # うち親機に届いた数
    survival = sprayed_landed / sprayed_copies * 100 if sprayed_copies else 0

    # バンドル単位：フルにばら撒いた(L-1回)のに中継コピーが1つも届かなかった本数
    spray_count = defaultdict(int)
    for _, _, _, bid, _ in transfer_log:
        spray_count[bid] += 1
    relay_by_bid = defaultdict(int)
    for d in delivery_log:
        if d[6] >= 2:
            relay_by_bid[d[3]] += 1
    full_sprayed = [bid for bid, n in spray_count.items() if n == L - 1]
    full_wasted  = [bid for bid in full_sprayed if relay_by_bid[bid] == 0]

    return {
        "gen": gen,
        "total_deliv": total_deliv,
        "deliv_rate": total_deliv / gen * 100 if gen else 0,
        "self_deliv": self_deliv,
        "relay_deliv": relay_deliv,
        "self_pct": self_deliv / total_deliv * 100 if total_deliv else 0,
        "relay_pct": relay_deliv / total_deliv * 100 if total_deliv else 0,
        "sprayed_copies": sprayed_copies,
        "sprayed_landed": sprayed_landed,
        "sprayed_wasted": sprayed_copies - sprayed_landed,
        "survival": survival,
        "waste_rate": 100 - survival,
        "n_full": len(full_sprayed),
        "n_full_wasted": len(full_wasted),
        "L": L,
    }


# ---- 全角を考慮した桁そろえ用ヘルパ ----
def _w(s):
    """表示幅（全角=2, 半角=1）でカウント"""
    return sum(2 if ord(c) > 0x2E7F else 1 for c in s)

def _pad(s, width):
    return s + " " * max(0, width - _w(s))


def _print_comparison(rows):
    """rows = [(label, result_dict), ...] を表で並べて出力する"""
    labels = [label for label, _ in rows]
    rs     = [r for _, r in rows]
    label_col = 26
    val_col   = 18

    def line(name, values):
        s = _pad("  " + name, label_col)
        for v in values:
            s += _pad(v, val_col)
        print(s)

    print("\n" + "=" * (label_col + val_col * len(rows)))
    print("  弱点（Waitフェーズの受動性）影響度 — 親機の設置位置で比較")
    print("=" * (label_col + val_col * len(rows)))
    print(f"  設定: N={NUM_NODES}  T={SIM_END}s  L={SAW_L}  seed={SEED}（親機位置以外は共通）")
    print("-" * (label_col + val_col * len(rows)))

    line("親機の位置", labels)
    print("-" * (label_col + val_col * len(rows)))
    line("配送率(配送/生成)",      [f"{r['deliv_rate']:.1f}%" for r in rs])
    line("配送合計(コピー)",       [f"{r['total_deliv']}" for r in rs])
    print()
    line("自力配送(1hop)",         [f"{r['self_deliv']} ({r['self_pct']:.1f}%)" for r in rs])
    line("中継配送(2hop+)",        [f"{r['relay_deliv']} ({r['relay_pct']:.1f}%)" for r in rs])
    print()
    line("ばら撒きコピー数",       [f"{r['sprayed_copies']}" for r in rs])
    line("うち親機に届いた",       [f"{r['sprayed_landed']}" for r in rs])
    line("Waitのまま死んだ",       [f"{r['sprayed_wasted']}" for r in rs])
    line("ばら撒き生存率",         [f"{r['survival']:.1f}%" for r in rs])
    line("無駄死に率(弱点の影響)", [f"{r['waste_rate']:.1f}%" for r in rs])
    print()
    line(f"フル撒き(L-1={rs[0]['L']-1})本数",  [f"{r['n_full']}" for r in rs])
    line("うち中継0で未達",        [f"{r['n_full_wasted']}" for r in rs])
    print("=" * (label_col + val_col * len(rows)))


def _collect():
    """全ケースを回して (label, result) のリストを返す"""
    rows = []
    for label, pos in GATEWAY_CASES:
        sim, routing = _run_simulation(pos)
        rows.append((label, _analyze(sim, routing)))
    return rows


# ============================================================
# pytest 用：各ケースの指標が妥当な範囲に収まっているかを確認する
#   （数値の大小ではなく，計算が破綻していないことの担保）
# ============================================================
def test_wait_weakness():
    rows = _collect()
    _print_comparison(rows)
    for _, r in rows:
        assert r["sprayed_copies"] > 0, "ばら撒きが発生していない"
        assert r["total_deliv"] > 0,   "配送が発生していない"
        assert 0 <= r["survival"] <= 100
        assert r["sprayed_landed"] <= r["sprayed_copies"]


if __name__ == "__main__":
    _print_comparison(_collect())


# ============================================================
# 【結果から言えること】（N=30, T=2h, L=6, seed=42 の実測。親機位置のみ変更）
# ------------------------------------------------------------
#  親機を中心(300,300)から端の隅(600,600)に移すだけで，結果は激変した。
#  （隅では半径100mの通信範囲のうち約1/4しかエリアに入らず，親機に
#   出会えるノードが激減するため）
#
#  [配送率]      53.6%  →  5.0%    約1/10に崩壊
#  [配送合計]    3844件 →  355件
#  [無駄死に率]  75.9%  →  98.7%   ばら撒きがほぼ全て無駄に
#  [ばら撒き生存率] 24.1% → 1.3%
#
#  注目点：
#   - 自力配送の「割合」は両方とも約81%でほぼ不変。つまり「どう届くか」の
#     内訳構造は親機位置に依らず，変わったのは配送の「絶対量」。
#     → 中心でも端でも，届くものの8割は生成ノードの自力配送。中継は脇役。
#   - ばら撒いたコピー数は端の方が多い(3043→5213)。届かないバンドルが
#     消えずに長く生き残り，より多くの相手に撒かれるため。
#     それでも生存率1.3%。＝撒けば撒くほど無駄が増える悪循環。
#
# 【結論】
#   弱点（Wait受動性）は親機の配置に極めて敏感で，親機に出会いにくい配置
#   ほど深刻化する。端配置では撒いたコピーの98.7%がWaitのまま消滅し，
#   配送率は中心の約1/10まで落ちた。
#   「ばら撒くだけで，撒いた先（親機への届けやすさ）を選べない」という
#   S&W の限界が，親機位置の差として明確に数字に出ている。
#   本番想定（親機2台・端寄りに固定・広域）は端配置に近いため，
#   この弱点が実環境で効くことを裏付ける。
# ============================================================
