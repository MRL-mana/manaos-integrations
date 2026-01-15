#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File Secretary LLM統合テスト
常時起動LLM（Ollama）との統合確認
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from file_secretary_db import FileSecretaryDB
from file_secretary_organizer import FileOrganizer
from file_secretary_schemas import FileRecord, FileType, FileStatus, FileSource
from datetime import datetime

def test_ollama_connection():
    """Ollama接続テスト"""
    print("=== Ollama接続テスト ===")
    try:
        import httpx
        response = httpx.get("http://localhost:11434/api/tags", timeout=5.0)
        if response.status_code == 200:
            models = response.json().get("models", [])
            print(f"✅ Ollama接続成功")
            print(f"   利用可能モデル数: {len(models)}")
            if models:
                print(f"   モデル例: {models[0].get('name', 'unknown')}")
            return True
        else:
            print(f"⚠️ Ollama接続失敗: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Ollama接続不可: {e}")
        return False

def test_llm_tag_inference():
    """LLMタグ推定テスト"""
    print("\n=== LLMタグ推定テスト ===")
    try:
        db = FileSecretaryDB('file_secretary.db')
        organizer = FileOrganizer(db)
        
        # テスト用FileRecord作成
        test_file = FileRecord(
            id="test_llm_001",
            source=FileSource.MOTHER,
            path="test_日報_2026年1月.pdf",
            original_name="test_日報_2026年1月.pdf",
            created_at=datetime.now().isoformat(),
            status=FileStatus.TRIAGED,
            type=FileType.PDF,
            size=1024
        )
        
        # LLMタグ推定
        tags = organizer._infer_tags_llm(test_file)
        print(f"✅ LLMタグ推定成功")
        print(f"   推定タグ: {tags}")
        
        db.close()
        return len(tags) > 0
    except Exception as e:
        print(f"⚠️ LLMタグ推定エラー: {e}")
        return False

def test_keyword_fallback():
    """キーワードベースフォールバックテスト"""
    print("\n=== キーワードベースフォールバックテスト ===")
    try:
        db = FileSecretaryDB('file_secretary.db')
        organizer = FileOrganizer(db)
        
        # テスト用FileRecord作成
        test_file = FileRecord(
            id="test_keyword_001",
            source=FileSource.MOTHER,
            path="test_日報.pdf",
            original_name="test_日報.pdf",
            created_at=datetime.now().isoformat(),
            status=FileStatus.TRIAGED,
            type=FileType.PDF,
            size=1024
        )
        
        # キーワードベースタグ推定
        tags = organizer._infer_tags_simple(test_file)
        print(f"✅ キーワードベースタグ推定成功")
        print(f"   推定タグ: {tags}")
        
        db.close()
        return True
    except Exception as e:
        print(f"⚠️ キーワードベースタグ推定エラー: {e}")
        return False

def main():
    """メイン処理"""
    print("=" * 60)
    print("File Secretary LLM統合テスト")
    print("=" * 60)
    
    results = {}
    results['ollama_connection'] = test_ollama_connection()
    results['llm_tag_inference'] = test_llm_tag_inference() if results['ollama_connection'] else False
    results['keyword_fallback'] = test_keyword_fallback()
    
    print("\n" + "=" * 60)
    print("統合テスト結果")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "✅ OK" if result else "❌ NG"
        print(f"{name:25s}: {status}")
    
    print(f"\n合計: {passed}/{total} テスト通過")
    
    if results['ollama_connection']:
        print("\n🎉 Ollama統合は動作しています！")
        if results['llm_tag_inference']:
            print("   ✅ LLMタグ推定が利用可能です")
        else:
            print("   ⚠️ LLMタグ推定は利用できません（キーワードベースにフォールバック）")
    else:
        print("\n⚠️ Ollamaが利用できません")
        print("   - Ollamaが起動しているか確認してください")
        print("   - キーワードベースのタグ推定が使用されます")

if __name__ == '__main__':
    main()






















