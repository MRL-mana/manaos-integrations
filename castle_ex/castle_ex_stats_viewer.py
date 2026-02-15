#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CASTLE-EXフレームワーク: データ分布レポート可視化ツール

stats.jsonを読み込んで、偏りや問題点を可視化
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError, TypeError):
        pass


class CastleEXStatsViewer:
    """CASTLE-EXデータ分布レポート可視化器"""
    
    def __init__(self, stats_file: str):
        """初期化"""
        self.stats_file = Path(stats_file)
        self.stats = None
        self.load_stats()
    
    def load_stats(self):
        """stats.jsonを読み込み"""
        if not self.stats_file.exists():
            raise FileNotFoundError(f"statsファイルが存在しません: {self.stats_file}")
        
        with open(self.stats_file, 'r', encoding='utf-8') as f:
            self.stats = json.load(f)
    
    def check_biases(self) -> Dict[str, Any]:
        """偏りチェック"""
        issues = []
        warnings = []
        
        # 1. logic-only偏りチェック
        axes_combinations = self.stats.get("axes_combinations", {})
        logic_only_count = axes_combinations.get("logic", 0)
        total = self.stats.get("total", 1)
        logic_only_ratio = logic_only_count / total
        
        if logic_only_ratio > 0.5:
            issues.append({
                "type": "logic_only_bias",
                "severity": "high",
                "message": f"logic-onlyデータが{logic_only_ratio:.1%}と高すぎます（推奨: 50%以下）",
                "current": logic_only_count,
                "total": total
            })
        elif logic_only_ratio > 0.4:
            warnings.append({
                "type": "logic_only_bias",
                "message": f"logic-onlyデータが{logic_only_ratio:.1%}とやや高めです",
                "current": logic_only_count,
                "total": total
            })
        
        # 2. error_type分布の偏りチェック
        error_dist = self.stats.get("error_type_distribution", {})
        if error_dist:
            error_types = list(error_dist.keys())
            error_counts = list(error_dist.values())
            if error_counts:
                max_count = max(error_counts)
                min_count = min(error_counts)
                if max_count > 0:
                    imbalance_ratio = min_count / max_count
                    if imbalance_ratio < 0.5:
                        issues.append({
                            "type": "error_type_imbalance",
                            "severity": "medium",
                            "message": f"error_typeの分布が偏っています（最小/最大 = {imbalance_ratio:.2f}）",
                            "distribution": error_dist
                        })
        
        # 3. layer×error_typeクロス集計の偏りチェック
        layer_error_cross = self.stats.get("layer_error_type_cross", {})
        if layer_error_cross:
            # 特定のlayerにerror_typeが集中していないか
            layer_error_counts = {}
            for key, count in layer_error_cross.items():
                # "layer_X_error_Y" から layer を抽出
                layer = key.split("_")[1]
                if layer not in layer_error_counts:
                    layer_error_counts[layer] = 0
                layer_error_counts[layer] += count
            
            if layer_error_counts:
                max_layer_errors = max(layer_error_counts.values())
                for layer, count in layer_error_counts.items():
                    if count > max_layer_errors * 0.8:
                        warnings.append({
                            "type": "layer_error_concentration",
                            "message": f"Layer {layer}にerror_typeが集中しています（{count}件）"
                        })
        
        # 4. axes×平均トークン長の偏りチェック
        axes_token = self.stats.get("axes_avg_token_length", {})
        if axes_token:
            for axes_key, token_data in axes_token.items():
                assistant_avg = token_data.get("assistant_avg", 0)
                # 短すぎる or 長すぎる
                if assistant_avg < 5 and "logic" in axes_key:
                    warnings.append({
                        "type": "short_response",
                        "message": f"{axes_key}の回答が短すぎます（平均{assistant_avg:.1f}文字）"
                    })
                elif assistant_avg > 200:
                    warnings.append({
                        "type": "long_response",
                        "message": f"{axes_key}の回答が長すぎます（平均{assistant_avg:.1f}文字）"
                    })
        
        # 5. 重複メッセージチェック
        duplicate_count = self.stats.get("duplicate_count", 0)
        if duplicate_count > total * 0.1:
            issues.append({
                "type": "high_duplication",
                "severity": "high",
                "message": f"重複メッセージが{duplicate_count}件（{duplicate_count/total:.1%}）と高すぎます",
                "current": duplicate_count,
                "total": total
            })
        elif duplicate_count > 0:
            warnings.append({
                "type": "duplication",
                "message": f"重複メッセージが{duplicate_count}件あります"
            })
        
        # 6. axis_evidenceカバレッジチェック
        evidence_coverage = self.stats.get("axis_evidence_coverage", {})
        if evidence_coverage:
            with_evidence = evidence_coverage.get("with_evidence", 0)
            without_evidence = evidence_coverage.get("without_evidence", 0)
            total_evidence = with_evidence + without_evidence
            if total_evidence > 0:
                coverage_ratio = with_evidence / total_evidence
                # Layer 3+ではaxis_evidenceが推奨
                if coverage_ratio < 0.3:
                    warnings.append({
                        "type": "low_axis_evidence",
                        "message": f"axis_evidenceカバレッジが{coverage_ratio:.1%}と低いです（Layer 3+で推奨）"
                    })
        
        return {
            "issues": issues,
            "warnings": warnings
        }
    
    def recommend_next_steps(self) -> Dict[str, Any]:
        """次に増やすべきLayer/axesの推奨"""
        recommendations = []
        
        by_layer = self.stats.get("by_layer", {})
        axes_combinations = self.stats.get("axes_combinations", {})
        
        # Layer別の推奨
        layer_ratios = {}
        total = self.stats.get("total", 1)
        for layer_str, layer_data in by_layer.items():
            layer = int(layer_str)
            count = layer_data.get("total", 0)
            ratio = count / total
            layer_ratios[layer] = ratio
        
        # 理想的な比率
        ideal_ratios = {
            0: 0.15, 1: 0.15, 2: 0.15,
            3: 0.10, 4: 0.10,
            5: 0.20, 6: 0.15
        }
        
        for layer, ideal_ratio in ideal_ratios.items():
            current_ratio = layer_ratios.get(layer, 0)
            if current_ratio < ideal_ratio * 0.8:
                recommendations.append({
                    "type": "layer_underrepresented",
                    "layer": layer,
                    "current_ratio": current_ratio,
                    "ideal_ratio": ideal_ratio,
                    "message": f"Layer {layer}が不足しています（現在{current_ratio:.1%}、理想{ideal_ratio:.1%}）"
                })
        
        # axes組み合わせの推奨
        logic_only = axes_combinations.get("logic", 0)
        integrated = axes_combinations.get("context,emotion,logic", 0)
        total = self.stats.get("total", 1)
        
        if logic_only / total > 0.5:
            recommendations.append({
                "type": "axes_combination",
                "message": "3軸統合（context,emotion,logic）のデータを増やすことを推奨",
                "current_logic_only": logic_only / total,
                "current_integrated": integrated / total
            })
        
        return {
            "recommendations": recommendations
        }
    
    def recommend_hard_negative_placement(self) -> Dict[str, Any]:
        """hard negativeをどこに入れるかの推奨"""
        recommendations = []
        
        by_layer = self.stats.get("by_layer", {})
        error_dist = self.stats.get("error_type_distribution", {})
        
        # Layer 5-6にhard negativeを推奨
        for layer_str in ["5", "6"]:
            layer_data = by_layer.get(layer_str, {})
            negative_count = layer_data.get("negative", 0)
            total_count = layer_data.get("total", 0)
            
            if total_count > 0:
                negative_ratio = negative_count / total_count
                if negative_ratio < 0.15:
                    recommendations.append({
                        "layer": int(layer_str),
                        "message": f"Layer {layer_str}にhard negativeを追加することを推奨（現在の負例率: {negative_ratio:.1%}）",
                        "current_negative": negative_count,
                        "total": total_count
                    })
        
        return {
            "hard_negative_recommendations": recommendations
        }
    
    def print_report(self):
        """レポート表示"""
        print("=" * 60)
        print("CASTLE-EX データ分布レポート分析")
        print("=" * 60)
        print(f"ファイル: {self.stats_file}")
        print(f"総データ数: {self.stats.get('total', 0)}")
        
        # 偏りチェック
        bias_check = self.check_biases()
        
        print("\n" + "=" * 60)
        print("【偏りチェック結果】")
        print("=" * 60)
        
        if bias_check["issues"]:
            print("\n[問題点]")
            for issue in bias_check["issues"]:
                severity = issue.get("severity", "unknown")
                print(f"  [{severity.upper()}] {issue['message']}")
        
        if bias_check["warnings"]:
            print("\n[警告]")
            for warning in bias_check["warnings"]:
                print(f"  - {warning['message']}")
        
        if not bias_check["issues"] and not bias_check["warnings"]:
            print("\n[OK] 特に問題は見つかりませんでした")
        
        # 次に増やすべきLayer/axes
        next_steps = self.recommend_next_steps()
        if next_steps["recommendations"]:
            print("\n" + "=" * 60)
            print("【次に増やすべきLayer/axes】")
            print("=" * 60)
            for rec in next_steps["recommendations"]:
                print(f"  - {rec['message']}")
        
        # hard negative推奨
        hard_neg_rec = self.recommend_hard_negative_placement()
        if hard_neg_rec["hard_negative_recommendations"]:
            print("\n" + "=" * 60)
            print("【hard negative配置推奨】")
            print("=" * 60)
            for rec in hard_neg_rec["hard_negative_recommendations"]:
                print(f"  - {rec['message']}")
        
        # 統計サマリー
        print("\n" + "=" * 60)
        print("【統計サマリー】")
        print("=" * 60)
        
        by_layer = self.stats.get("by_layer", {})
        print("\n層別内訳:")
        for layer_str in sorted(by_layer.keys(), key=int):
            layer_data = by_layer[layer_str]
            total = layer_data.get("total", 0)
            positive = layer_data.get("positive", 0)
            negative = layer_data.get("negative", 0)
            print(f"  Layer {layer_str}: {total}件（正例: {positive}, 負例: {negative}）")
        
        axes_combinations = self.stats.get("axes_combinations", {})
        print("\naxes組み合わせ（上位5位）:")
        sorted_axes = sorted(axes_combinations.items(), key=lambda x: x[1], reverse=True)[:5]
        for axes_key, count in sorted_axes:
            ratio = count / self.stats.get("total", 1)
            print(f"  {axes_key}: {count}件 ({ratio:.1%})")
        
        error_dist = self.stats.get("error_type_distribution", {})
        if error_dist:
            print("\nerror_type分布:")
            for error_type, count in sorted(error_dist.items(), key=lambda x: x[1], reverse=True):
                print(f"  {error_type}: {count}件")


def main():
    """メイン処理"""
    import argparse
    
    parser = argparse.ArgumentParser(description='CASTLE-EXデータ分布レポート可視化ツール')
    parser.add_argument('stats_file', type=str, help='stats.jsonファイルパス')
    
    args = parser.parse_args()
    
    viewer = CastleEXStatsViewer(args.stats_file)
    viewer.print_report()


if __name__ == "__main__":
    main()
