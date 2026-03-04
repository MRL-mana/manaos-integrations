#!/usr/bin/env python3
"""
🔄 PDF→Excel n8n Workflow Auto Import
既存のManaOSシステムにPDF→Excelフローを統合
"""

import requests

N8N_URL = "http://localhost:5678"

def create_pdf_workflow():
    """PDF→Excelワークフロー定義"""
    return {
        "name": "ManaOS - PDF to Excel Converter",
        "nodes": [
            {
                "parameters": {
                    "path": "/root/ocr_test/input",
                    "options": {
                        "watchFolder": True
                    }
                },
                "id": "file-watcher",
                "name": "PDF File Watcher",
                "type": "n8n-nodes-base.localFileTrigger",
                "typeVersion": 1,
                "position": [240, 300]
            },
            {
                "parameters": {
                    "conditions": {
                        "options": {
                            "caseSensitive": True,
                            "leftValue": "",
                            "typeValidation": "strict"
                        },
                        "conditions": [
                            {
                                "id": "pdf-check",
                                "leftValue": "={{ $json.name }}",
                                "rightValue": ".pdf",
                                "operator": {
                                    "type": "string",
                                    "operation": "endsWith"
                                }
                            }
                        ],
                        "combinator": "and"
                    },
                    "options": {}
                },
                "id": "pdf-filter",
                "name": "PDF Filter",
                "type": "n8n-nodes-base.if",
                "typeVersion": 2,
                "position": [460, 300]
            },
            {
                "parameters": {
                    "command": "cd /root/ocr_test && python3 autopipeline_basic.py /root/ocr_test/input/{{ $json.name }}"
                },
                "id": "pdf-converter",
                "name": "PDF Converter",
                "type": "n8n-nodes-base.executeCommand",
                "typeVersion": 1,
                "position": [680, 200]
            },
            {
                "parameters": {
                    "command": "mv /root/ocr_test/input/{{ $json.name }} /root/ocr_test/processed/{{ $json.name }}"
                },
                "id": "move-processed",
                "name": "Move to Processed",
                "type": "n8n-nodes-base.executeCommand",
                "typeVersion": 1,
                "position": [900, 200]
            },
            {
                "parameters": {
                    "command": "mv /root/ocr_test/out.xlsx /root/ocr_test/output/{{ $json.name.replace('.pdf', '.xlsx') }}"
                },
                "id": "move-output",
                "name": "Move Excel Output",
                "type": "n8n-nodes-base.executeCommand",
                "typeVersion": 1,
                "position": [1120, 200]
            },
            {
                "parameters": {
                    "url": "http://localhost:5053/api/send",
                    "method": "POST",
                    "bodyParameters": {
                        "parameters": [
                            {"name": "message", "value": "🟢 PDF変換完了！ファイル: {{ $json.name }}"},
                            {"name": "channels", "value": ["line", "manaos"]}
                        ]
                    }
                },
                "id": "success-notification",
                "name": "Success Notification",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 1,
                "position": [1340, 200]
            }
        ],
        "connections": {
            "PDF File Watcher": {
                "main": [
                    [
                        {
                            "node": "PDF Filter",
                            "type": "main",
                            "index": 0
                        }
                    ]
                ]
            },
            "PDF Filter": {
                "main": [
                    [
                        {
                            "node": "PDF Converter",
                            "type": "main",
                            "index": 0
                        }
                    ]
                ]
            },
            "PDF Converter": {
                "main": [
                    [
                        {
                            "node": "Move to Processed",
                            "type": "main",
                            "index": 0
                        }
                    ]
                ]
            },
            "Move to Processed": {
                "main": [
                    [
                        {
                            "node": "Move Excel Output",
                            "type": "main",
                            "index": 0
                        }
                    ]
                ]
            },
            "Move Excel Output": {
                "main": [
                    [
                        {
                            "node": "Success Notification",
                            "type": "main",
                            "index": 0
                        }
                    ]
                ]
            }
        },
        "active": True,
        "settings": {
            "executionOrder": "v1"
        }
    }

def import_workflow():
    """ワークフローインポート"""
    print("📥 PDF→Excelワークフローインポート中...")
    
    try:
        workflow_data = create_pdf_workflow()
        
        # n8n APIでワークフロー作成
        response = requests.post(
            f"{N8N_URL}/api/v1/workflows",
            json=workflow_data,
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            print("✅ PDF→Excelワークフローインポート成功")
            return True
        else:
            print(f"⚠️ インポート失敗 (HTTP {response.status_code})")
            print("  n8n UIから手動でインポートしてください")
            return False
            
    except Exception as e:
        print(f"❌ エラー: {e}")
        return False

def main():
    print("🔄 PDF→Excel n8n Workflow Auto Import")
    print("=====================================")
    print("")
    
    # n8n接続確認
    try:
        response = requests.get(f"{N8N_URL}/healthz", timeout=5)
        print("✅ n8n接続成功")
    except requests.RequestException:
        print("❌ n8n接続失敗")
        print("  n8nが起動していることを確認してください")
        return
    
    print("")
    
    # ワークフローインポート
    if import_workflow():
        print("")
        print("✅ PDF→Excelワークフロー統合完了！")
        print("")
        print("🎯 次のステップ:")
        print("  1. n8nにアクセス: http://localhost:5678")
        print("  2. Workflows でPDF→Excelフローを確認")
        print("  3. フローをアクティブ化")
        print("  4. テスト: PDFファイルを /root/ocr_test/input/ に配置")
        print("")
        print("📁 ディレクトリ構造:")
        print("  /root/ocr_test/input/     - 監視ディレクトリ")
        print("  /root/ocr_test/processed/ - 処理済みPDF")
        print("  /root/ocr_test/output/    - 生成Excel")
        print("")
    else:
        print("")
        print("⚠️ 自動インポート失敗")
        print("  手動でn8n管理画面からインポートしてください")
        print("")

if __name__ == '__main__':
    main()



