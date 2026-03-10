#!/usr/bin/env python3
"""
レポート自動生成システム
Excel, PDF, Markdownレポート生成
"""

import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from pathlib import Path
from typing import Dict


class ReportGenerator:
    """レポート自動生成"""
    
    def __init__(self):
        self.reports_dir = Path("/root/url_summarization_system/reports")
        self.reports_dir.mkdir(exist_ok=True)
        
        # 日本語フォント設定
        plt.rcParams['font.family'] = 'DejaVu Sans'
    
    def generate_excel_report(self, data: Dict, filename: str = None) -> str:  # type: ignore
        """Excelレポート生成"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"report_{timestamp}.xlsx"
        
        filepath = self.reports_dir / filename
        
        try:
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # サマリーシート
                if "summary" in data:
                    summary_df = pd.DataFrame([{"項目": "要約", "内容": data["summary"]}])
                    summary_df.to_excel(writer, sheet_name="サマリー", index=False)
                
                # 記事一覧シート
                if "articles" in data:
                    articles_data = []
                    for article in data["articles"]:
                        articles_data.append({
                            "タイトル": article.get("title", ""),
                            "URL": article.get("url", ""),
                            "文字数": article.get("word_count", 0),
                            "内容": article.get("content", "")[:500]
                        })
                    articles_df = pd.DataFrame(articles_data)
                    articles_df.to_excel(writer, sheet_name="記事一覧", index=False)
                
                # 統計シート
                if "articles" in data:
                    stats_data = {
                        "項目": ["記事数", "平均文字数", "合計文字数"],
                        "値": [
                            len(data["articles"]),
                            sum([a.get("word_count", 0) for a in data["articles"]]) / len(data["articles"]) if data["articles"] else 0,
                            sum([a.get("word_count", 0) for a in data["articles"]])
                        ]
                    }
                    stats_df = pd.DataFrame(stats_data)
                    stats_df.to_excel(writer, sheet_name="統計", index=False)
            
            return str(filepath)
        
        except Exception as e:
            return f"エラー: {str(e)}"
    
    def generate_markdown_report(self, data: Dict, filename: str = None) -> str:  # type: ignore
        """Markdownレポート生成"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"report_{timestamp}.md"
        
        filepath = self.reports_dir / filename
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"# {data.get('query', 'レポート')}\n\n")
                f.write(f"**生成日時**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                # サマリー
                if "summary" in data:
                    f.write("## 📊 総合サマリー\n\n")
                    f.write(f"{data['summary']}\n\n")
                
                # 記事一覧
                if "articles" in data:
                    f.write(f"## 📰 記事一覧 ({len(data['articles'])}件)\n\n")
                    
                    for i, article in enumerate(data["articles"], 1):
                        f.write(f"### {i}. {article.get('title', 'タイトルなし')}\n\n")
                        f.write(f"**URL**: {article.get('url', '')}\n\n")
                        f.write(f"**文字数**: {article.get('word_count', 0)}文字\n\n")
                        f.write(f"**内容**:\n{article.get('content', '')[:300]}...\n\n")
                        f.write("---\n\n")
                
                # 統計
                if "articles" in data:
                    f.write("## 📈 統計情報\n\n")
                    f.write(f"- **記事数**: {len(data['articles'])}件\n")
                    f.write(f"- **平均文字数**: {sum([a.get('word_count', 0) for a in data['articles']]) / len(data['articles']) if data['articles'] else 0:.0f}文字\n")
                    f.write(f"- **合計文字数**: {sum([a.get('word_count', 0) for a in data['articles']])}文字\n\n")
            
            return str(filepath)
        
        except Exception as e:
            return f"エラー: {str(e)}"
    
    def generate_comparison_report(self, comparison_data: Dict, filename: str = None) -> str:  # type: ignore
        """比較レポート生成"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"comparison_{timestamp}.xlsx"
        
        filepath = self.reports_dir / filename
        
        try:
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # 各企業のデータ
                for company, data in comparison_data.items():
                    if "articles" in data:
                        articles_data = []
                        for article in data["articles"]:
                            articles_data.append({
                                "タイトル": article.get("title", ""),
                                "URL": article.get("url", ""),
                                "文字数": article.get("word_count", 0)
                            })
                        df = pd.DataFrame(articles_data)
                        df.to_excel(writer, sheet_name=company[:31], index=False)
                
                # 比較サマリー
                comparison_summary = []
                for company, data in comparison_data.items():
                    comparison_summary.append({
                        "企業": company,
                        "記事数": len(data.get("articles", [])),
                        "平均文字数": sum([a.get("word_count", 0) for a in data.get("articles", [])]) / len(data.get("articles", [])) if data.get("articles") else 0
                    })
                
                summary_df = pd.DataFrame(comparison_summary)
                summary_df.to_excel(writer, sheet_name="比較サマリー", index=False)
            
            return str(filepath)
        
        except Exception as e:
            return f"エラー: {str(e)}"
    
    def generate_chart(self, data: Dict, chart_type: str = "bar") -> str:  # type: ignore
        """グラフ生成"""
        try:
            if chart_type == "bar":
                # 棒グラフ
                articles = data.get("articles", [])
                if not articles:
                    return "データがありません"
                
                titles = [a.get("title", "タイトルなし")[:20] for a in articles]
                word_counts = [a.get("word_count", 0) for a in articles]
                
                plt.figure(figsize=(12, 6))
                plt.barh(titles, word_counts)
                plt.xlabel("文字数")
                plt.title(f"記事別文字数: {data.get('query', '')}")
                plt.tight_layout()
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filepath = self.reports_dir / f"chart_{timestamp}.png"
                plt.savefig(filepath, dpi=150, bbox_inches='tight')
                plt.close()
                
                return str(filepath)
        
        except Exception as e:
            return f"エラー: {str(e)}"

