# test_saw.py を dtn_sim/直下に置く

import config
from models.node import Node
from routing.spray_and_wait import SprayAndWait

config.SAW_L = 6

node_a = Node("A", x=0, y=0, config=config)
node_b = Node("B", x=5, y=0, config=config)

# バンドルを手動で生成
node_a.generate_data(0)
node_a.generate_data(0)
node_a.generate_data(0)
node_a.bundle_data(0)

print(f"転送前: A={len(node_a.bundle_buffer)}個, copies={node_a.bundle_buffer[0].copies_left}")
print(f"転送前: B={len(node_b.bundle_buffer)}個")

routing = SprayAndWait(config)
routing.node_to_node(node_a, node_b, current_time=0)

print(f"転送後: A={len(node_a.bundle_buffer)}個, copies={node_a.bundle_buffer[0].copies_left}")
print(f"転送後: B={len(node_b.bundle_buffer)}個, copies={node_b.bundle_buffer[0].copies_left}")