#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ExcelファイルのOCR結果をLLMで修正・補完
既存のExcelファイルを読み込んで、LLMで文字化けや誤認識を修正
"""

import sys
import os
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Optional, List
import json
import re
import unicodedata

# Windowsのエンコーディングは呼び出し側（.bat の chcp 65001 など）で統一する。
# ここで sys.stdout/sys.stderr を差し替えると、実行形態によっては
# "ValueError: I/O operation on closed file." の原因になるため行わない。

try:
    from local_llm_helper import generate, chat
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    print("警告: local_llm_helperが見つかりません")


class ExcelLLMOCRCorrector:
    """ExcelファイルのOCR結果をLLMで修正"""

    def __init__(
        self,
        llm_model: str = None,  # Noneの場合は環境変数またはデフォルトを使用
        batch_size: int = 100,  # 一度に処理するセル数
        max_cell_length: int = 500  # セルあたりの最大文字数
    ):
        """
        初期化

        Args:
            llm_model: 使用するLLMモデル（Noneの場合は環境変数またはデフォルトを使用）
            batch_size: バッチ処理サイズ
            max_cell_length: セルあたりの最大文字数
        """
        # モデル選択: 環境変数 > 引数 > デフォルト
        if llm_model is None:
            llm_model = os.getenv("MANA_OCR_LLM_MODEL", "qwen2.5:7b")

        # より大きなモデルが利用可能な場合は推奨
        # 環境変数 MANA_OCR_USE_LARGE_MODEL=1 で自動的に大きなモデルを選択
        if os.getenv("MANA_OCR_USE_LARGE_MODEL", "0").strip().lower() in ("1", "true", "yes", "y", "on"):
            # 大きなモデルの優先順位（LM Studio対応）
            large_models = [
                "qwen2.5-coder-32b-instruct",  # 32B（LM Studio用、最高精度）
                "qwen2.5-coder-14b-instruct",  # 14B（LM Studio用、高精度）
                "qwen3:30b",  # 30B（Ollama用、高精度）
                "qwen2.5:14b",  # 14B（Ollama用、中規模）
            ]

            # 利用可能なモデルを確認
            try:
                from local_llm_helper import list_models
                available_models = list_models()
                for model in large_models:
                    if model in available_models:
                        llm_model = model
                        print(f"大きなモデルを選択: {model}")
                        break
            except Exception:
                # LM Studioのモデル名を直接試す
                if os.getenv("USE_LM_STUDIO", "0").strip().lower() in ("1", "true", "yes", "y", "on"):
                    # LM Studio APIから直接モデル一覧を取得
                    try:
                        from tools.lm_studio_model_selector import ModelSelectionConfig, select_models
                        cfg = ModelSelectionConfig(
                            preferred_models=[
                                # まずは安定して起動しやすい順（精度重視なら32Bを事前ロード推奨）
                                "qwen2.5-coder-7b-instruct",
                                "qwen/qwen2.5-coder-14b-instruct",
                                "openai/gpt-oss-20b",
                                "qwen2.5-coder-32b-instruct",
                                "qwen2.5-coder-14b-instruct",
                            ],
                            skip_substrings=["ggml-org/qwen2.5-coder-14b-instruct"],
                            max_models=1,
                        )
                        picked = select_models(cfg)
                        if picked:
                            llm_model = picked[0]
                            print(f"LM Studioモデルを選択（キャッシュ/テスト済み）: {llm_model}")
                    except Exception:
                        # API取得に失敗した場合はデフォルトモデルを使用
                        pass

        self.llm_model = llm_model
        self.batch_size = batch_size
        self.max_cell_length = max_cell_length
        self.stats = {
            'total_cells': 0,
            'corrected_cells': 0,
            'skipped_cells': 0
        }

    _CIRCLED_MAP = str.maketrans({
        "①":"1","②":"2","③":"3","④":"4","⑤":"5","⑥":"6","⑦":"7","⑧":"8","⑨":"9","⑩":"10",
        "⑪":"11","⑫":"12","⑬":"13","⑭":"14","⑮":"15","⑯":"16","⑰":"17","⑱":"18","⑲":"19","⑳":"20",
        "㉑":"21","㉒":"22","㉓":"23","㉔":"24","㉕":"25",
    })

    def _normalize_text(self, text: str) -> str:
        """丸数字・全角などを正規化（数字は壊さない）"""
        if text is None:
            return ""
        t = str(text)
        # 全角→半角（可能な範囲）
        t = unicodedata.normalize("NFKC", t)
        # 丸数字→通常数字
        t = t.translate(self._CIRCLED_MAP)
        # 余計な連続空白を整理
        t = re.sub(r"[ \t]{2,}", " ", t)
        return t.strip()

    # よくあるOCR誤認識パターン（文字化け・文字間違い）
    _OCR_FIX_PATTERNS = [
        # 数字と文字の誤認識（より積極的に）
        (r'\bO\b', '0'),  # 単独のO → 0
        (r'\bl\b', '1'),  # 単独のl → 1
        (r'\bS\b', '5'),  # 単独のS → 5
        (r'\bB\b', '8'),  # 単独のB → 8
        (r'\bI\b', '1'),  # 単独のI → 1
        (r'\bZ\b', '2'),  # 単独のZ → 2
        # よくある文字化けパターン（拡張）
        (r'文宇', '文字'),
        (r'読取', '読取'),
        (r'認識', '認識'),
        (r'文字化け', '文字化け'),
        (r'誤認識', '誤認識'),
        (r'読み取り', '読み取り'),
        # 全角/半角の統一（数字・英字・記号）
        (r'０', '0'), (r'１', '1'), (r'２', '2'), (r'３', '3'), (r'４', '4'),
        (r'５', '5'), (r'６', '6'), (r'７', '7'), (r'８', '8'), (r'９', '9'),
        (r'（', '('), (r'）', ')'), (r'，', ','), (r'．', '.'), (r'：', ':'),
        (r'；', ';'), (r'？', '?'), (r'！', '!'), (r'ー', '-'), (r'～', '~'),
        # よくある誤認識パターン（日報関連）
        (r'ハイオク', 'ハイオク'),
        (r'レギュラー', 'レギュラー'),
        (r'軽油', '軽油'),
        (r'数量', '数量'),
        (r'金額', '金額'),
        (r'合計', '合計'),
        (r'給油', '給油'),
        (r'在庫', '在庫'),
        (r'前日', '前日'),
        (r'当日', '当日'),
        (r'総合計', '総合計'),
        # よくある文字間違いパターン（拡張）
        (r'文宇', '文字'),
        (r'読取', '読取'),
        (r'誤認識', '誤認識'),
        (r'読み取り', '読み取り'),
        # 新しく発見された誤認識パターン（拡張版）
        (r'総一合一計', '総合計'),
        (r'総一合', '総合'),
        (r'現釜売上', '現金売上'),
        (r'現釜', '現金'),
        (r'レギュラニ', 'レギュラー'),
        (r'リ挥翠避', '軽油'),
        (r'揮翠避', '軽油'),
        (r'揮泰避通一', '軽油通一'),
        (r'揮泰避', '軽油'),
        (r'その地避計', 'その他避計'),
        (r'その地', 'その他'),
        (r'完料油計一', '完料油計'),
        (r'完料', '完料'),
        (r'自動車木通', '自動車用油'),
        (r'自動車木', '自動車用'),
        (r'その他自動重囲』遺油一', 'その他自動車用油'),
        (r'その他自動重囲', 'その他自動車'),
        (r'亘動用潤滑油計', '自動車用潤滑油計'),
        (r'亘動用', '自動車用'),
        (r'その価,冨樹一', 'その他'),
        (r'その価', 'その他'),
        (r'研廻', '研修'),
        (r'金_額', '金額'),
        (r'数_量', '数量'),
        (r'金額_', '金額'),
        (r'数量_', '数量'),
        (r'数量二', '数量'),
        (r'金額一', '金額'),
        (r'粗利金額_', '粗利金額'),
        (r'トノロ比', '粗利率'),
        (r'川杉比', '粗利率'),
        (r'見微し', '見積'),
        (r'見 微 し', '見積'),
        (r'見微', '見積'),
        (r'乙617', '617'),
        (r'四9', '49'),
        (r'辺6', '6'),
        (r'血4', '4'),
        (r'山四', '山'),
        (r'11河', '11'),
        (r'54,69一', '54,69'),
        (r'31,29一', '31,29'),
        (r'33.00_', '33.00'),
        (r'0 00', '0.00'),
        (r'0.00_', '0.00'),
        # アンダースコアの誤認識（拡張）
        (r'_$', ''),  # 末尾のアンダースコアを削除
        (r'金額_', '金額'),
        (r'数量_', '数量'),
        (r'粗利金額_', '粗利金額'),
        (r'合計_', '合計'),
        (r'売上_', '売上'),
        # よくある誤認識パターン（拡張）
        (r'トノロ比', '粗利率'),
        (r'川杉比', '粗利率'),
        (r'粗利比', '粗利率'),
        (r'研廻', '研修'),
        (r'完料', '完料'),
        (r'完料油', '完料油'),
        # 数字の連続誤認識パターン（例: "617.672116,578.2112234.472" → 適切に分割）
        # ただし、これは文脈依存なのでLLMに任せる
        # より積極的な修正パターン
        (r'一$', ''),  # 末尾の「一」を削除（誤認識の可能性）
        (r'二$', ''),  # 末尾の「二」を削除（誤認識の可能性）
        (r'計一$', '計'),  # 「計一」→「計」
        (r'計二$', '計'),  # 「計二」→「計」
    ]

    def _fix_common_ocr_errors(self, text: str) -> str:
        """よくあるOCR誤認識を自動修正"""
        if not text:
            return text
        t = str(text)
        # パターンマッチで修正（ただし、文脈を考慮して慎重に）
        for pattern, replacement in self._OCR_FIX_PATTERNS:
            # 単独の文字のみ（単語境界で囲まれた場合）
            if pattern.startswith(r'\b') and pattern.endswith(r'\b'):
                # 数字の前後が数字や記号でない場合のみ置換
                t = re.sub(pattern, replacement, t)
            else:
                t = re.sub(pattern, replacement, t)
        return t

    def _looks_numeric(self, s: str) -> bool:
        """数値っぽい（ここは絶対にLLMで触らない）"""
        s = s.strip()
        if not s:
            return True
        # カンマ・小数点・括弧・% を許容して数値判定
        s2 = s.replace(",", "").replace(" ", "")
        s2 = s2.replace("(", "").replace(")", "").replace("%", "")
        s2 = s2.replace("－", "-")
        return bool(re.fullmatch(r"[-+]?\d+(\.\d+)?", s2))

    def _has_japanese(self, s: str) -> bool:
        return bool(re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", s))

    def _has_mojibake_like(self, s: str) -> bool:
        """
        文字化けっぽさの簡易判定。
        - U+FFFD（replacement char）が含まれる
        - 制御文字が混ざる（改行/タブ除く）
        """
        if not s:
            return False
        if "\ufffd" in s:
            return True
        for ch in s:
            o = ord(ch)
            if o < 32 and ch not in ("\n", "\r", "\t"):
                return True
        return False

    def _build_col_headers(self, df: pd.DataFrame, top_n: int = 6) -> Dict[int, str]:
        """列ごとに上側から見出しっぽい値を拾う（なければ空）"""
        headers: Dict[int, str] = {}
        n = min(len(df), top_n)
        for col_idx in range(len(df.columns)):
            header = ""
            for r in range(n):
                v = df.iat[r, col_idx]
                if pd.isna(v):
                    continue
                s = str(v).strip()
                if s:
                    header = s[:40]
                    break
            headers[col_idx] = header
        return headers

    def _build_cell_context(self, df: pd.DataFrame, row_idx: int, col_idx: int, col_headers: Dict[int, str]) -> str:
        """近傍・列見出し・行スニペットを短くまとめてLLMに渡す"""
        def _s(v) -> str:
            if v is None or (isinstance(v, float) and pd.isna(v)) or pd.isna(v):
                return ""
            return str(v).strip()

        left = _s(df.iat[row_idx, col_idx - 1]) if col_idx - 1 >= 0 else ""
        right = _s(df.iat[row_idx, col_idx + 1]) if col_idx + 1 < len(df.columns) else ""
        up = _s(df.iat[row_idx - 1, col_idx]) if row_idx - 1 >= 0 else ""
        down = _s(df.iat[row_idx + 1, col_idx]) if row_idx + 1 < len(df) else ""

        c0 = max(0, col_idx - 2)
        c1 = min(len(df.columns) - 1, col_idx + 2)
        row_snip_vals = []
        for c in range(c0, c1 + 1):
            if c == col_idx:
                continue
            sv = _s(df.iat[row_idx, c])
            if sv:
                row_snip_vals.append(sv[:30])
        row_snip = " | ".join(row_snip_vals[:5])

        header = (col_headers.get(col_idx) or "").strip()

        parts = []
        if header:
            parts.append(f"列: {header}")
        if up:
            parts.append(f"上: {up[:40]}")
        if left:
            parts.append(f"左: {left[:40]}")
        if right:
            parts.append(f"右: {right[:40]}")
        if down:
            parts.append(f"下: {down[:40]}")
        if row_snip:
            parts.append(f"同行: {row_snip}")
        return " / ".join(parts)

    def correct_cell_text(self, text: str, context: str = "") -> Optional[str]:
        """
        セルのテキストをLLMで修正

        Args:
            text: 修正するテキスト
            context: 周辺コンテキスト（同じ行・列の情報）
        """
        if not text or not str(text).strip():
            return text

        # まず正規化（丸数字→数字、全角→半角など）
        normalized = self._normalize_text(str(text))
        if normalized != str(text):
            text = normalized

        # よくあるOCR誤認識を自動修正
        fixed = self._fix_common_ocr_errors(text)
        if fixed != text:
            text = fixed

        # 数値セルは絶対に触らない
        if self._looks_numeric(text):
            self.stats['skipped_cells'] += 1
            return text

        # 文字化けがある場合は修正対象（日本語がなくても）
        has_mojibake = self._has_mojibake_like(text)
        if not self._has_japanese(text) and not has_mojibake:
            # 日本語も文字化けもない場合はスキップ
            self.stats['skipped_cells'] += 1
            return text

        # 長すぎる場合は切り詰め
        if len(text) > self.max_cell_length:
            text = text[:self.max_cell_length]

        context_prefix = f"周辺コンテキスト: {context}\n" if context else ""

        prompt = f"""以下のOCR（光学文字認識）結果を修正してください。

OCR結果には以下の問題がある可能性があります：
- 文字化け（例: "文字" → "文宇"、"総合計" → "総一合一計"、"現金" → "現釜"、"金額" → "金_額"、"数量" → "数_量"）
- 読み取り不足（空白や改行の誤認識）
- 数字や記号の誤認識（例: "1" → "l"、"5" → "S"、"0" → "O"、"8" → "B"、"617" → "乙617"、"49" → "四9"）
- 日本語の誤認識（例: "レギュラー" → "レギュラニ"、"軽油" → "リ挥翠避"、"自動車用" → "自動車木"、"その他" → "その地"、"見積" → "見微し"、"粗利率" → "トノロ比"）
- カンマ位置の誤認識（例: "374,648" → "374,6485"、"54,69" → "54,69一"）
- 似た文字の誤認識（例: "O"と"0"、"1"と"l"、"5"と"S"、"避"と"油"、"木"と"用"、"地"と"他"、"微"と"積"）
- 数字の連続誤認識（例: "617.672116,578.2112234.472" → 適切に分割）
- アンダースコアや特殊文字の誤認識（例: "金額_" → "金額"、"数量_" → "数量"、"33.00_" → "33.00"）
- 漢字の誤認識（例: "研廻" → "研修"、"完料" → "完料"）

{context_prefix}OCR結果:
{text}

修正指示（情報を保持しながら修正）:
1. 明らかな誤字・脱字を修正してください（特に日本語の文字化け、アンダースコア、特殊文字）
2. 文脈から推測できる正しい文字に修正してください（特に数字・記号・日本語・漢字）
3. **重要**: 数字や数値データは絶対に削除しないでください（金額、数量、日付など）
4. **重要**: 複数の値が含まれている場合は、すべて保持してください（例: "2,797.45 | 374,648" はそのまま保持）
5. **重要**: 元のテキストの情報量を保持してください（短くしすぎない）
6. カンマ位置を正しく修正してください（例: "374,6485" → "374,648"、"54,69一" → "54,69"）
7. アンダースコアや末尾の余分な文字を削除してください（例: "金額_" → "金額"、"33.00_" → "33.00"）
8. よくある誤認識パターンを修正してください（例: "見微し" → "見積"、"トノロ比" → "粗利率"）
8. 日本語の誤認識を修正してください:
   - "総一合一計" → "総合計"
   - "現釜" → "現金"
   - "レギュラニ" → "レギュラー"
   - "リ挥翠避" → "軽油"
   - "揮泰避" → "軽油"
   - "その地" → "その他"
   - "自動車木" → "自動車用"
   - "亘動用" → "自動車用"
   - "完料油計一" → "完料油計"
   - "見微し" → "見積"
   - "トノロ比" → "粗利率"
   - "川杉比" → "粗利率"
   - "研廻" → "研修"
7. アンダースコアや末尾の余分な文字を削除してください:
   - "金額_" → "金額"
   - "数量_" → "数量"
   - "33.00_" → "33.00"
   - "54,69一" → "54,69"
   - "計一" → "計"
9. 数字の誤認識を修正してください:
   - "乙617" → "617"
   - "四9" → "49"
   - "11河" → "11"
10. **重要**: 複数の値が含まれている場合は、すべて保持してください（例: "2,797.45 | 374,648" はそのまま保持）
11. **重要**: 数値データ（金額、数量、日付など）は絶対に削除しないでください
12. **重要**: 元のテキストの長さや情報量を保持してください（短くしすぎない）
13. 数字の連続誤認識を修正してください（例: "617.672116,578.2112234.472" → 適切に分割）
14. 似た文字の誤認識を修正してください（O/0、1/l、5/S、8/B、避/油、木/用、地/他など）
15. 元の形式（空白、改行、区切り文字）は可能な限り保持してください
16. 修正できない部分はそのまま残してください
17. 修正が不要な場合は元のテキストをそのまま返してください

修正後のテキストのみを返してください（説明やJSON形式は不要）:"""

        try:
            result = generate(self.llm_model, prompt, timeout=30)
            if result and result.get('response'):
                corrected = result['response'].strip()

                # プロンプトの繰り返しや説明を削除
                lines = corrected.split('\n')
                # 最初の実質的なテキスト行を取得
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('修正') and not line.startswith('OCR'):
                        corrected = line
                        break

                # 情報量チェック: 元のテキストが長い場合、修正後が短すぎないか確認
                original_len = len(text)
                corrected_len = len(corrected)

                # 元のテキストに数値が含まれている場合、修正後にも数値が含まれているか確認
                original_has_numbers = bool(re.search(r'\d', text))
                corrected_has_numbers = bool(re.search(r'\d', corrected))

                # 情報が大幅に失われている場合は、元のテキストを保持
                if original_has_numbers and not corrected_has_numbers:
                    # 数値が含まれていたのに削除された場合は元のテキストを保持
                    print(f"  [WARNING] 数値データが失われたため、元のテキストを保持: {text[:50]}...")
                    return text

                # カンマを含む数値が失われた場合も保持
                original_has_comma_numbers = bool(re.search(r'\d+,\d+', text))
                corrected_has_comma_numbers = bool(re.search(r'\d+,\d+', corrected))
                if original_has_comma_numbers and not corrected_has_comma_numbers:
                    print(f"  [WARNING] カンマ付き数値が失われたため、元のテキストを保持: {text[:50]}...")
                    return text

                # 元のテキストの70%未満に短縮された場合は元のテキストを保持（50%から70%に変更）
                if corrected_len < original_len * 0.7 and original_len > 10:
                    print(f"  [WARNING] 情報が大幅に失われたため、元のテキストを保持: {text[:50]}...")
                    return text

                # 複数の値が含まれている場合（| や / で区切られている）、それらが失われた場合は保持
                original_separators = text.count('|') + text.count('/') + text.count(' / ')
                corrected_separators = corrected.count('|') + corrected.count('/') + corrected.count(' / ')
                if original_separators > 0 and corrected_separators < original_separators * 0.5:
                    print(f"  [WARNING] 複数の値が失われたため、元のテキストを保持: {text[:50]}...")
                    return text

                # 元のテキストと異なる場合のみ修正としてカウント
                if corrected != text:
                    self.stats['corrected_cells'] += 1
                    return corrected
                else:
                    return text
        except Exception as e:
            print(f"  [WARNING] LLM修正エラー: {e}")

        return text

    def correct_sheet(self, df: pd.DataFrame, sheet_name: str, verbose: bool = True) -> pd.DataFrame:
        """
        シート全体を修正

        Args:
            df: データフレーム
            sheet_name: シート名
            verbose: 詳細出力
        """
        if verbose:
            print(f"  シート '{sheet_name}': {len(df)}行 × {len(df.columns)}列を処理中...")

        corrected_df = df.copy()
        total_cells = len(df) * len(df.columns)
        processed = 0

        col_headers = self._build_col_headers(df, top_n=6)

        # 行ごとに処理（コンテキストを保持）
        for idx, row in df.iterrows():
            if verbose and (idx + 1) % 10 == 0:
                print(f"    行 {idx + 1}/{len(df)} を処理中...")

            for col_idx, col_name in enumerate(df.columns):
                cell_value = row[col_name]

                # 空セルや数値のみのセルはスキップ
                if pd.isna(cell_value):
                    continue

                cell_str = str(cell_value)

                # 正規化
                cell_str_norm = self._normalize_text(cell_str)
                if cell_str_norm != cell_str:
                    corrected_df.at[idx, col_name] = cell_str_norm
                    cell_str = cell_str_norm

                # よくあるOCR誤認識を自動修正（ルールベース）
                fixed = self._fix_common_ocr_errors(cell_str)
                if fixed != cell_str:
                    corrected_df.at[idx, col_name] = fixed
                    cell_str = fixed
                    self.stats['corrected_cells'] += 1

                # 純粋な数値セルはスキップ（数値の誤認識は危険）
                # ただし、数値と文字が混在している場合は修正対象
                is_pure_numeric = self._looks_numeric(cell_str) and not self._has_japanese(cell_str)
                if is_pure_numeric:
                    self.stats['skipped_cells'] += 1
                    continue

                # 短すぎるセルもスキップ（修正の必要性が低い）
                if len(cell_str) < 2:  # 2文字以上に変更（"0"→"O"などの修正のため）
                    continue

                # LLMで修正（より積極的に適用）
                # 文字化けの可能性をチェック（� や制御文字が含まれている場合）
                has_mojibake = self._has_mojibake_like(cell_str)
                # 日本語が含まれている、または文字化けの可能性がある、または長い文字列の場合
                should_correct = (
                    self._has_japanese(cell_str) or
                    has_mojibake or
                    len(cell_str) >= 5  # 5文字以上は修正対象に
                )

                if should_correct:
                    context = self._build_cell_context(df, idx, col_idx, col_headers)
                    corrected = self.correct_cell_text(cell_str, context)
                    if corrected != cell_str:
                        corrected_df.at[idx, col_name] = corrected

                processed += 1
                self.stats['total_cells'] += 1

        if verbose:
            print(f"  [OK] シート '{sheet_name}' の処理完了")

        return corrected_df

    def correct_excel(
        self,
        input_excel_path: str,
        output_excel_path: str,
        sheet_names: Optional[List[str]] = None,
        max_sheets: Optional[int] = None,
        verbose: bool = True
    ) -> str:
        """
        Excelファイル全体を修正

        Args:
            input_excel_path: 入力Excelファイルパス
            output_excel_path: 出力Excelファイルパス
            sheet_names: 処理するシート名（Noneの場合は全シート）
            verbose: 詳細出力
        """
        if not LLM_AVAILABLE:
            raise RuntimeError("LLMが利用できません。local_llm_helperをインストールしてください。")

        print(f"Excelファイルを読み込み中: {input_excel_path}")
        df_dict = pd.read_excel(input_excel_path, sheet_name=None)

        if sheet_names:
            df_dict = {name: df_dict[name] for name in sheet_names if name in df_dict}

        # 最大シート数制限
        if max_sheets and len(df_dict) > max_sheets:
            print(f"  注意: {len(df_dict)}シート中、最初の{max_sheets}シートのみ処理します")
            df_dict = dict(list(df_dict.items())[:max_sheets])

        print(f"  {len(df_dict)}シートを処理します")

        corrected_dict = {}

        for sheet_name, df in df_dict.items():
            print(f"\nシート '{sheet_name}' を処理中...")
            corrected_df = self.correct_sheet(df, sheet_name, verbose=verbose)
            corrected_dict[sheet_name] = corrected_df

        # Excelに書き込み
        print(f"\n修正済みExcelファイルを保存中: {output_excel_path}")
        with pd.ExcelWriter(output_excel_path, engine='openpyxl') as writer:
            for sheet_name, df in corrected_dict.items():
                # シート名制限（31文字）
                safe_sheet_name = sheet_name[:31] if len(sheet_name) > 31 else sheet_name
                df.to_excel(writer, sheet_name=safe_sheet_name, index=False, header=False)

        print(f"\n[OK] 修正完了: {output_excel_path}")
        print(f"\n📊 統計:")
        print(f"  - 処理セル数: {self.stats['total_cells']}")
        print(f"  - 修正セル数: {self.stats['corrected_cells']}")
        print(f"  - 修正率: {self.stats['corrected_cells'] / max(self.stats['total_cells'], 1) * 100:.1f}%")

        return output_excel_path


def main():
    """メイン関数"""
    if len(sys.argv) < 2:
        print("使用方法: python excel_llm_ocr_corrector.py <入力Excelファイル> [出力Excelファイル] [最大シート数]")
        print("例: python excel_llm_ocr_corrector.py input.xlsx output_corrected.xlsx")
        print("例（最初の3シートのみ）: python excel_llm_ocr_corrector.py input.xlsx output.xlsx 3")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else input_path.replace('.xlsx', '_LLM_CORRECTED.xlsx')
    max_sheets = int(sys.argv[3]) if len(sys.argv) > 3 else None

    if not os.path.exists(input_path):
        print(f"[ERROR] ファイルが見つかりません: {input_path}")
        sys.exit(1)

    # モデル選択: 環境変数 MANA_OCR_LLM_MODEL または MANA_OCR_USE_LARGE_MODEL=1 で制御
    model = os.getenv("MANA_OCR_LLM_MODEL", None)
    use_large = os.getenv("MANA_OCR_USE_LARGE_MODEL", "0").strip().lower() in ("1", "true", "yes", "y", "on")

    corrector = ExcelLLMOCRCorrector(
        llm_model=model,  # Noneの場合は内部で自動選択
        batch_size=100
    )

    if use_large:
        print(f"大きなモデルモード: {corrector.llm_model}")
    else:
        print(f"使用モデル: {corrector.llm_model} (大きなモデルを使う場合は MANA_OCR_USE_LARGE_MODEL=1 を設定)")

    try:
        result_path = corrector.correct_excel(input_path, output_path, max_sheets=max_sheets, verbose=True)
        print(f"\n完了！修正済みファイル: {result_path}")
    except KeyboardInterrupt:
        print("\n[INFO] ユーザーによって中断されました")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] エラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
