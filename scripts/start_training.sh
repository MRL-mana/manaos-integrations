#!/bin/bash
echo "============================================================"
echo "CASTLE-EX 学習開始"
echo "============================================================"
echo ""

# Axolotlを使用する場合
if command -v axolotl &> /dev/null; then
    echo "Axolotlで学習を開始します..."
    axolotl train castle_ex/castle_ex_training_config.yaml
    exit 0
fi

# LLaMA-Factoryを使用する場合
if command -v llama-factory &> /dev/null; then
    echo "LLaMA-Factoryで学習を開始します..."
    TRAIN_DATA="castle_ex_dataset_v1_0_train.jsonl"
    if [ -f "data/castle_ex_dataset_v1_0_train.jsonl" ]; then
        TRAIN_DATA="data/castle_ex_dataset_v1_0_train.jsonl"
    fi
    llama-factory train \
        --model_name_or_path <ベースモデル> \
        --dataset "${TRAIN_DATA}" \
        --output_dir ./outputs/castle_ex_v1_0 \
        --num_train_epochs 25
    exit 0
fi

echo "[エラー] 外部トレーナーが見つかりません。"
echo "AxolotlまたはLLaMA-Factoryをインストールしてください。"
exit 1
