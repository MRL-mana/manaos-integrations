#!/usr/bin/env python3
"""
🧠 ManaSpec Vector Search - 本実装
意味的な類似検索を実現
"""

import json
from pathlib import Path
from typing import List, Dict
from sentence_transformers import SentenceTransformer
import faiss

class ManaSpecVectorSearch:
    """ベクトル検索システム"""
    
    def __init__(self, index_dir: str = "/root/.manaspec/vector_index"):
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        
        self.index_file = self.index_dir / "specs.index"
        self.metadata_file = self.index_dir / "metadata.json"
        
        # モデルロード
        print("🧠 Loading embedding model...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        print("✅ Model loaded")
        
        self.index = None
        self.metadata = []
    
    def build_index(self, openspec_paths: List[str]):
        """インデックス構築"""
        print(f"\n🔨 Building vector index from {len(openspec_paths)} projects...\n")
        
        documents = []
        metadata = []
        
        # すべてのプロジェクトから収集
        for project_path in openspec_paths:
            project_path = Path(project_path)
            
            # Specs収集
            specs_dir = project_path / "openspec" / "specs"
            if specs_dir.exists():
                for spec_file in specs_dir.rglob("spec.md"):
                    content = spec_file.read_text()
                    documents.append(content)
                    metadata.append({
                        "type": "spec",
                        "path": str(spec_file),
                        "capability": spec_file.parent.name,
                        "project": project_path.name
                    })
                    print(f"  ✅ Indexed spec: {spec_file.parent.name}")
            
            # Archives収集
            archive_dir = project_path / "openspec" / "changes" / "archive"
            if archive_dir.exists():
                for proposal_file in archive_dir.rglob("proposal.md"):
                    content = proposal_file.read_text()
                    documents.append(content)
                    metadata.append({
                        "type": "archive",
                        "path": str(proposal_file),
                        "change_id": proposal_file.parent.name,
                        "project": project_path.name
                    })
                    print(f"  ✅ Indexed archive: {proposal_file.parent.name}")
        
        if not documents:
            print("⚠️ No documents found")
            return False
        
        print(f"\n🔢 Total documents: {len(documents)}")
        print("🧮 Generating embeddings...")
        
        # Embedding生成
        embeddings = self.model.encode(documents, show_progress_bar=True)
        
        print("📊 Building FAISS index...")
        
        # FAISSインデックス作成
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(embeddings.astype('float32'))
        self.metadata = metadata
        
        # 保存
        faiss.write_index(self.index, str(self.index_file))
        self.metadata_file.write_text(json.dumps(metadata, indent=2, ensure_ascii=False))
        
        print("\n✅ Index built successfully!")
        print(f"📊 Vectors: {self.index.ntotal}")
        print(f"📐 Dimensions: {dimension}")
        print(f"💾 Saved to: {self.index_dir}")
        
        return True
    
    def load_index(self):
        """インデックスをロード"""
        if not self.index_file.exists():
            print("❌ Index not found. Run build_index() first.")
            return False
        
        self.index = faiss.read_index(str(self.index_file))
        self.metadata = json.loads(self.metadata_file.read_text())
        
        print(f"✅ Index loaded: {self.index.ntotal} vectors")
        return True
    
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """類似検索"""
        if self.index is None:
            if not self.load_index():
                return []
        
        # クエリをエンコード
        query_vector = self.model.encode([query])
        
        # 検索
        distances, indices = self.index.search(query_vector.astype('float32'), top_k)  # type: ignore[union-attr]
        
        results = []
        for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
            if idx < len(self.metadata):
                result = self.metadata[idx].copy()
                result['distance'] = float(dist)
                result['similarity'] = 1 / (1 + dist)  # 距離を類似度に変換
                result['rank'] = i + 1
                results.append(result)
        
        return results


def main():
    """テスト実行"""
    search = ManaSpecVectorSearch()
    
    # 登録プロジェクトからインデックス構築
    projects = [
        "/root/openspec_test",
        "/root/manaos_v3",
        "/root/trinity_automation"
    ]
    
    # 存在するプロジェクトのみ
    existing_projects = [p for p in projects if (Path(p) / "openspec").exists()]
    
    print(f"📂 Projects to index: {len(existing_projects)}\n")
    
    # インデックス構築
    if search.build_index(existing_projects):
        print("\n🔍 Testing search...\n")
        
        # テスト検索
        queries = [
            "greeting system",
            "Remi optimization",
            "performance improvement"
        ]
        
        for query in queries:
            print(f"\n🔎 Query: '{query}'")
            print("─" * 60)
            
            results = search.search(query, top_k=3)
            
            for result in results:
                print(f"  {result['rank']}. [{result['type']}] {result.get('capability') or result.get('change_id')}")
                print(f"     Similarity: {result['similarity']:.3f}")
                print(f"     Project: {result['project']}")


if __name__ == '__main__':
    main()

