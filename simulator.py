import random
from models.node import Node
from models.gateway import Gateway
from routing.spray_and_wait import SprayAndWait
from events.event_queue import EventQueue, Event

class Simulator:
    """
    DTNシミュレーター本体
    イベント駆動型で動作する
    """

    def __init__(self, config):
        self.config   = config
        self.time     = config.SIM_START
        self.nodes    = []
        self.gateways = []
        self.routing  = SprayAndWait(config)
        self.eq       = EventQueue()

        # 統計
        self.total_bundles_generated = 0
        self.total_delivered         = 0
        self.total_expired           = 0
        self.delay_list              = []
        self.hop_list                = []

        # 初期化
        self._setup_gateways()
        self._setup_nodes()
        self._schedule_initial_events()

    # ==================
    # 初期化
    # ==================

    def _setup_gateways(self):
        """親機を配置する"""
        for i, (x, y) in enumerate(self.config.GATEWAY_POSITIONS):
            gw = Gateway(
                gateway_id = f"GW{i}",
                x = x, y = y,
                config = self.config
            )
            self.gateways.append(gw)
        print(f"[INIT] 親機 {len(self.gateways)} 台を配置")

    def _setup_nodes(self):
        """子機ノードを生成する"""
        if self.config.NODE_SPAWN_MODE == "all_at_once":
            for i in range(self.config.NUM_NODES):
                node = self._create_node(i)
                self.nodes.append(node)
            print(f"[INIT] 子機 {len(self.nodes)} 台を生成")

        elif self.config.NODE_SPAWN_MODE == "time_based":
            node_id = 0
            for spawn_time, count in self.config.NODE_SPAWN_SCHEDULE.items():
                self.eq.push(Event(
                    time       = spawn_time,
                    event_type = "NODE_SPAWN",
                    data       = {"count": count, "start_id": node_id}
                ))
                node_id += count
            print(f"[INIT] 子機は時間帯ごとに生成予定")

    def _create_node(self, node_id):
        """ノードを1台生成する"""
        if self.config.NODE_SPAWN_AREA == "spawn_points":
            base = random.choice(self.config.SPAWN_POINTS)
            x = base[0] + random.uniform(-self.config.SPAWN_RADIUS, self.config.SPAWN_RADIUS)
            y = base[1] + random.uniform(-self.config.SPAWN_RADIUS, self.config.SPAWN_RADIUS)
            x = max(0, min(self.config.AREA_WIDTH, x))
            y = max(0, min(self.config.AREA_HEIGHT, y))
        else:
            x = random.uniform(0, self.config.AREA_WIDTH)
            y = random.uniform(0, self.config.AREA_HEIGHT)

        node = Node(node_id=f"N{node_id}", x=x, y=y, config=self.config)
        node.set_new_destination()
        return node

    def _schedule_initial_events(self):
        """初期イベントをキューに登録"""

        # データ生成イベント（10秒ごと・全ノード）
        t = self.config.SIM_START
        while t < self.config.SIM_END:
            self.eq.push(Event(time=t, event_type=Event.MSG_GENERATE))
            t += self.config.MSG_GENERATION_INTERVAL

        # バンドル生成イベント（30秒ごと・全ノード）
        t = self.config.SIM_START
        while t < self.config.SIM_END:
            self.eq.push(Event(time=t, event_type="BUNDLE_GENERATE"))
            t += self.config.BUNDLE_INTERVAL

        # ノード移動イベント（1ステップごと）
        t = self.config.SIM_START
        while t < self.config.SIM_END:
            self.eq.push(Event(
                time       = t,
                event_type = Event.NODE_MOVE,
                data       = {"action": "move"}
            ))
            t += self.config.TIME_STEP

        # TTLチェックイベント（1分ごと）
        t = self.config.SIM_START
        while t < self.config.SIM_END:
            self.eq.push(Event(time=t, event_type=Event.TTL_CHECK))
            t += 60

    # ==================
    # シミュレーション実行
    # ==================

    def run(self):
        """シミュレーションを実行する"""
        print(f"\n[START] シミュレーション開始")
        print(f"  エリア        : {self.config.AREA_WIDTH}m × {self.config.AREA_HEIGHT}m")
        print(f"  実行時間      : {self.config.SIM_END}s ({self.config.SIM_END//3600}時間)")
        print(f"  ノード数      : {self.config.NUM_NODES}")
        print(f"  親機数        : {len(self.gateways)}")
        print(f"  SAW L値       : {self.config.SAW_L}")
        print(f"  TTL           : {self.config.MSG_TTL}s")
        print(f"  バンドルサイズ : {self.config.BUNDLE_SIZE}件")
        print("-" * 40)

        last_progress = -1

        while not self.eq.is_empty():
            event = self.eq.pop()
            self.time = event.time

            if self.time > self.config.SIM_END:
                break

            # 進捗表示（10%ごと）
            progress = int(self.time / self.config.SIM_END * 10) * 10
            if progress != last_progress:
                print(f"  進捗: {progress}% (t={self.time}s)")
                last_progress = progress

            # イベント処理
            if event.event_type == Event.MSG_GENERATE:
                self._handle_data_generate()

            elif event.event_type == "BUNDLE_GENERATE":
                self._handle_bundle_generate()

            elif event.event_type == Event.NODE_MOVE:
                if event.data and event.data.get("action") == "move":
                    self._handle_node_move()
                    self._handle_contacts()

            elif event.event_type == "NODE_SPAWN":
                self._handle_node_spawn(event.data)

            elif event.event_type == Event.TTL_CHECK:
                self._handle_ttl_check()

        self._print_results()
        # if self.config.OUTPUT_CSV:
        #     self._save_csv()

    # ==================
    # イベントハンドラ
    # ==================

    def _handle_data_generate(self):
        """全ノードが10秒ごとにデータを1件生成"""
        for node in self.nodes:
            node.generate_data(self.time)

    def _handle_bundle_generate(self):
        """全ノードが30秒ごとにデータをバンドル化"""
        for node in self.nodes:
            before = node.bundles_generated
            node.bundle_data(self.time)
            self.total_bundles_generated += (node.bundles_generated - before)

    def _handle_node_move(self):
        """全ノードを1ステップ移動させる"""
        for node in self.nodes:
            node.move(self.config.TIME_STEP)

    def _handle_contacts(self):
        """接触判定と転送処理"""
        # 子機間の接触
        for i, node_a in enumerate(self.nodes):
            for node_b in self.nodes[i+1:]:
                dist = node_a.distance_to(node_b)
                if dist <= self.config.RANGE_NODE_TO_NODE:
                    if (node_a.can_contact(node_b.id, self.time) and
                        node_b.can_contact(node_a.id, self.time)):
                        self.routing.node_to_node(node_a, node_b, self.time)
                        self.routing.node_to_node(node_b, node_a, self.time)
                        node_a.record_contact(node_b.id, self.time)
                        node_b.record_contact(node_a.id, self.time)

        # 子機→親機の接触
        for node in self.nodes:
            for gw in self.gateways:
                if gw.in_range(node):
                    delivered = self.routing.node_to_gateway(node, gw, self.time)
                    for bundle in delivered:
                        self.total_delivered += 1
                        delay = self.time - bundle.created_at
                        self.delay_list.append(delay)
                        self.hop_list.append(bundle.hops)

    def _handle_node_spawn(self, data):
        """time_basedモードでのノード生成"""
        start_id = data["start_id"]
        for i in range(data["count"]):
            node = self._create_node(start_id + i)
            self.nodes.append(node)
        print(f"  [SPAWN] t={self.time}s: {data['count']}台追加 (合計{len(self.nodes)}台)")

    def _handle_ttl_check(self):
        """TTL切れバンドルを削除"""
        for node in self.nodes:
            expired = node.remove_expired_bundles(self.time)
            self.total_expired += expired

    # ==================
    # 結果出力
    # ==================

    def _print_results(self):
        delivery_rate = (
            self.total_delivered / self.total_bundles_generated * 100
            if self.total_bundles_generated > 0 else 0
        )
        avg_delay = (
            sum(self.delay_list) / len(self.delay_list)
            if self.delay_list else 0
        )
        avg_hops = (
            sum(self.hop_list) / len(self.hop_list)
            if self.hop_list else 0
        )

        print("\n" + "=" * 40)
        print("  シミュレーション結果")
        print("=" * 40)
        print(f"  生成バンドル数    : {self.total_bundles_generated}")
        print(f"  親機到達数        : {self.total_delivered}")
        print(f"  TTL切れ           : {self.total_expired}")
        print(f"  配送率            : {delivery_rate:.1f}%")
        print(f"  平均遅延          : {avg_delay:.1f} s")
        print(f"  平均ホップ数      : {avg_hops:.2f} 回")
        print("=" * 40)
