#!/usr/bin/env python3
"""
Trinity AI Smart Prompt Templates System
インテリジェントプロンプトテンプレートシステム
"""

import os
import json
import random
from datetime import datetime
from typing import List, Dict, Tuple
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SmartPromptTemplates:
    def __init__(self):
        self.templates = self._load_templates()
        self.history = []
        self.favorites = []
        
    def _load_templates(self):
        """プロンプトテンプレートを読み込む"""
        return {
            "anime": {
                "base": "a beautiful anime girl, {style}, {quality}, {mood}",
                "styles": ["kawaii", "elegant", "cute", "cool", "mysterious"],
                "quality": ["high quality", "masterpiece", "best quality", "ultra detailed"],
                "mood": ["smiling", "serene", "confident", "shy", "playful"],
                "negative": "low quality, blurry, distorted, bad anatomy"
            },
            "realistic": {
                "base": "a beautiful woman, {style}, {quality}, {lighting}, {mood}",
                "styles": ["professional", "casual", "elegant", "sporty", "artistic"],
                "quality": ["photorealistic", "high resolution", "detailed", "sharp"],
                "lighting": ["soft lighting", "dramatic lighting", "natural light", "studio lighting"],
                "mood": ["confident", "serene", "friendly", "mysterious", "happy"],
                "negative": "low quality, blurry, distorted, bad anatomy, deformed"
            },
            "fantasy": {
                "base": "a {character_type}, {magical_elements}, {setting}, {quality}",
                "character_type": ["elf", "fairy", "wizard", "knight", "princess", "mage"],
                "magical_elements": ["magical aura", "sparkling effects", "mystical energy", "enchanted"],
                "setting": ["fantasy forest", "magical castle", "enchanted garden", "mystical realm"],
                "quality": ["fantasy art", "magical", "ethereal", "mystical"],
                "negative": "low quality, blurry, distorted, bad anatomy"
            },
            "cyberpunk": {
                "base": "a {character_type}, {tech_elements}, {setting}, {quality}",
                "character_type": ["cyberpunk girl", "hacker", "android", "cyborg", "neon warrior"],
                "tech_elements": ["neon lights", "holographic", "cyber implants", "neural interface"],
                "setting": ["cyberpunk city", "neon district", "futuristic", "digital realm"],
                "quality": ["cyberpunk art", "neon aesthetic", "futuristic", "high tech"],
                "negative": "low quality, blurry, distorted, bad anatomy"
            },
            "nature": {
                "base": "a {subject}, {environment}, {weather}, {quality}",
                "subject": ["landscape", "forest", "mountain", "ocean", "sunset", "sunrise"],
                "environment": ["serene", "majestic", "peaceful", "dramatic", "tranquil"],
                "weather": ["clear sky", "misty", "stormy", "golden hour", "blue hour"],
                "quality": ["nature photography", "landscape art", "scenic", "breathtaking"],
                "negative": "low quality, blurry, distorted, artificial"
            }
        }
    
    def generate_prompt(self, category: str, custom_elements: Dict = None) -> str:  # type: ignore
        """プロンプトを生成する"""
        if category not in self.templates:
            logger.warning(f"未知のカテゴリ: {category}")
            return "a beautiful image, high quality"
        
        template = self.templates[category]
        prompt = template["base"]
        
        # テンプレート変数を置換
        for key, values in template.items():
            if key not in ["base", "negative"] and isinstance(values, list):
                if custom_elements and key in custom_elements:
                    value = custom_elements[key]
                else:
                    value = random.choice(values)
                prompt = prompt.replace(f"{{{key}}}", value)
        
        # ネガティブプロンプトを追加
        if "negative" in template:
            prompt += f", {template['negative']}"
        
        return prompt
    
    def generate_batch_prompts(self, category: str, count: int = 5) -> List[str]:
        """バッチプロンプトを生成する"""
        prompts = []
        for i in range(count):
            prompt = self.generate_prompt(category)
            prompts.append(prompt)
        return prompts
    
    def generate_style_variations(self, base_prompt: str, styles: List[str]) -> List[str]:
        """スタイルバリエーションを生成する"""
        variations = []
        for style in styles:
            variation = f"{base_prompt}, {style} style"
            variations.append(variation)
        return variations
    
    def generate_quality_variations(self, base_prompt: str, quality_levels: List[str]) -> List[str]:
        """品質バリエーションを生成する"""
        variations = []
        for quality in quality_levels:
            variation = f"{base_prompt}, {quality}"
            variations.append(variation)
        return variations
    
    def save_prompt_to_history(self, prompt: str, category: str, success: bool = True):
        """プロンプトを履歴に保存する"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "prompt": prompt,
            "category": category,
            "success": success
        }
        self.history.append(entry)
        
        # 履歴をファイルに保存
        self._save_history()
    
    def add_to_favorites(self, prompt: str, category: str):
        """プロンプトをお気に入りに追加する"""
        favorite = {
            "prompt": prompt,
            "category": category,
            "added_at": datetime.now().isoformat()
        }
        self.favorites.append(favorite)
        self._save_favorites()
        logger.info(f"✅ プロンプトをお気に入りに追加: {category}")
    
    def get_recommendations(self, category: str, count: int = 3) -> List[str]:
        """推奨プロンプトを取得する"""
        if category not in self.templates:
            return []
        
        # 履歴から成功したプロンプトを分析
        successful_prompts = [h for h in self.history if h["category"] == category and h["success"]]
        
        if len(successful_prompts) >= count:
            # 成功したプロンプトから推奨
            recommendations = [h["prompt"] for h in successful_prompts[-count:]]
        else:
            # テンプレートから生成
            recommendations = self.generate_batch_prompts(category, count)
        
        return recommendations
    
    def analyze_prompt_performance(self) -> Dict:
        """プロンプトパフォーマンスを分析する"""
        if not self.history:
            return {"total": 0, "success_rate": 0, "categories": {}}
        
        total = len(self.history)
        successful = sum(1 for h in self.history if h["success"])
        success_rate = (successful / total) * 100 if total > 0 else 0
        
        # カテゴリ別分析
        categories = {}
        for entry in self.history:
            category = entry["category"]
            if category not in categories:
                categories[category] = {"total": 0, "successful": 0}
            categories[category]["total"] += 1
            if entry["success"]:
                categories[category]["successful"] += 1
        
        # 成功率を計算
        for category in categories:
            total_cat = categories[category]["total"]
            successful_cat = categories[category]["successful"]
            categories[category]["success_rate"] = (successful_cat / total_cat) * 100 if total_cat > 0 else 0
        
        return {
            "total": total,
            "success_rate": success_rate,
            "categories": categories
        }
    
    def _save_history(self):
        """履歴をファイルに保存する"""
        try:
            with open("/root/trinity_workspace/prompt_history.json", "w") as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            logger.error(f"履歴保存エラー: {e}")
    
    def _save_favorites(self):
        """お気に入りをファイルに保存する"""
        try:
            with open("/root/trinity_workspace/prompt_favorites.json", "w") as f:
                json.dump(self.favorites, f, indent=2)
        except Exception as e:
            logger.error(f"お気に入り保存エラー: {e}")
    
    def load_history(self):
        """履歴をファイルから読み込む"""
        try:
            if os.path.exists("/root/trinity_workspace/prompt_history.json"):
                with open("/root/trinity_workspace/prompt_history.json", "r") as f:
                    self.history = json.load(f)
        except Exception as e:
            logger.error(f"履歴読み込みエラー: {e}")
    
    def load_favorites(self):
        """お気に入りをファイルから読み込む"""
        try:
            if os.path.exists("/root/trinity_workspace/prompt_favorites.json"):
                with open("/root/trinity_workspace/prompt_favorites.json", "r") as f:
                    self.favorites = json.load(f)
        except Exception as e:
            logger.error(f"お気に入り読み込みエラー: {e}")
    
    def get_available_categories(self) -> List[str]:
        """利用可能なカテゴリ一覧を取得"""
        return list(self.templates.keys())
    
    def get_category_info(self, category: str) -> Dict:
        """カテゴリ情報を取得する"""
        if category not in self.templates:
            return {}
        
        template = self.templates[category]
        return {
            "base_template": template["base"],
            "available_styles": template.get("styles", []),
            "quality_options": template.get("quality", []),
            "negative_prompt": template.get("negative", "")
        }

def main():
    """メイン実行関数"""
    print("🧠 Trinity AI Smart Prompt Templates System")
    print("=" * 60)
    
    templates = SmartPromptTemplates()
    
    # 履歴とお気に入りを読み込み
    templates.load_history()
    templates.load_favorites()
    
    # 利用可能なカテゴリ表示
    categories = templates.get_available_categories()
    print(f"📚 利用可能なカテゴリ:")
    for category in categories:
        print(f"   🎨 {category}")
    
    # 各カテゴリのサンプルプロンプト生成
    print(f"\n🎯 サンプルプロンプト生成:")
    for category in categories:
        sample_prompt = templates.generate_prompt(category)
        print(f"   {category}: {sample_prompt}")
    
    # バッチプロンプト生成デモ
    print(f"\n🚀 バッチプロンプト生成デモ:")
    batch_prompts = templates.generate_batch_prompts("anime", 3)
    for i, prompt in enumerate(batch_prompts, 1):
        print(f"   {i}. {prompt}")
    
    # スタイルバリエーションデモ
    print(f"\n🎭 スタイルバリエーションデモ:")
    base_prompt = "a beautiful girl"
    styles = ["anime", "realistic", "fantasy", "cyberpunk"]
    style_variations = templates.generate_style_variations(base_prompt, styles)
    for i, variation in enumerate(style_variations, 1):
        print(f"   {i}. {variation}")
    
    # パフォーマンス分析
    print(f"\n📊 プロンプトパフォーマンス分析:")
    performance = templates.analyze_prompt_performance()
    print(f"   総プロンプト数: {performance['total']}")
    print(f"   成功率: {performance['success_rate']:.1f}%")
    
    if performance['categories']:
        print(f"   カテゴリ別成功率:")
        for category, stats in performance['categories'].items():
            print(f"     {category}: {stats['success_rate']:.1f}% ({stats['successful']}/{stats['total']})")
    
    # お気に入り表示
    if templates.favorites:
        print(f"\n⭐ お気に入りプロンプト:")
        for i, favorite in enumerate(templates.favorites[-3:], 1):  # 最新3個
            print(f"   {i}. [{favorite['category']}] {favorite['prompt']}")
    
    print(f"\n🎉 プロンプトテンプレートシステム準備完了！")

if __name__ == "__main__":
    main()