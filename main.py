"""
DTN シミュレーター エントリポイント

Usage:
    python main.py -N 200 -T 28800 --routing spray_and_wait -L 6
    python main.py -N 50  -T 3600  --mobility random_waypoint --geo open_field
    python main.py --help
"""

import argparse
import random

import config
from simulator import Simulator

# 利用可能なモデルの登録
# 新しいモデルを追加するときはここに追加するだけでよい
from mobility.random_waypoint import RandomWaypoint
from geography.open_field import OpenField
from routing.spray_and_wait import SprayAndWait

MOBILITY_MODELS = {
    'random_waypoint': RandomWaypoint,
}

GEOGRAPHY_MODELS = {
    'open_field': OpenField,
}

ROUTING_PROTOCOLS = {
    'spray_and_wait': SprayAndWait,
}


def parse_args():
    parser = argparse.ArgumentParser(description='DTN Simulator')

    parser.add_argument('-N', '--nodes',    type=int,   default=200,
                        help='number of nodes (default: 200)')
    parser.add_argument('-T', '--time',     type=int,   default=28800,
                        help='simulation duration [s] (default: 28800 = 8h)')
    parser.add_argument('-L', '--saw-l',    type=int,   default=6,
                        help='Spray and Wait copy count (default: 6)')
    parser.add_argument('--seed',           type=int,   default=None,
                        help='random seed (default: none)')
    parser.add_argument('--mobility',       type=str,   default='random_waypoint',
                        choices=MOBILITY_MODELS.keys(),
                        help='mobility model (default: random_waypoint)')
    parser.add_argument('--geo',            type=str,   default='open_field',
                        choices=GEOGRAPHY_MODELS.keys(),
                        help='geography model (default: open_field)')
    parser.add_argument('--routing',        type=str,   default='spray_and_wait',
                        choices=ROUTING_PROTOCOLS.keys(),
                        help='routing protocol (default: spray_and_wait)')

    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    # 引数で config を上書き
    config.NUM_NODES = args.nodes
    config.SIM_END   = args.time
    config.SAW_L     = args.saw_l

    # モデルを選択して注入
    mobility  = MOBILITY_MODELS[args.mobility](config)
    geography = GEOGRAPHY_MODELS[args.geo](config)
    routing   = ROUTING_PROTOCOLS[args.routing](config)

    sim = Simulator(config, mobility=mobility, geography=geography, routing=routing)
    sim.run()
