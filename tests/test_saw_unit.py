"""
Spray and Wait ユニットテスト（発表用ログ出力版）

シミュレーションを丸ごと回すのではなく，2〜3ノードだけの最小構成を作り，
「パラメータ → 期待値 → 実際の結果」を1件ずつ確認する。
各テストはパラメータを変えて，何を確認しているかが分かりやすいようにしている。
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import config
from models.node import Node
from models.gateway import Gateway
from models.message import Bundle
from routing.spray_and_wait import SprayAndWait

results = []  # (test_name, passed)


def make_node(node_id, x=0, y=0):
    return Node(node_id=node_id, x=x, y=y, config=config)


def make_bundle(source_id, copies_left, created_at=0, ttl=1500):
    b = Bundle(created_at=created_at, source_id=source_id, messages=[], ttl=ttl)
    b.copies_left = copies_left
    return b


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


# ============================================================
# 1. 単一接触テスト
#    L=6 のソースが1回配ると，自分は5に減り，受け取った側は1になる
# ============================================================
def test_single_contact_spray():
    L = 6
    routing = SprayAndWait(config)
    a = make_node("A")
    b = make_node("B")
    bundle = make_bundle(source_id="A", copies_left=L)
    a.bundle_buffer.append(bundle)

    routing.node_to_node(a, b, current_time=0)

    expected = {"送信元の残コピー": L - 1, "受信側の残コピー": 1}
    actual   = {"送信元の残コピー": bundle.copies_left,
                "受信側の残コピー": b.bundle_buffer[0].copies_left if b.bundle_buffer else None}
    passed = (actual == expected)
    report("1. 単一接触テスト",
           "L個のコピーを持つ送信元が1回配ると，送信元はL-1に減り，受信側は1になる",
           {"L": L}, expected, actual, passed)


# ============================================================
# 2. 受信側は転送しないテスト
#    copies_left=1 のノードは誰にも配れない
# ============================================================
def test_receiver_does_not_forward():
    routing = SprayAndWait(config)
    b = make_node("B")
    c = make_node("C")
    bundle = make_bundle(source_id="A", copies_left=1)
    b.bundle_buffer.append(bundle)

    routing.node_to_node(b, c, current_time=0)

    expected = {"Cが受け取った件数": 0}
    actual   = {"Cが受け取った件数": len(c.bundle_buffer)}
    passed = (actual == expected)
    report("2. 受信側は転送しないテスト",
           "残コピー=1（Waitフェーズ）のノードは接触相手に何も渡さない",
           {"残コピー": 1}, expected, actual, passed)


# ============================================================
# 3. 重複防止テスト
#    すでに同じbundle_idを持つノードには渡らない
# ============================================================
def test_duplicate_prevention():
    routing = SprayAndWait(config)
    a = make_node("A")
    c = make_node("C")
    bundle = make_bundle(source_id="A", copies_left=6)
    a.bundle_buffer.append(bundle)

    existing = make_bundle(source_id="A", copies_left=1)
    existing.id = bundle.id   # Cはすでに同じバンドルを持っている
    c.bundle_buffer.append(existing)

    routing.node_to_node(a, c, current_time=0)

    expected = {"送信元の残コピー": 6, "Cのバッファ件数": 1}
    actual   = {"送信元の残コピー": bundle.copies_left, "Cのバッファ件数": len(c.bundle_buffer)}
    passed = (actual == expected)
    report("3. 重複防止テスト",
           "受信側がすでに同じbundle_idを持っている場合は転送しない（増えない・減らない）",
           {"既存bundle_id": "一致させた状態"}, expected, actual, passed)


# ============================================================
# 4. コピー上限テスト
#    L=3 のとき，2回配るとcopies_left=1になり，3回目は転送が発生しない
# ============================================================
def test_copy_limit_exhausted():
    L = 3
    routing = SprayAndWait(config)
    src = make_node("SRC")
    bundle = make_bundle(source_id="SRC", copies_left=L)
    src.bundle_buffer.append(bundle)
    n1, n2, n3 = make_node("N1"), make_node("N2"), make_node("N3")

    # 1回目: src(残コピー=3) → n1
    fwd1 = routing.node_to_node(src, n1, current_time=0)
    step1 = {"送信元の残コピー(転送後)": bundle.copies_left,
             "転送された件数": len(fwd1), "n1が受け取った件数": len(n1.bundle_buffer)}

    # 2回目: src(残コピー=2) → n2
    fwd2 = routing.node_to_node(src, n2, current_time=1)
    step2 = {"送信元の残コピー(転送後)": bundle.copies_left,
             "転送された件数": len(fwd2), "n2が受け取った件数": len(n2.bundle_buffer)}

    # 3回目: src(残コピー=1) → n3  もう配れないはず
    fwd3 = routing.node_to_node(src, n3, current_time=2)
    step3 = {"送信元の残コピー(転送後)": bundle.copies_left,
             "転送された件数": len(fwd3), "n3が受け取った件数": len(n3.bundle_buffer)}

    expected = {
        "1回目の接触": {"送信元の残コピー(転送後)": 2, "転送された件数": 1, "n1が受け取った件数": 1},
        "2回目の接触": {"送信元の残コピー(転送後)": 1, "転送された件数": 1, "n2が受け取った件数": 1},
        "3回目の接触": {"送信元の残コピー(転送後)": 1, "転送された件数": 0, "n3が受け取った件数": 0},
    }
    actual = {"1回目の接触": step1, "2回目の接触": step2, "3回目の接触": step3}
    passed = (actual == expected)
    report("4. コピー上限テスト",
           f"L={L}のバンドルはL-1=2回しか配れない。1,2回目は配れて3回目は配れないことを比較する",
           {"L": L, "接触回数": 3}, expected, actual, passed)


# ============================================================
# 5. ゲートウェイ配送テスト
#    ノードのバンドルがゲートウェイに渡るとdelivered=Trueになる
# ============================================================
def test_gateway_delivery():
    routing = SprayAndWait(config)
    node = make_node("N")
    gw   = Gateway(gateway_id="GW0", x=0, y=0, config=config)
    created_at, current_time = 100, 150
    bundle = make_bundle(source_id="N", copies_left=1, created_at=created_at) #copies_leftを２にしてもPASSした
    node.bundle_buffer.append(bundle)

    delivered = routing.node_to_gateway(node, gw, current_time=current_time)

    expected = {"配送完了フラグ": True, "ゲートウェイに届いたか": True,
                "ノードのバッファ件数": 0, "遅延(秒)": current_time - created_at}
    actual   = {"配送完了フラグ": bundle.delivered,
                "ゲートウェイに届いたか": bundle in gw.received_messages,
                "ノードのバッファ件数": len(node.bundle_buffer),
                "遅延(秒)": routing.delivery_log[0][5] if routing.delivery_log else None}
    passed = (actual == expected)
    report("5. ゲートウェイ配送テスト",
           "ノードがゲートウェイにバンドルを渡すと配送完了フラグが立ち，バッファから消える",
           {"生成時刻": created_at, "配送時刻": current_time}, expected, actual, passed)


# ============================================================
# 6. TTL切れテスト
#    created_at=0, ttl=100 のバンドルはt=101で期限切れになる
# ============================================================
def test_ttl_expiry():
    ttl, current_time = 100, 101
    node = make_node("N")
    bundle = make_bundle(source_id="N", copies_left=3, created_at=0, ttl=ttl)
    node.bundle_buffer.append(bundle)

    removed = node.remove_expired_bundles(current_time=current_time)

    expected = {"削除された件数": 1, "削除後のバッファ件数": 0}
    actual   = {"削除された件数": removed, "削除後のバッファ件数": len(node.bundle_buffer)}
    passed = (actual == expected)
    report("6. TTL切れテスト",
           f"生成時刻=0, TTL={ttl} のバンドルは現在時刻={current_time}で期限切れになる",
           {"TTL": ttl, "現在時刻": current_time}, expected, actual, passed)


def test_ttl_boundary():
    ttl, current_time = 100, 100
    node = make_node("N")
    bundle = make_bundle(source_id="N", copies_left=3, created_at=0, ttl=ttl)
    node.bundle_buffer.append(bundle)

    removed = node.remove_expired_bundles(current_time=current_time)

    expected = {"削除された件数": 0, "削除後のバッファ件数": 1}
    actual   = {"削除された件数": removed, "削除後のバッファ件数": len(node.bundle_buffer)}
    passed = (actual == expected)
    report("6c. TTL境界テスト",
           f"生成時刻=0, TTL={ttl} のバンドルは現在時刻={current_time}（ちょうどTTL）ではまだ期限切れにならない",
           {"TTL": ttl, "現在時刻": current_time}, expected, actual, passed)


def test_ttl_not_yet_expired():
    ttl, current_time = 100, 99
    node = make_node("N")
    bundle = make_bundle(source_id="N", copies_left=3, created_at=0, ttl=ttl)
    node.bundle_buffer.append(bundle)

    removed = node.remove_expired_bundles(current_time=current_time)

    expected = {"削除された件数": 0, "削除後のバッファ件数": 1}
    actual   = {"削除された件数": removed, "削除後のバッファ件数": len(node.bundle_buffer)}
    passed = (actual == expected)
    report("6b. TTL未切れテスト",
           f"生成時刻=0, TTL={ttl} のバンドルは現在時刻={current_time}ではまだ期限切れにならない",
           {"TTL": ttl, "現在時刻": current_time}, expected, actual, passed)


# ============================================================
# 7. 通信範囲境界テスト
#    distance == RANGE_NODE_TO_NODE は範囲内（<=），+1すると範囲外
# ============================================================
def test_range_boundary():
    r = config.RANGE_NODE_TO_NODE
    a = make_node("A", x=0, y=0)
    b_in  = make_node("B_in",  x=r,     y=0)
    b_out = make_node("B_out", x=r + 1, y=0)

    dist_in  = a.distance_to(b_in)
    dist_out = a.distance_to(b_out)

    expected = {"境界ちょうど(10m)は通信可能": True, "境界+1m(11m)は通信不可": False}
    actual   = {"境界ちょうど(10m)は通信可能": dist_in <= r, "境界+1m(11m)は通信不可": dist_out <= r}
    passed = (actual == expected)
    report("7. 通信範囲境界テスト",
           f"ノード間通信範囲={r}m の境界ちょうどは範囲内，+1mは範囲外",
           {"通信範囲(m)": r, "境界での距離": dist_in, "境界+1mでの距離": dist_out},
           expected, actual, passed)


# ============================================================
# 7b. 親機通信範囲境界テスト
#     distance == RANGE_NODE_TO_GATEWAY は範囲内（<=），+1すると範囲外
# ============================================================
def test_gateway_range_boundary():
    r  = config.RANGE_NODE_TO_GATEWAY
    gw = Gateway(gateway_id="GW0", x=0, y=0, config=config)
    node_in  = make_node("N_in",  x=r,     y=0)
    node_out = make_node("N_out", x=r + 1, y=0)

    expected = {"境界ちょうど(100m)は通信可能": True, "境界+1m(101m)は通信不可": False}
    actual   = {"境界ちょうど(100m)は通信可能": gw.in_range(node_in),
                "境界+1m(101m)は通信不可": gw.in_range(node_out)}
    passed = (actual == expected)
    report("7b. 親機通信範囲境界テスト",
           f"親機通信範囲={r}m の境界ちょうどは範囲内，+1mは範囲外",
           {"通信範囲(m)": r}, expected, actual, passed)


# ============================================================
# 8. クールダウンテスト
#    t=10 で初回接触，10秒ごとに再接触を試み，t=61 で解除を確認
# ============================================================
def test_contact_cooldown():
    cooldown = config.CONTACT_COOLDOWN  # 60秒
    routing  = SprayAndWait(config)
    a   = make_node("A")
    b   = make_node("B")
    bundle = make_bundle(source_id="A", copies_left=6, created_at=0)
    a.bundle_buffer.append(bundle)

    # t=10: 初回接触 → 転送される
    fwd_10 = routing.node_to_node(a, b, current_time=10)
    a.record_contact(b.id, current_time=10)
    b.record_contact(a.id, current_time=10)

    # t=20,30,40,50,60: クールダウン中 → 転送されない
    contacts = {}
    for t in range(20, 61, 10):
        b.bundle_buffer.clear()  # 受信バッファをリセットして件数を見やすくする
        can = a.can_contact(b.id, current_time=t)
        fwd = routing.node_to_node(a, b, current_time=t) if can else []
        contacts[f"t={t}秒(CD中)"] = {"接触可能": can, "転送件数": len(fwd)}

    # t=61: クールダウン解除 → 転送される
    b.bundle_buffer.clear()
    can_61 = a.can_contact(b.id, current_time=71)
    fwd_71 = routing.node_to_node(a, b, current_time=71) if can_61 else []
    contacts["t=71秒(CD解除後)"] = {"接触可能": can_61, "転送件数": len(fwd_71)}

    expected = {
        "t=10秒(初回)転送件数": 1,
        "t=20秒(CD中)": {"接触可能": False, "転送件数": 0},
        "t=30秒(CD中)": {"接触可能": False, "転送件数": 0},
        "t=40秒(CD中)": {"接触可能": False, "転送件数": 0},
        "t=50秒(CD中)": {"接触可能": False, "転送件数": 0},
        "t=60秒(CD中)": {"接触可能": False, "転送件数": 0},
        "t=71秒(CD解除後)": {"接触可能": True, "転送件数": 1},
    }
    actual = {"t=10秒(初回)転送件数": len(fwd_10), **contacts}
    passed = (actual == expected)
    report("8. クールダウンテスト",
           f"t=10で初回接触，クールダウン={cooldown}秒中は転送不可，t=71(解除後)で転送再開",
           {"クールダウン(秒)": cooldown, "初回接触時刻": 10}, expected, actual, passed)


# ============================================================
# 実行
# ============================================================
print("=" * 60)
print("Spray and Wait ユニットテスト")
print("=" * 60)

test_single_contact_spray()
test_receiver_does_not_forward()
test_duplicate_prevention()
test_copy_limit_exhausted()
test_gateway_delivery()
test_ttl_expiry()
test_ttl_not_yet_expired()
test_range_boundary()
test_gateway_range_boundary()
test_contact_cooldown()

print("\n" + "=" * 60)
passed_count = sum(1 for _, p in results if p)
print(f"結果: {passed_count}/{len(results)} 件 PASS")
for name, p in results:
    print(f"  [{'PASS' if p else 'FAIL'}] {name}")
print("=" * 60)
