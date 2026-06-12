import random
from models.node import Node
from models.gateway import Gateway
from mobility.random_waypoint import RandomWaypoint
from geography.open_field import OpenField
from routing.spray_and_wait import SprayAndWait
from events.event_queue import EventQueue, Event


class Simulator:
    """
    DTNシミュレーター本体
    mobility / geography / routing は外部から注入できる
    省略した場合はデフォルト実装を使う

    Example
    -------
    sim = Simulator(config)                          # デフォルト
    sim = Simulator(config, routing=Prophet(config)) # ルーティングだけ差し替え
    """

    def __init__(self, config, mobility=None, geography=None, routing=None):
        self.config    = config
        self.time      = config.SIM_START
        self.nodes     = []
        self.gateways  = []
        self.mobility  = mobility  or RandomWaypoint(config)
        self.geography = geography or OpenField(config)
        self.routing   = routing   or SprayAndWait(config)
        self.eq        = EventQueue()

        # 統計
        self.total_bundles_generated = 0
        self.total_delivered         = 0
        self.total_expired           = 0
        self.delay_list              = []
        self.hop_list                = []

        self._setup_gateways()
        self._setup_nodes()
        self._schedule_initial_events()

    # ==================
    # 初期化
    # ==================

    def _setup_gateways(self):
        for i, (x, y) in enumerate(self.config.GATEWAY_POSITIONS):
            gw = Gateway(gateway_id=f"GW{i}", x=x, y=y, config=self.config)
            self.gateways.append(gw)
        print(f"[INIT] gateways: {len(self.gateways)}")

    def _setup_nodes(self):
        if self.config.NODE_SPAWN_MODE == "all_at_once":
            for i in range(self.config.NUM_NODES):
                self.nodes.append(self._create_node(i))
            print(f"[INIT] nodes: {len(self.nodes)}")
        elif self.config.NODE_SPAWN_MODE == "time_based":
            node_id = 0
            for spawn_time, count in self.config.NODE_SPAWN_SCHEDULE.items():
                self.eq.push(Event(
                    time       = spawn_time,
                    event_type = "NODE_SPAWN",
                    data       = {"count": count, "start_id": node_id}
                ))
                node_id += count
            print(f"[INIT] nodes will spawn on schedule")

    def _create_node(self, node_id):
        x, y = self.geography.get_spawn_position()
        node = Node(node_id=f"N{node_id}", x=x, y=y, config=self.config)
        self.mobility.init_node(node)
        return node

    def _schedule_initial_events(self):
        for t in range(self.config.SIM_START, self.config.SIM_END, self.config.MSG_GENERATION_INTERVAL):
            self.eq.push(Event(time=t, event_type=Event.MSG_GENERATE))

        for t in range(self.config.SIM_START, self.config.SIM_END, self.config.BUNDLE_INTERVAL):
            self.eq.push(Event(time=t, event_type="BUNDLE_GENERATE"))

        for t in range(self.config.SIM_START, self.config.SIM_END, self.config.TIME_STEP):
            self.eq.push(Event(time=t, event_type=Event.NODE_MOVE, data={"action": "move"}))

        for t in range(self.config.SIM_START, self.config.SIM_END, 60):
            self.eq.push(Event(time=t, event_type=Event.TTL_CHECK))

    # ==================
    # シミュレーション実行
    # ==================

    def run(self):
        print(f"\n[START] simulation")
        print(f"  area     : {self.config.AREA_WIDTH}m x {self.config.AREA_HEIGHT}m")
        print(f"  duration : {self.config.SIM_END}s ({self.config.SIM_END//3600}h)")
        print(f"  nodes    : {self.config.NUM_NODES}")
        print(f"  mobility : {self.mobility.__class__.__name__}")
        print(f"  routing  : {self.routing.__class__.__name__}")
        print("-" * 40)

        last_progress = -1

        while not self.eq.is_empty():
            event = self.eq.pop()
            self.time = event.time

            if self.time > self.config.SIM_END:
                break

            progress = int(self.time / self.config.SIM_END * 10) * 10
            if progress != last_progress:
                print(f"  {progress}% (t={self.time}s)")
                last_progress = progress

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

    # ==================
    # イベントハンドラ
    # ==================

    def _handle_data_generate(self):
        for node in self.nodes:
            node.generate_data(self.time)

    def _handle_bundle_generate(self):
        for node in self.nodes:
            before = node.bundles_generated
            node.bundle_data(self.time)
            self.total_bundles_generated += node.bundles_generated - before

    def _handle_node_move(self):
        for node in self.nodes:
            self.mobility.move(node, self.config.TIME_STEP)

    def _handle_contacts(self):
        for i, node_a in enumerate(self.nodes):
            for node_b in self.nodes[i+1:]:
                if node_a.distance_to(node_b) <= self.config.RANGE_NODE_TO_NODE:
                    if (node_a.can_contact(node_b.id, self.time) and
                            node_b.can_contact(node_a.id, self.time)):
                        self.routing.node_to_node(node_a, node_b, self.time)
                        self.routing.node_to_node(node_b, node_a, self.time)
                        node_a.record_contact(node_b.id, self.time)
                        node_b.record_contact(node_a.id, self.time)

        for node in self.nodes:
            for gw in self.gateways:
                if gw.in_range(node):
                    delivered = self.routing.node_to_gateway(node, gw, self.time)
                    for bundle in delivered:
                        self.total_delivered += 1
                        self.delay_list.append(self.time - bundle.created_at)
                        self.hop_list.append(bundle.hops)

    def _handle_node_spawn(self, data):
        for i in range(data["count"]):
            self.nodes.append(self._create_node(data["start_id"] + i))
        print(f"  [SPAWN] t={self.time}s: +{data['count']} nodes (total={len(self.nodes)})")

    def _handle_ttl_check(self):
        for node in self.nodes:
            self.total_expired += node.remove_expired_bundles(self.time)

    # ==================
    # 結果出力
    # ==================

    def _print_results(self):
        gen  = self.total_bundles_generated
        dlv  = self.total_delivered
        rate = dlv / gen * 100 if gen > 0 else 0
        avg_delay = sum(self.delay_list) / len(self.delay_list) if self.delay_list else 0
        avg_hops  = sum(self.hop_list)   / len(self.hop_list)   if self.hop_list  else 0

        print("\n" + "=" * 40)
        print("  Results")
        print("=" * 40)
        print(f"  bundles generated : {gen}")
        print(f"  delivered         : {dlv}")
        print(f"  expired           : {self.total_expired}")
        print(f"  delivery rate     : {rate:.1f}%")
        print(f"  avg delay         : {avg_delay:.1f} s")
        print(f"  avg hops          : {avg_hops:.2f}")
        print("=" * 40)
