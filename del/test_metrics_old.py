# test_metrics.py を dtn_sim/直下に置く

import config
config.SIM_END    = 360   # 6分（TTLと同じ）
config.NUM_NODES  = 5
config.SAW_L      = 3

from simulator import Simulator
sim = Simulator(config)
sim.run()

# 手動で確認
print(f"\n手動確認:")
print(f"配送率の分母（生成バンドル数）: {sim.total_bundles_generated}")
print(f"配送率の分子（到達数）: {sim.total_delivered}")
print(f"TTL切れ: {sim.total_expired}")
print(f"未配送: {sim.total_bundles_generated - sim.total_delivered - sim.total_expired}")