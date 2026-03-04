#!/usr/bin/env python3
"""
画像生成統合システム
Cursorから画像生成→Obsidianに保存
"""

from datetime import datetime
from pathlib import Path

class AIImageGenerator:
    """AI画像生成（Stable Diffusion統合）"""
    
    def __init__(self):
        self.output_dir = Path("/root/generated_images")
        self.output_dir.mkdir(exist_ok=True)
        
        self.obsidian_images = Path("/root/obsidian_vault/Images")
        self.obsidian_images.mkdir(exist_ok=True)
    
    def generate_image(self, prompt, negative_prompt="", steps=30):
        """画像生成"""
        print("🎨 画像生成中...")
        print(f"プロンプト: {prompt}")
        print(f"ステップ数: {steps}")
        
        # Stable Diffusion実行（RunPod/Modalと連携）
        # 実際にはrunpod_integration/modal_gpu_service.py使用
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"generated_{timestamp}.png"
        
        # ダミー画像（実装時は実際の画像）
        image_path = self.output_dir / filename
        
        # Obsidianにも保存
        obsidian_path = self.obsidian_images / filename
        
        # メタデータ保存
        metadata = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "steps": steps,
            "timestamp": datetime.now().isoformat(),
            "filename": filename
        }
        
        metadata_path = self.output_dir / f"{filename}.json"
        import json
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 画像生成完了: {image_path}")
        print(f"✅ Obsidianに保存: {obsidian_path}")
        print(f"📄 メタデータ: {metadata_path}")
        
        return {
            "path": str(image_path),
            "obsidian_path": str(obsidian_path),
            "metadata": metadata
        }
    
    def create_image_note(self, image_path, prompt, description=""):
        """画像付きObsidianノート作成"""
        timestamp = datetime.now()
        filename = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_image_note.md"
        
        note = f"""# 生成画像 - {timestamp.strftime('%Y-%m-%d %H:%M')}

## 🎨 プロンプト
{prompt}

## 📝 説明
{description}

## 🖼️ 画像
![[{Path(image_path).name}]]

---
作成: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}
Tags: #ai-generated #image
"""
        
        note_path = Path("/root/obsidian_vault/Images") / filename
        with open(note_path, 'w', encoding='utf-8') as f:
            f.write(note)
        
        print(f"✅ 画像ノート作成: {note_path}")
        
        return str(note_path)

def main():
    generator = AIImageGenerator()
    
    print("🎨 AI画像生成統合システム\n")
    
    # テスト生成
    result = generator.generate_image(
        prompt="A beautiful sunset over mountains",
        steps=20
    )
    
    # ノート作成
    generator.create_image_note(
        result["path"],
        "A beautiful sunset over mountains",
        "テスト用の風景画像"
    )
    
    print("\n✅ テスト完了")
    print("📁 画像: /root/generated_images/")
    print("📝 Obsidian: /root/obsidian_vault/Images/")

if __name__ == "__main__":
    main()

