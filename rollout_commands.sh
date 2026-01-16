#!/bin/bash
# MRL Memory System - 段階的ロールアウト用切替コマンド

# Phase 1: Read-onlyモード
phase1_readonly() {
    echo "Phase 1: Read-onlyモードに切り替え"
    export FWPKM_ENABLED=1
    export FWPKM_WRITE_MODE=readonly
    export FWPKM_WRITE_ENABLED=0
    export FWPKM_REVIEW_EFFECT=0
    echo "設定完了: Read-onlyモード"
}

# Phase 2: Write 10%
phase2_sampled() {
    echo "Phase 2: Write 10%モードに切り替え"
    export FWPKM_ENABLED=1
    export FWPKM_WRITE_MODE=sampled
    export FWPKM_WRITE_SAMPLE_RATE=0.1
    export FWPKM_WRITE_ENABLED=1
    export FWPKM_REVIEW_EFFECT=0
    echo "設定完了: Write 10%モード"
}

# Phase 3: Write 100%
phase3_full() {
    echo "Phase 3: Write 100%モードに切り替え"
    export FWPKM_ENABLED=1
    export FWPKM_WRITE_MODE=full
    export FWPKM_WRITE_ENABLED=1
    export FWPKM_REVIEW_EFFECT=0
    echo "設定完了: Write 100%モード"
}

# Phase 4: Review effect ON
phase4_review() {
    echo "Phase 4: Review effect ONに切り替え"
    export FWPKM_ENABLED=1
    export FWPKM_WRITE_MODE=full
    export FWPKM_WRITE_ENABLED=1
    export FWPKM_REVIEW_EFFECT=1
    echo "設定完了: Review effect ON"
}

# Kill Switch: 即座に停止
kill_switch() {
    echo "Kill Switch: 即座に停止"
    export FWPKM_WRITE_ENABLED=0
    echo "設定完了: 書き込み無効化"
}

# 使用方法
usage() {
    echo "使用方法: $0 [phase1|phase2|phase3|phase4|kill]"
    echo ""
    echo "  phase1: Read-onlyモード"
    echo "  phase2: Write 10%モード"
    echo "  phase3: Write 100%モード"
    echo "  phase4: Review effect ON"
    echo "  kill:   即座に停止"
}

# メイン処理
case "$1" in
    phase1)
        phase1_readonly
        ;;
    phase2)
        phase2_sampled
        ;;
    phase3)
        phase3_full
        ;;
    phase4)
        phase4_review
        ;;
    kill)
        kill_switch
        ;;
    *)
        usage
        exit 1
        ;;
esac
