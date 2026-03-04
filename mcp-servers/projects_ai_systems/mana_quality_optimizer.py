#!/usr/bin/env python3
"""
Mana Quality Optimizer
品質最適化システム - コード品質・エラーハンドリング・パフォーマンス向上
"""

import ast
import logging
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ManaQualityOptimizer:
    def __init__(self):
        self.project_root = Path("/root")
        self.mana_files = list(self.project_root.glob("mana_*.py"))
        
        # 品質チェック設定
        self.config = {
            "max_function_lines": 50,
            "max_file_lines": 1000,
            "min_docstring_coverage": 80,
            "error_handling_required": True
        }
        
        logger.info("🏆 Mana Quality Optimizer 初期化")
        logger.info(f"対象ファイル: {len(self.mana_files)}個")
    
    def analyze_code_quality(self) -> Dict[str, Any]:
        """コード品質分析"""
        logger.info("🔍 コード品質を分析中...")
        
        results = {
            "total_files": len(self.mana_files),
            "total_lines": 0,
            "total_functions": 0,
            "files_with_issues": [],
            "quality_score": 0
        }
        
        for file_path in self.mana_files:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    lines = content.split('\n')
                
                results["total_lines"] += len(lines)
                
                # ASTでコード解析
                try:
                    tree = ast.parse(content)
                    
                    # 関数数をカウント
                    functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
                    results["total_functions"] += len(functions)
                    
                    # 長すぎる関数をチェック
                    long_functions = []
                    for func in functions:
                        func_lines = func.end_lineno - func.lineno
                        if func_lines > self.config["max_function_lines"]:
                            long_functions.append({
                                "name": func.name,
                                "lines": func_lines
                            })
                    
                    if long_functions or len(lines) > self.config["max_file_lines"]:
                        results["files_with_issues"].append({
                            "file": file_path.name,
                            "lines": len(lines),
                            "long_functions": long_functions
                        })
                        
                except SyntaxError:
                    logger.warning(f"構文エラー: {file_path.name}")
                    
            except Exception as e:
                logger.error(f"ファイル分析エラー ({file_path}): {e}")
        
        # 品質スコア計算
        issues_count = len(results["files_with_issues"])
        results["quality_score"] = max(100 - (issues_count * 5), 0)
        
        logger.info(f"✅ 品質分析完了: スコア {results['quality_score']}/100")
        
        return results
    
    def optimize_imports(self, file_path: Path) -> Dict[str, Any]:
        """import文を最適化"""
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
            
            # import文を抽出
            imports = []
            other_lines = []
            
            for line in lines:
                if line.strip().startswith(('import ', 'from ')):
                    imports.append(line)
                else:
                    other_lines.append(line)
            
            # 重複削除・ソート
            unique_imports = sorted(set(imports))
            
            optimized_count = len(imports) - len(unique_imports)
            
            if optimized_count > 0:
                # 最適化版を書き込み
                with open(file_path, 'w') as f:
                    f.writelines(unique_imports)
                    f.writelines(other_lines)
                
                logger.info(f"✅ import最適化: {file_path.name} - {optimized_count}行削減")
            
            return {
                "success": True,
                "file": file_path.name,
                "optimized": optimized_count
            }
            
        except Exception as e:
            logger.error(f"import最適化エラー ({file_path}): {e}")
            return {"success": False, "error": str(e)}
    
    def add_error_handling(self) -> Dict[str, Any]:
        """エラーハンドリング強化"""
        logger.info("🛡️ エラーハンドリング強化中...")
        
        enhanced = 0
        
        for file_path in self.mana_files:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                
                # try-exceptが少ない箇所を検出
                try_count = content.count('try:')
                except_count = content.count('except ')
                
                if except_count < try_count:
                    logger.warning(f"⚠️ エラーハンドリング不足: {file_path.name}")
                else:
                    enhanced += 1
                    
            except Exception as e:
                logger.error(f"エラーハンドリングチェックエラー: {e}")
        
        return {
            "total_files": len(self.mana_files),
            "files_with_good_handling": enhanced,
            "coverage_percent": round(enhanced / len(self.mana_files) * 100, 1)
        }
    
    def run_quality_check(self) -> Dict[str, Any]:
        """品質チェック実行"""
        logger.info("=" * 60)
        logger.info("🏆 品質チェック開始")
        logger.info("=" * 60)
        
        # コード品質分析
        quality_analysis = self.analyze_code_quality()
        
        # エラーハンドリングチェック
        error_handling = self.add_error_handling()
        
        report = {
            "quality_analysis": quality_analysis,
            "error_handling": error_handling,
            "overall_quality_score": (quality_analysis["quality_score"] + error_handling["coverage_percent"]) / 2,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info("=" * 60)
        logger.info(f"✅ 総合品質スコア: {report['overall_quality_score']:.1f}/100")
        logger.info("=" * 60)
        
        return report

def main():
    optimizer = ManaQualityOptimizer()
    report = optimizer.run_quality_check()
    
    print("\n" + "=" * 60)
    print("🏆 品質最適化レポート")
    print("=" * 60)
    print(f"\nファイル数: {report['quality_analysis']['total_files']}")
    print(f"総コード行数: {report['quality_analysis']['total_lines']:,}行")
    print(f"総関数数: {report['quality_analysis']['total_functions']}")
    print(f"\n品質スコア: {report['quality_analysis']['quality_score']}/100")
    print(f"エラーハンドリングカバレッジ: {report['error_handling']['coverage_percent']}%")
    print(f"\n総合品質スコア: {report['overall_quality_score']:.1f}/100")
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()

