# dtn_sim

DTN (Delay Tolerant Network) シミュレーター

## ディレクトリ構成

```
dtn_sim/
├── main.py           # エントリポイント
├── config.py         # 固定パラメータ
├── simulator.py      # シミュレーター本体
├── Makefile          # 実験実行用
├── mobility/         # 移動モデル
│   ├── base.py
│   └── random_waypoint.py
├── geography/        # 地理モデル
│   ├── base.py
│   └── open_field.py
├── routing/          # ルーティングプロトコル
│   ├── base.py
│   └── spray_and_wait.py
├── models/           # データ構造
│   ├── node.py
│   ├── gateway.py
│   └── message.py
├── events/           # イベントキュー
│   └── event_queue.py
├── tests/            # テスト
│   └── test_mobility.py
└── del/              # 不要ファイル置き場
```

## 実行方法

### 基本実行

```bash
python main.py -N 200 -T 28800 --routing spray_and_wait -L 6 --seed 0
```

### Makefile を使った実行

```bash
make run              # デフォルトパラメータで実行
make test             # 小規模テスト（N=20, T=1h）
make sweep-N          # ノード数スイープ（50 / 100 / 200）
make sweep-L          # コピー数スイープ（2 / 4 / 6 / 8）
make test-mobility    # モビリティテスト（スナップショット出力）
make clean            # __pycache__ を削除
```

### パラメータを上書きして実行

```bash
make run N=100 T=7200 L=4
```

## コマンド引数

実験ごとに変えるパラメータ。

| 引数 | 省略形 | デフォルト | 説明 |
|------|--------|-----------|------|
| `--nodes` | `-N` | 200 | ノード数 |
| `--time` | `-T` | 28800 | シミュレーション時間 [s] |
| `--saw-l` | `-L` | 6 | Spray and Wait コピー数上限 |
| `--seed` | | None | 乱数シード |
| `--mobility` | | random_waypoint | 移動モデル |
| `--geo` | | open_field | 地理モデル |
| `--routing` | | spray_and_wait | ルーティングプロトコル |

## config.py の固定パラメータ

物理的・環境的に固定なパラメータ。変更する場合は `config.py` を直接編集する。

| パラメータ | デフォルト | 説明 |
|-----------|-----------|------|
| `AREA_WIDTH / HEIGHT` | 600 m | エリアサイズ |
| `TIME_STEP` | 1 s | シミュレーションの時間刻み |
| `MOVE_SPEED` | 1.1 m/s | 移動速度 |
| `PAUSE_TIME_MIN` | 300 s | 目的地での最小停止時間 |
| `PAUSE_TIME_MAX` | 2400 s | 目的地での最大停止時間 |
| `RANGE_NODE_TO_NODE` | 10 m | 子機間通信範囲 |
| `RANGE_NODE_TO_GATEWAY` | 100 m | 子機–親機通信範囲 |
| `CONTACT_COOLDOWN` | 60 s | 同一ノード間の再接触クールダウン |
| `GATEWAY_POSITIONS` | PATTERN_B | 親機の位置（2台） |
| `SPAWN_POINTS` | 2箇所 | ノード生成座標 |
| `SPAWN_RADIUS` | 30 m | 生成座標のばらつき半径 |
| `MSG_GENERATION_INTERVAL` | 10 s | データ生成間隔 |
| `BUNDLE_INTERVAL` | 30 s | バンドル生成間隔 |
| `BUNDLE_SIZE` | 3 件 | 1バンドルあたりのメッセージ数 |
| `MSG_TTL` | 1500 s | メッセージの生存時間 |

## モデルの追加方法

### ルーティングプロトコルを追加する例

1. `routing/prophet.py` を作成し `RoutingProtocol` を継承して実装
2. `main.py` の `ROUTING_PROTOCOLS` に登録

```python
ROUTING_PROTOCOLS = {
    'spray_and_wait': SprayAndWait,
    'prophet':        Prophet,       # 追加
}
```

3. コマンドで指定できるようになる

```bash
python main.py --routing prophet
```

移動モデル・地理モデルも同様の手順で追加できる。
