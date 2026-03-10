#!/usr/bin/env python3
"""
ManaSpec Dashboard API
Trinity Unified Dashboard用のManaSpec統合APIサーバー
"""

import os
import json
import subprocess
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Configuration
OPENSPEC_PROJECT_PATH = os.getenv("OPENSPEC_PROJECT_PATH", "/root/openspec_test")
AI_LEARNING_DB = os.getenv("AI_LEARNING_DB", "/root/ai_learning.db")

def run_openspec_command(cmd: str, cwd: str = None) -> tuple:  # type: ignore
    """Run openspec command and return result"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=cwd or OPENSPEC_PROJECT_PATH
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)

@app.route('/api/manaspec/status', methods=['GET'])
def get_status():
    """Get ManaSpec overall status"""
    # OpenSpec changes
    returncode, stdout, stderr = run_openspec_command("openspec list --json")
    changes = []
    if returncode == 0 and stdout.strip():
        try:
            changes = json.loads(stdout)
        except IOError:
            pass
    
    # OpenSpec specs
    returncode, stdout, stderr = run_openspec_command("openspec list --specs --json")
    specs = []
    if returncode == 0 and stdout.strip():
        try:
            specs = json.loads(stdout)
        except IOError:
            pass
    
    # AI Learning stats
    ai_stats = get_ai_learning_stats()
    
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "openspec": {
            "active_changes": len(changes),
            "total_specs": len(specs)
        },
        "ai_learning": ai_stats,
        "project_path": OPENSPEC_PROJECT_PATH
    })

@app.route('/api/manaspec/changes', methods=['GET'])
def get_changes():
    """Get all OpenSpec changes"""
    returncode, stdout, stderr = run_openspec_command("openspec list")
    
    if returncode != 0:
        return jsonify({"error": stderr}), 500
    
    # Parse output
    changes = []
    for line in stdout.strip().split('\n'):
        if line.strip() and not line.startswith('Changes:') and not line.startswith('No active'):
            parts = line.strip().split()
            if len(parts) >= 2:
                change_id = parts[0]
                tasks_info = ' '.join(parts[1:])
                
                changes.append({
                    "id": change_id,
                    "tasks": tasks_info,
                    "url": f"/api/manaspec/changes/{change_id}"
                })
    
    return jsonify({
        "changes": changes,
        "total": len(changes)
    })

@app.route('/api/manaspec/changes/<change_id>', methods=['GET'])
def get_change_detail(change_id: str):
    """Get change details"""
    returncode, stdout, stderr = run_openspec_command(f"openspec show {change_id}")
    
    if returncode != 0:
        return jsonify({"error": stderr}), 404
    
    # Load files directly for more details
    change_path = Path(OPENSPEC_PROJECT_PATH) / "openspec" / "changes" / change_id
    
    details = {
        "id": change_id,
        "proposal": "",
        "tasks": "",
        "specs": []
    }
    
    if change_path.exists():
        proposal_file = change_path / "proposal.md"
        if proposal_file.exists():
            details["proposal"] = proposal_file.read_text()
        
        tasks_file = change_path / "tasks.md"
        if tasks_file.exists():
            details["tasks"] = tasks_file.read_text()
        
        # Get spec deltas
        specs_dir = change_path / "specs"
        if specs_dir.exists():
            for capability_dir in specs_dir.iterdir():
                if capability_dir.is_dir():
                    spec_file = capability_dir / "spec.md"
                    if spec_file.exists():
                        details["specs"].append({
                            "capability": capability_dir.name,
                            "content": spec_file.read_text()
                        })
    
    return jsonify(details)

@app.route('/api/manaspec/specs', methods=['GET'])
def get_specs():
    """Get all OpenSpec specifications"""
    returncode, stdout, stderr = run_openspec_command("openspec list --specs")
    
    if returncode != 0:
        return jsonify({"error": stderr}), 500
    
    # Parse output
    specs = []
    for line in stdout.strip().split('\n'):
        if line.strip() and not line.startswith('Specs:') and not line.startswith('No specs'):
            parts = line.strip().split()
            if len(parts) >= 2:
                spec_id = parts[0]
                info = ' '.join(parts[1:])
                
                specs.append({
                    "id": spec_id,
                    "info": info,
                    "url": f"/api/manaspec/specs/{spec_id}"
                })
    
    return jsonify({
        "specs": specs,
        "total": len(specs)
    })

@app.route('/api/manaspec/specs/<spec_id>', methods=['GET'])
def get_spec_detail(spec_id: str):
    """Get spec details"""
    # Load spec file directly
    spec_path = Path(OPENSPEC_PROJECT_PATH) / "openspec" / "specs" / spec_id / "spec.md"
    
    if not spec_path.exists():
        return jsonify({"error": "Spec not found"}), 404
    
    return jsonify({
        "id": spec_id,
        "content": spec_path.read_text()
    })

@app.route('/api/manaspec/archives', methods=['GET'])
def get_archives():
    """Get archived changes"""
    archive_dir = Path(OPENSPEC_PROJECT_PATH) / "openspec" / "changes" / "archive"
    
    if not archive_dir.exists():
        return jsonify({"archives": [], "total": 0})
    
    archives = []
    for archive_path in sorted(archive_dir.iterdir(), reverse=True):
        if archive_path.is_dir():
            # Extract date and change_id from directory name (YYYY-MM-DD-change-id)
            dir_name = archive_path.name
            parts = dir_name.split('-', 3)
            
            if len(parts) >= 4:
                archive_date = f"{parts[0]}-{parts[1]}-{parts[2]}"
                change_id = parts[3]
            else:
                archive_date = "unknown"
                change_id = dir_name
            
            proposal_file = archive_path / "proposal.md"
            proposal_preview = ""
            if proposal_file.exists():
                content = proposal_file.read_text()
                proposal_preview = content[:200] + "..." if len(content) > 200 else content
            
            archives.append({
                "id": dir_name,
                "change_id": change_id,
                "archive_date": archive_date,
                "proposal_preview": proposal_preview,
                "path": str(archive_path)
            })
    
    return jsonify({
        "archives": archives,
        "total": len(archives)
    })

@app.route('/api/manaspec/ai-learning/stats', methods=['GET'])
def get_ai_learning_stats_api():
    """Get AI Learning statistics"""
    stats = get_ai_learning_stats()
    return jsonify(stats)

@app.route('/stats', methods=['GET'])
def stats_short():
    """Short stats endpoint for compatibility"""
    return get_status()

def get_ai_learning_stats() -> Dict:
    """Get statistics from AI Learning database"""
    if not os.path.exists(AI_LEARNING_DB):
        return {
            "total_archives": 0,
            "total_patterns": 0,
            "total_insights": 0,
            "recent_archives": [],
            "top_patterns": []
        }
    
    try:
        conn = sqlite3.connect(AI_LEARNING_DB)
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
        
        # Recent archives
        cursor.execute("""
            SELECT change_id, archive_date, feature_description
            FROM openspec_archives
            ORDER BY created_at DESC
            LIMIT 5
        """)
        recent_archives = [
            {"change_id": row[0], "archive_date": row[1], "feature": row[2]}
            for row in cursor.fetchall()
        ]
        
        # Top patterns
        cursor.execute("""
            SELECT pattern_type, pattern_name, usage_count, success_rate
            FROM spec_patterns
            ORDER BY usage_count DESC, success_rate DESC
            LIMIT 5
        """)
        top_patterns = [
            {"type": row[0], "name": row[1], "usage": row[2], "success_rate": row[3]}
            for row in cursor.fetchall()
        ]
        
        conn.close()
        
        return {
            "total_archives": total_archives,
            "total_patterns": total_patterns,
            "total_insights": total_insights,
            "recent_archives": recent_archives,
            "top_patterns": top_patterns
        }
    except Exception as e:
        return {
            "error": str(e),
            "total_archives": 0,
            "total_patterns": 0,
            "total_insights": 0
        }

@app.route('/api/manaspec/ai-learning/similar', methods=['POST'])
def find_similar_archives():
    """Find similar archives based on feature description"""
    data = request.json
    feature = data.get('feature', '')
    
    if not feature:
        return jsonify({"error": "Feature description required"}), 400
    
    # Simple keyword-based search
    try:
        conn = sqlite3.connect(AI_LEARNING_DB)
        cursor = conn.cursor()
        
        keywords = feature.lower().split()
        
        cursor.execute("""
            SELECT change_id, archive_date, feature_description, proposal
            FROM openspec_archives
            ORDER BY created_at DESC
            LIMIT 50
        """)
        
        results = []
        for row in cursor.fetchall():
            change_id, archive_date, feature_desc, proposal = row
            
            # Calculate similarity
            text = (feature_desc or "") + " " + (proposal or "")
            similarity = sum(1 for keyword in keywords if keyword in text.lower())
            
            if similarity > 0:
                results.append({
                    "change_id": change_id,
                    "archive_date": archive_date,
                    "feature_description": feature_desc,
                    "similarity_score": similarity
                })
        
        # Sort by similarity
        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        
        conn.close()
        
        return jsonify({
            "query": feature,
            "results": results[:5]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/manaspec/validate/<change_id>', methods=['POST'])
def validate_change(change_id: str):
    """Validate a change"""
    returncode, stdout, stderr = run_openspec_command(f"openspec validate {change_id} --strict")
    
    return jsonify({
        "change_id": change_id,
        "valid": returncode == 0,
        "output": stdout,
        "error": stderr if returncode != 0 else None
    })

@app.route('/api/manaspec/archive/<change_id>', methods=['POST'])
def archive_change(change_id: str):
    """Archive a change"""
    returncode, stdout, stderr = run_openspec_command(f"openspec archive {change_id} --yes")
    
    return jsonify({
        "change_id": change_id,
        "success": returncode == 0,
        "output": stdout,
        "error": stderr if returncode != 0 else None
    })

@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({"status": "healthy", "service": "manaspec-dashboard-api"})

if __name__ == '__main__':
    print("🚀 ManaSpec Dashboard API Server starting...")
    print(f"📁 OpenSpec Project: {OPENSPEC_PROJECT_PATH}")
    print(f"🧠 AI Learning DB: {AI_LEARNING_DB}")
    print("🌐 Server: http://localhost:9300")
    
    app.run(host='0.0.0.0', port=9301, debug=os.getenv("DEBUG", "False").lower() == "true")

