PYTHON = python
MAIN   = main.py

# --- 実験パラメータ（上書き可能） ---
N       = 200
T       = 28800
L       = 6
SEED    = 0
MOBILITY = random_waypoint
GEO      = open_field
ROUTING  = spray_and_wait

# ============================================================
# 基本実行
# ============================================================

run:
	$(PYTHON) $(MAIN) -N $(N) -T $(T) -L $(L) --seed $(SEED) \
		--mobility $(MOBILITY) --geo $(GEO) --routing $(ROUTING)

# 小規模テスト（動作確認用）
test:
	$(PYTHON) $(MAIN) -N 20 -T 3600 -L 6 --seed 42 \
		--mobility random_waypoint --geo open_field --routing spray_and_wait

# ============================================================
# モビリティテスト
# ============================================================

test-mobility:
	$(PYTHON) tests/test_mobility.py

test-saw:
	$(PYTHON) tests/test_saw.py

# ============================================================
# パラメータスイープ例
# ============================================================

# ノード数を変えて実行: make sweep-N
sweep-N:
	for n in 50 100 200; do \
		$(PYTHON) $(MAIN) -N $$n -T $(T) -L $(L) --seed $(SEED) \
			--mobility $(MOBILITY) --geo $(GEO) --routing $(ROUTING); \
	done

# コピー数を変えて実行: make sweep-L
sweep-L:
	for l in 2 4 6 8; do \
		$(PYTHON) $(MAIN) -N $(N) -T $(T) -L $$l --seed $(SEED) \
			--mobility $(MOBILITY) --geo $(GEO) --routing $(ROUTING); \
	done

# ============================================================
# クリーンアップ
# ============================================================

clean:
	find . -name '__pycache__' -type d | xargs rm -rf
	find . -name '*.pyc' -delete

.PHONY: run test test-mobility sweep-N sweep-L clean
