#!/usr/bin/env python3
"""
最初のMCP統合ワークフロー
コードレビュー自動化の超簡易版
"""
import asyncio
import json
from datetime import datetime

async def auto_code_review(file_path):
    """ファイルを読み込んで簡易レビュー"""
    
    print(f"\n🔍 自動コードレビュー開始: {file_path}")
    print("=" * 60)
    
    # 1. Filesystem MCPでファイル読み込み（模擬）
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        print("✅ ファイル読み込み成功")
    except Exception as e:
        print(f"❌ ファイル読み込みエラー: {e}")
        return None
    
    # 2. 簡易チェック（実際はAI Learning MCP等を使う）
    issues = []
    warnings = []
    
    lines = code.split('\n')
    
    # チェック項目
    if 'TODO' in code or 'FIXME' in code:
        issues.append("未完了のTODO/FIXMEコメントが残っています")
    
    if len(lines) > 500:
        warnings.append(f"ファイルが長めです（{len(lines)}行）。分割を検討してください")
    
    if 'import *' in code:
        issues.append("ワイルドカードインポート（import *）は避けるべきです")
    
    if 'print(' in code and file_path.endswith('.py'):
        warnings.append("デバッグ用printが残っている可能性があります")
    
    # 良い点も検出
    good_points = []
    if '"""' in code or "'''" in code:
        good_points.append("ドキュメント文字列がきちんと書かれています")
    
    if 'def test_' in code or 'class Test' in code:
        good_points.append("テストコードが含まれています")
    
    if 'async def' in code:
        good_points.append("非同期処理を活用しています")
    
    # 3. 結果を生成
    result = {
        "file": file_path,
        "timestamp": datetime.now().isoformat(),
        "stats": {
            "lines": len(lines),
            "characters": len(code),
            "functions": code.count('def '),
            "classes": code.count('class ')
        },
        "issues": issues,
        "warnings": warnings,
        "good_points": good_points,
        "status": "needs_fix" if issues else ("approved_with_warnings" if warnings else "approved")
    }
    
    # 4. 結果表示
    print("\n📊 レビュー結果")
    print(f"   行数: {result['stats']['lines']}")
    print(f"   文字数: {result['stats']['characters']}")
    print(f"   関数: {result['stats']['functions']}個")
    print(f"   クラス: {result['stats']['classes']}個")
    
    if good_points:
        print(f"\n✅ 良い点 ({len(good_points)}件):")
        for point in good_points:
            print(f"     ✓ {point}")
    
    if issues:
        print(f"\n❌ 問題 ({len(issues)}件):")
        for issue in issues:
            print(f"     × {issue}")
    
    if warnings:
        print(f"\n⚠️  警告 ({len(warnings)}件):")
        for warning in warnings:
            print(f"     ! {warning}")
    
    # 判定
    status_emoji = {
        "approved": "✅",
        "approved_with_warnings": "⚠️ ",
        "needs_fix": "❌"
    }
    status_text = {
        "approved": "承認",
        "approved_with_warnings": "条件付き承認",
        "needs_fix": "要修正"
    }
    
    print(f"\n{status_emoji[result['status']]} 総合判定: {status_text[result['status']]}")
    
    # 5. 結果をファイルに保存（Memory MCP代わり）
    output_file = f"/root/code_review_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 レビュー結果を保存: {output_file}")
    print("=" * 60)
    
    return result

async def batch_review(file_paths):
    """複数ファイルを一括レビュー"""
    print("\n🚀 バッチレビュー開始")
    print(f"対象ファイル: {len(file_paths)}個")
    
    results = []
    for file_path in file_paths:
        result = await auto_code_review(file_path)
        if result:
            results.append(result)
        await asyncio.sleep(0.1)
    
    # サマリー
    print("\n" + "=" * 60)
    print("📊 バッチレビュー完了サマリー")
    print("=" * 60)
    
    approved = sum(1 for r in results if r['status'] == 'approved')
    approved_with_warnings = sum(1 for r in results if r['status'] == 'approved_with_warnings')
    needs_fix = sum(1 for r in results if r['status'] == 'needs_fix')
    
    print(f"✅ 承認: {approved}件")
    print(f"⚠️  条件付き承認: {approved_with_warnings}件")
    print(f"❌ 要修正: {needs_fix}件")
    print(f"合計: {len(results)}件")
    
    return results

# 実行例
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 2:
        # 複数ファイル指定
        files = sys.argv[1:]
        print(f"バッチレビューモード: {len(files)}ファイル")
        asyncio.run(batch_review(files))
    elif len(sys.argv) > 1:
        # 単一ファイル指定
        file = sys.argv[1]
        asyncio.run(auto_code_review(file))
    else:
        # デフォルト: デモファイルをレビュー
        print("使い方: python3 my_first_mcp_workflow.py <file_path>")
        print("デフォルトでデモファイルをレビューします\n")
        asyncio.run(auto_code_review("/root/mcp_quick_demo.py"))

