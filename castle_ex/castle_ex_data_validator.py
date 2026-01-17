#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CASTLE-EXフレームワーク: データ検証ツール

生成データの品質チェック機能
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from collections import Counter

if sys.platform == 'win32':
    try:
        import io
        if not hasattr(sys.stdout, 'buffer') or sys.stdout.buffer.closed:
            pass
        else:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except (AttributeError, ValueError):
        pass


class CastleEXDataValidator:
    """CASTLE-EXデータ検証器"""
    
    # 回答長の基準（文字数）
    LAYER_LENGTH_LIMITS = {
        0: (1, 5),      # 公理層: 1-5文字
        1: (1, 20),     # 操作層: 1-20文字
        2: (5, 40),     # 関係層: 5-40文字
        3: (10, 40),    # 感情基礎層: 10-40文字
        4: (20, 60),    # 文脈基礎層: 20-60文字
        5: (40, 100),   # 因果層: 40-100文字
        6: (80, 200),   # 統合層: 80-200文字
    }
    
    def __init__(self):
        """初期化"""
        self.errors = []
        self.warnings = []
        self.stats = {
            "total": 0,
            "valid": 0,
            "invalid": 0,
            "by_layer": {},
            "error_types": Counter(),
        }
        self.message_hashes = {}  # 重複検知用
    
    def validate_format(self, item: Dict) -> Tuple[bool, Optional[str]]:
        """基本的なフォーマット検証"""
        if "messages" not in item:
            return False, "messagesキーが存在しません"
        
        messages = item["messages"]
        if not isinstance(messages, list) or len(messages) < 2:
            return False, "messagesは少なくとも2つの要素が必要です"
        
        if messages[0].get("role") != "user":
            return False, "最初のメッセージのroleは'user'である必要があります"
        
        if messages[-1].get("role") != "assistant":
            return False, "最後のメッセージのroleは'assistant'である必要があります"
        
        if "content" not in messages[0] or "content" not in messages[-1]:
            return False, "userとassistantのメッセージにcontentが必要です"
        
        return True, None
    
    def validate_answer_length(self, item: Dict, layer: Optional[int] = None) -> Tuple[bool, Optional[str]]:
        """回答長の検証"""
        if layer is None:
            layer = item.get("layer")
        
        if layer is None:
            # 層情報がない場合は推定を試みる
            assistant_content = item["messages"][-1]["content"]
            length = len(assistant_content)
            
            # 長さから層を推定
            for l, (min_len, max_len) in self.LAYER_LENGTH_LIMITS.items():
                if min_len <= length <= max_len:
                    return True, None
            
            return False, f"回答長({length}文字)がどの層の基準にも合致しません"
        
        if layer not in self.LAYER_LENGTH_LIMITS:
            return True, None  # 層が不明な場合は警告のみ
        
        assistant_content = item["messages"][-1]["content"]
        length = len(assistant_content)
        min_len, max_len = self.LAYER_LENGTH_LIMITS[layer]
        
        if length < min_len:
            return False, f"Layer {layer}: 回答が短すぎます ({length}文字 < {min_len}文字)"
        
        if length > max_len:
            return False, f"Layer {layer}: 回答が長すぎます ({length}文字 > {max_len}文字)"
        
        return True, None
    
    def validate_content_quality(self, item: Dict) -> Tuple[bool, List[str]]:
        """内容品質の検証"""
        warnings = []
        
        user_content = item["messages"][0]["content"]
        assistant_content = item["messages"][-1]["content"]
        
        # 曖昧な回答チェック（Layer 0-2では禁止）
        ambiguous_phrases = ["場合による", "文脈次第", "場合により", "時と場合により"]
        layer = item.get("layer")
        
        if layer is not None and layer <= 2:
            for phrase in ambiguous_phrases:
                if phrase in assistant_content:
                    warnings.append(f"Layer {layer}で曖昧な表現「{phrase}」が使用されています")
        
        # 空の回答チェック
        if not assistant_content.strip():
            return False, ["回答が空です"]
        
        # 回答が短すぎる場合（公理層以外）
        if layer is not None and layer > 0 and len(assistant_content.strip()) < 2:
            warnings.append("回答が非常に短いです")
        
        # ユーザーメッセージが空
        if not user_content.strip():
            return False, ["ユーザーメッセージが空です"]
        
        return True, warnings
    
    def validate_3axis_integration(self, item: Dict) -> Tuple[bool, List[str]]:
        """3軸統合の検証（Layer 5-6）"""
        warnings = []
        layer = item.get("layer")
        
        if layer is None or layer < 5:
            return True, []  # Layer 5-6以外はチェックしない
        
        user_content = item["messages"][0]["content"]
        assistant_content = item["messages"][-1]["content"]
        
        # Layer 5-6では感情・文脈要素が含まれるべき
        emotion_keywords = ["感情", "悲しい", "怒り", "嬉しい", "不安", "自信"]
        context_keywords = ["文脈", "状況", "会議", "関係", "真意", "意味"]
        
        has_emotion = any(keyword in user_content or keyword in assistant_content 
                         for keyword in emotion_keywords)
        has_context = any(keyword in user_content or keyword in assistant_content 
                         for keyword in context_keywords)
        
        if layer >= 5 and not has_emotion and not has_context:
            warnings.append(f"Layer {layer}では感情または文脈要素が推奨されます")
        
        return True, warnings
    
    def validate_axis_evidence(self, item: Dict) -> Tuple[bool, List[str]]:
        """axis_evidenceの必須チェック（Layer3+で60%以上必須）"""
        warnings = []
        layer = item.get("layer")
        axes = item.get("axes", [])
        axis_evidence = item.get("axis_evidence", {})
        
        # Layer 3+ではaxis_evidenceが推奨（統計で60%以上必要）
        if layer is not None and layer >= 3:
            if not axis_evidence:
                warnings.append(f"Layer {layer}ではaxis_evidenceが推奨されます（Layer 3+で60%以上必要）")
            else:
                # axesに含まれる軸に対してevidenceがあるかチェック
                for axis in axes:
                    if axis not in axis_evidence:
                        warnings.append(f"axesに'{axis}'が含まれていますが、axis_evidenceに'{axis}'の証拠がありません")
        
        # axis_evidenceがあるのにaxesに含まれていない軸がある場合
        if axis_evidence:
            for axis in axis_evidence.keys():
                if axis not in axes:
                    warnings.append(f"axis_evidenceに'{axis}'の証拠がありますが、axesに'{axis}'が含まれていません")
        
        return True, warnings
    
    def validate_axis_evidence_coverage(self, all_items: List[Dict]) -> Tuple[bool, str]:
        """axis_evidenceカバレッジの検証（Layer 3+で60%以上必須）"""
        layer3_plus_items = [item for item in all_items if item.get("layer", 0) >= 3]
        if not layer3_plus_items:
            return True, ""
        
        with_evidence = sum(1 for item in layer3_plus_items if item.get("axis_evidence"))
        coverage_ratio = with_evidence / len(layer3_plus_items)
        
        if coverage_ratio < 0.6:
            return False, f"Layer 3+のaxis_evidenceカバレッジが{coverage_ratio:.1%}と低すぎます（60%以上必要）"
        
        return True, ""
    
    def validate_item(self, item: Dict, index: int) -> bool:
        """単一データ項目の検証"""
        self.stats["total"] += 1
        
        # フォーマット検証
        is_valid, error = self.validate_format(item)
        if not is_valid:
            self.errors.append(f"行{index+1}: {error}")
            self.stats["error_types"][error] += 1
            self.stats["invalid"] += 1
            return False
        
        # 内容品質検証
        is_valid, warnings = self.validate_content_quality(item)
        if not is_valid:
            for warning in warnings:
                self.errors.append(f"行{index+1}: {warning}")
                self.stats["error_types"][warning] += 1
            self.stats["invalid"] += 1
            return False
        
        # 回答長検証
        is_valid, error = self.validate_answer_length(item)
        if not is_valid:
            self.warnings.append(f"行{index+1}: {error}")
        
        # 3軸統合検証
        is_valid, warnings = self.validate_3axis_integration(item)
        for warning in warnings:
            self.warnings.append(f"行{index+1}: {warning}")
        
        # axis_evidence検証
        is_valid, warnings = self.validate_axis_evidence(item)
        for warning in warnings:
            self.warnings.append(f"行{index+1}: {warning}")
        
        # 重複検知（messagesのハッシュ）
        import hashlib
        messages = item.get("messages", [])
        if messages:
            messages_str = json.dumps(messages, sort_keys=True, ensure_ascii=False)
            msg_hash = hashlib.md5(messages_str.encode('utf-8')).hexdigest()
            if msg_hash in self.message_hashes:
                self.warnings.append(f"行{index+1}: 重複メッセージを検出（行{self.message_hashes[msg_hash]}と同一）")
            else:
                self.message_hashes[msg_hash] = index + 1
        
        # 層統計
        layer = item.get("layer")
        if layer is not None:
            if layer not in self.stats["by_layer"]:
                self.stats["by_layer"][layer] = {"total": 0, "valid": 0, "invalid": 0}
            self.stats["by_layer"][layer]["total"] += 1
        
        self.stats["valid"] += 1
        if layer is not None:
            self.stats["by_layer"][layer]["valid"] += 1
        
        return True
    
    def validate_file(self, file_path: str) -> Dict[str, Any]:
        """JSONLファイル全体の検証"""
        print("=" * 60)
        print("CASTLE-EX データ検証")
        print("=" * 60)
        print(f"検証ファイル: {file_path}")
        
        path = Path(file_path)
        if not path.exists():
            print(f"✗ ファイルが存在しません: {file_path}")
            return {"valid": False, "error": "ファイルが存在しません"}
        
        # ファイル読み込み
        items = []
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        item = json.loads(line)
                        items.append(item)
                    except json.JSONDecodeError as e:
                        self.errors.append(f"行{line_num}: JSON解析エラー - {e}")
                        self.stats["error_types"]["JSON解析エラー"] += 1
        except Exception as e:
            print(f"✗ ファイル読み込みエラー: {e}")
            return {"valid": False, "error": str(e)}
        
        print(f"読み込み完了: {len(items)}件")
        print("\n検証中...")
        
        # 各項目を検証
        for i, item in enumerate(items):
            self.validate_item(item, i)
        
        # axis_evidenceカバレッジの検証（Layer 3+で60%以上必須）
        is_valid_coverage, coverage_error = self.validate_axis_evidence_coverage(items)
        if not is_valid_coverage:
            self.errors.append(coverage_error)
            self.stats["invalid"] += 1
        
        # 結果レポート
        self.print_report()
        
        return {
            "valid": len(self.errors) == 0,
            "stats": self.stats,
            "errors": self.errors,
            "warnings": self.warnings,
        }
    
    def print_report(self):
        """検証結果レポートの表示"""
        print("\n" + "=" * 60)
        print("検証結果")
        print("=" * 60)
        
        total = self.stats["total"]
        valid = self.stats["valid"]
        invalid = self.stats["invalid"]
        
        print(f"総データ数: {total}")
        print(f"有効: {valid} ({valid/total*100:.1f}%)")
        print(f"無効: {invalid} ({invalid/total*100:.1f}%)")
        print(f"警告: {len(self.warnings)}件")
        
        if self.stats["by_layer"]:
            print("\n層別統計:")
            for layer in sorted(self.stats["by_layer"].keys()):
                layer_stats = self.stats["by_layer"][layer]
                total_l = layer_stats["total"]
                valid_l = layer_stats["valid"]
                print(f"  Layer {layer}: {valid_l}/{total_l} 有効 ({valid_l/total_l*100:.1f}%)")
        
        if self.errors:
            print(f"\n✗ エラー ({len(self.errors)}件):")
            for error in self.errors[:10]:  # 最初の10件のみ表示
                print(f"  - {error}")
            if len(self.errors) > 10:
                print(f"  ... 他{len(self.errors)-10}件")
        
        if self.warnings:
            print(f"\n⚠ 警告 ({len(self.warnings)}件):")
            for warning in self.warnings[:10]:  # 最初の10件のみ表示
                print(f"  - {warning}")
            if len(self.warnings) > 10:
                print(f"  ... 他{len(self.warnings)-10}件")
        
        if self.stats["error_types"]:
            print("\nエラータイプ別集計:")
            for error_type, count in self.stats["error_types"].most_common(5):
                print(f"  - {error_type}: {count}件")


def main():
    """メイン処理"""
    import argparse
    
    parser = argparse.ArgumentParser(description='CASTLE-EXデータ検証ツール')
    parser.add_argument('file', type=str, help='検証するJSONLファイルパス')
    
    args = parser.parse_args()
    
    validator = CastleEXDataValidator()
    result = validator.validate_file(args.file)
    
    if result["valid"]:
        print("\n✓ すべてのデータが有効です")
        sys.exit(0)
    else:
        print("\n✗ 検証エラーが検出されました")
        sys.exit(1)


if __name__ == "__main__":
    main()
