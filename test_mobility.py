import config
from models.node import Node

config.NUM_NODES = 1
node = Node("TEST", x=300, y=300, config=config)
node.set_new_destination()

print(f"初期位置: ({node.x:.1f}, {node.y:.1f})")
print(f"目的地: ({node.dest_x:.1f}, {node.dest_y:.1f})")

for t in range(10):
    node.move(config.TIME_STEP)
    print(f"t={t+1}s: ({node.x:.1f}, {node.y:.1f}) 停止中={node.is_pausing}")