#!/usr/bin/env python3
"""
Trinity Orchestrator - Main Entry Point
CLI/API両対応のエントリーポイント
"""

import argparse
import json
import os
import sys
from datetime import datetime

from core import TrinityOrchestrator


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="Trinity Orchestrator - マルチエージェント制御エンジン",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 基本的な使い方
  python3 main.py --goal "TODOアプリを作成"
  
  # コンテキストを指定
  python3 main.py --goal "計算機アプリ" --context "Python" "CLI" "関数化"
  
  # ターン数を制限
  python3 main.py --goal "シンプルなブログ" --budget 15
  
  # 静かモード
  python3 main.py --goal "Hello World" --quiet
        """
    )
    
    parser.add_argument(
        "--goal",
        required=True,
        help="達成目標"
    )
    
    parser.add_argument(
        "--context",
        nargs="*",
        default=[],
        help="前提条件・制約（スペース区切り）"
    )
    
    parser.add_argument(
        "--budget",
        type=int,
        default=12,
        help="最大ターン数（デフォルト: 12）"
    )
    
    parser.add_argument(
        "--redis-host",
        default="localhost",
        help="Redisホスト（デフォルト: localhost）"
    )
    
    parser.add_argument(
        "--redis-port",
        type=int,
        default=6379,
        help="Redisポート（デフォルト: 6379）"
    )
    
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="静かモード（ログ出力を抑制）"
    )
    
    parser.add_argument(
        "--output",
        help="結果をJSONファイルに保存"
    )
    
    args = parser.parse_args()
    
    # APIキー確認
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY not set")
        print("\nSet it with:")
        print("  export OPENAI_API_KEY='your-api-key'")
        print("\nOr add to ~/.bashrc:")
        print("  echo 'export OPENAI_API_KEY=\"your-api-key\"' >> ~/.bashrc")
        print("  source ~/.bashrc")
        sys.exit(1)
    
    # バナー表示
    if not args.quiet:
        print_banner()
    
    # Orchestrator初期化
    try:
        orchestrator = TrinityOrchestrator(
            redis_host=args.redis_host,
            redis_port=args.redis_port
        )
        orchestrator.verbose = not args.quiet
        
    except Exception as e:
        print(f"❌ Initialization error: {e}")
        sys.exit(1)
    
    # 実行
    try:
        if not args.quiet:
            print(f"\n🎯 Goal: {args.goal}")
            if args.context:
                print(f"📋 Context: {', '.join(args.context)}")
            print(f"⏱️ Budget: {args.budget} turns")
            print("\n" + "="*60)
            print()
        
        result = orchestrator.run(
            goal=args.goal,
            context=args.context,
            budget_turns=args.budget
        )
        
        # 結果表示
        if not args.quiet:
            print("\n" + "="*60)
            print("📊 Final Result")
            print("="*60)
            print(f"🎫 Ticket ID: {result['ticket_id']}")
            print(f"🏁 Status: {result['final_status']}")
            print(f"💯 Confidence: {result['confidence']:.2f}")
            print(f"🔄 Turns: {result['turns']}/{args.budget}")
            print(f"🎁 Artifacts: {len(result['artifacts'])} items")
            
            if result['artifacts']:
                print("\n📦 Generated Files:")
                for artifact in result['artifacts']:
                    print(f"  - {artifact['path']}")
                    if artifact.get('description'):
                        print(f"    {artifact['description']}")
        
        # ファイル出力
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"\n💾 Result saved to: {args.output}")
        
        # 終了コード
        sys.exit(0 if result['final_status'] == 'completed' else 1)
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        if not args.quiet:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def print_banner():
    """バナー表示"""
    banner = r"""
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║   ████████╗██████╗ ██╗███╗   ██╗██╗████████╗██╗   ██╗  ║
║   ╚══██╔══╝██╔══██╗██║████╗  ██║██║╚══██╔══╝╚██╗ ██╔╝  ║
║      ██║   ██████╔╝██║██╔██╗ ██║██║   ██║    ╚████╔╝   ║
║      ██║   ██╔══██╗██║██║╚██╗██║██║   ██║     ╚██╔╝    ║
║      ██║   ██║  ██║██║██║ ╚████║██║   ██║      ██║     ║
║      ╚═╝   ╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝╚═╝   ╚═╝      ╚═╝     ║
║                                                          ║
║              Orchestrator v1.0                           ║
║          Multi-Agent Control Engine                      ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
"""
    print(banner)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()


if __name__ == "__main__":
    main()



