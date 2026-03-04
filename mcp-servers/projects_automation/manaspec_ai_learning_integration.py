#!/usr/bin/env python3
"""
ManaSpec × AI Learning System Integration

OPENSPECのアーカイブデータをAI Learning Systemに自動保存し、
過去の実装パターンから学習する
"""

import json
import sqlite3
import asyncio
from typing import Dict, List, Optional

class ManaSpecAILearningIntegration:
    """AI Learning System統合"""
    
    def __init__(self, db_path: str = "/root/ai_learning.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize AI Learning database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS openspec_archives (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                change_id TEXT NOT NULL,
                archive_date TEXT NOT NULL,
                feature_description TEXT,
                proposal TEXT,
                tasks TEXT,
                specs JSON,
                implementation_notes TEXT,
                success_metrics JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(change_id, archive_date)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS spec_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT NOT NULL,
                pattern_name TEXT NOT NULL,
                pattern_content TEXT,
                usage_count INTEGER DEFAULT 1,
                success_rate REAL DEFAULT 1.0,
                tags JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS implementation_insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                change_id TEXT NOT NULL,
                insight_type TEXT NOT NULL,
                insight_content TEXT,
                confidence REAL DEFAULT 0.5,
                metadata JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
        
        print(f"✅ AI Learning Database initialized: {self.db_path}")
    
    async def save_archive(self, archive_data: Dict) -> int:
        """
        Save archived change to AI Learning System
        
        Args:
            archive_data: Archive data from openspec
            
        Returns:
            ID of saved archive
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO openspec_archives
                (change_id, archive_date, feature_description, proposal, tasks, specs, implementation_notes, success_metrics)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                archive_data.get("change_id"),
                archive_data.get("archive_date"),
                archive_data.get("feature", ""),
                archive_data.get("proposal", ""),
                archive_data.get("tasks", ""),
                json.dumps(archive_data.get("specs", [])),
                archive_data.get("implementation_notes", ""),
                json.dumps(archive_data.get("success_metrics", {}))
            ))
            
            archive_id = cursor.lastrowid
            conn.commit()
            
            print(f"✅ Archive saved to AI Learning System: ID={archive_id}")
            
            # Extract and save patterns
            await self._extract_patterns(archive_data, cursor)
            
            conn.commit()
            return archive_id
            
        except Exception as e:
            print(f"❌ Failed to save archive: {e}")
            conn.rollback()
            return -1
        finally:
            conn.close()
    
    async def _extract_patterns(self, archive_data: Dict, cursor: sqlite3.Cursor):
        """Extract reusable patterns from archive"""
        
        # Extract requirement patterns
        for spec in archive_data.get("specs", []):
            content = spec.get("content", "")
            capability = spec.get("capability", "")
            
            # Simple pattern extraction (can be enhanced with NLP)
            if "SHALL" in content:
                # Extract SHALL statements as patterns
                import re
                shall_patterns = re.findall(r'(?:The system|User|System) SHALL ([^.]+)', content)
                
                for idx, pattern in enumerate(shall_patterns):
                    # Check if pattern exists
                    cursor.execute("""
                        SELECT id, usage_count FROM spec_patterns
                        WHERE pattern_type = ? AND pattern_name = ?
                    """, ("requirement", f"{capability}_requirement_{idx}"))
                    
                    existing = cursor.fetchone()
                    
                    if existing:
                        # Update usage count
                        cursor.execute("""
                            UPDATE spec_patterns
                            SET usage_count = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        """, (existing[1] + 1, existing[0]))
                    else:
                        # Insert new pattern
                        cursor.execute("""
                            INSERT INTO spec_patterns (pattern_type, pattern_name, pattern_content, tags)
                            VALUES (?, ?, ?, ?)
                        """, (
                            "requirement",
                            f"{capability}_requirement_{idx}",
                            pattern,
                            json.dumps([capability, "SHALL"])
                        ))
        
        print(f"✅ Patterns extracted from {archive_data.get('change_id')}")
    
    async def get_similar_archives(self, feature_description: str, limit: int = 5) -> List[Dict]:
        """
        Find similar archived changes based on feature description
        
        使用例: 新しいProposal作成時に過去の類似案件を参照
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Simple keyword-based similarity (can be enhanced with vector search)
        keywords = feature_description.lower().split()
        
        results = []
        cursor.execute("""
            SELECT id, change_id, archive_date, feature_description, proposal, specs, success_metrics
            FROM openspec_archives
            ORDER BY created_at DESC
            LIMIT 100
        """)
        
        for row in cursor.fetchall():
            archive_id, change_id, archive_date, feature, proposal, specs, metrics = row
            
            # Calculate simple similarity score
            similarity = sum(1 for keyword in keywords if keyword in (feature + proposal).lower())
            
            if similarity > 0:
                results.append({
                    "id": archive_id,
                    "change_id": change_id,
                    "archive_date": archive_date,
                    "feature_description": feature,
                    "proposal": proposal,
                    "specs": json.loads(specs) if specs else [],
                    "success_metrics": json.loads(metrics) if metrics else {},
                    "similarity_score": similarity
                })
        
        # Sort by similarity and return top N
        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        conn.close()
        
        return results[:limit]
    
    async def get_pattern_suggestions(self, capability: str, pattern_type: str = "requirement") -> List[Dict]:
        """
        Get pattern suggestions for a capability
        
        使用例: 新しいSpec Delta作成時に過去のパターンを提案
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT pattern_name, pattern_content, usage_count, success_rate, tags
            FROM spec_patterns
            WHERE pattern_type = ? AND (tags LIKE ? OR pattern_name LIKE ?)
            ORDER BY usage_count DESC, success_rate DESC
            LIMIT 10
        """, (pattern_type, f"%{capability}%", f"%{capability}%"))
        
        patterns = []
        for row in cursor.fetchall():
            pattern_name, content, usage_count, success_rate, tags = row
            patterns.append({
                "name": pattern_name,
                "content": content,
                "usage_count": usage_count,
                "success_rate": success_rate,
                "tags": json.loads(tags) if tags else []
            })
        
        conn.close()
        return patterns
    
    async def save_insight(self, change_id: str, insight_type: str, insight_content: str, 
                          confidence: float = 0.5, metadata: Dict = None):
        """
        Save implementation insight
        
        使用例: Mina が実装の洞察を記録
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO implementation_insights (change_id, insight_type, insight_content, confidence, metadata)
            VALUES (?, ?, ?, ?, ?)
        """, (
            change_id,
            insight_type,
            insight_content,
            confidence,
            json.dumps(metadata or {})
        ))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Insight saved: {insight_type} for {change_id}")
    
    async def get_insights(self, change_id: Optional[str] = None, insight_type: Optional[str] = None) -> List[Dict]:
        """Get implementation insights"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT change_id, insight_type, insight_content, confidence, metadata, created_at FROM implementation_insights WHERE 1=1"
        params = []
        
        if change_id:
            query += " AND change_id = ?"
            params.append(change_id)
        
        if insight_type:
            query += " AND insight_type = ?"
            params.append(insight_type)
        
        query += " ORDER BY created_at DESC LIMIT 50"
        
        cursor.execute(query, params)
        
        insights = []
        for row in cursor.fetchall():
            chg_id, i_type, content, confidence, metadata, created = row
            insights.append({
                "change_id": chg_id,
                "insight_type": i_type,
                "content": content,
                "confidence": confidence,
                "metadata": json.loads(metadata) if metadata else {},
                "created_at": created
            })
        
        conn.close()
        return insights
    
    async def get_statistics(self) -> Dict:
        """Get AI Learning System statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Count archives
        cursor.execute("SELECT COUNT(*) FROM openspec_archives")
        total_archives = cursor.fetchone()[0]
        
        # Count patterns
        cursor.execute("SELECT COUNT(*) FROM spec_patterns")
        total_patterns = cursor.fetchone()[0]
        
        # Count insights
        cursor.execute("SELECT COUNT(*) FROM implementation_insights")
        total_insights = cursor.fetchone()[0]
        
        # Get recent archives
        cursor.execute("""
            SELECT change_id, archive_date
            FROM openspec_archives
            ORDER BY created_at DESC
            LIMIT 5
        """)
        recent_archives = [{"change_id": row[0], "archive_date": row[1]} for row in cursor.fetchall()]
        
        # Top patterns
        cursor.execute("""
            SELECT pattern_type, pattern_name, usage_count
            FROM spec_patterns
            ORDER BY usage_count DESC
            LIMIT 5
        """)
        top_patterns = [{"type": row[0], "name": row[1], "usage": row[2]} for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            "total_archives": total_archives,
            "total_patterns": total_patterns,
            "total_insights": total_insights,
            "recent_archives": recent_archives,
            "top_patterns": top_patterns
        }


async def main():
    """Test AI Learning Integration"""
    integration = ManaSpecAILearningIntegration()
    
    # Test data
    test_archive = {
        "change_id": "add-hello-world",
        "archive_date": "2025-10-15",
        "feature": "Hello World greeting system",
        "proposal": "Add greeting capability with multi-language support",
        "tasks": "Implement greeting service, add tests",
        "specs": [
            {
                "capability": "greeting",
                "content": "The system SHALL provide greeting messages in multiple languages."
            }
        ],
        "success_metrics": {
            "implementation_time_hours": 2,
            "test_coverage": 95
        }
    }
    
    # Save archive
    archive_id = await integration.save_archive(test_archive)
    print(f"Saved archive ID: {archive_id}")
    
    # Get statistics
    stats = await integration.get_statistics()
    print("\nAI Learning Statistics:")
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    
    # Find similar archives
    similar = await integration.get_similar_archives("greeting system")
    print(f"\nSimilar archives found: {len(similar)}")
    for archive in similar:
        print(f"  - {archive['change_id']} (score: {archive['similarity_score']})")
    
    # Get pattern suggestions
    patterns = await integration.get_pattern_suggestions("greeting")
    print(f"\nPattern suggestions for 'greeting': {len(patterns)}")
    for pattern in patterns:
        print(f"  - {pattern['name']}: {pattern['content'][:50]}...")


if __name__ == '__main__':
    asyncio.run(main())

