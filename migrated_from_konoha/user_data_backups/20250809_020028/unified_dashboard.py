#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk
import subprocess
import threading
import json
import requests
import time
from datetime import datetime

class UnifiedDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("統合システムダッシュボード")
        self.root.geometry("1200x800")
        
        # メインフレーム
        main_frame = ttk.Frame(root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # タイトル
        title_label = ttk.Label(main_frame, text="🚀 統合システムダッシュボード", font=("Arial", 16, "bold"))
        title_label.pack(pady=10)
        
        # ステータスフレーム
        status_frame = ttk.LabelFrame(main_frame, text="システム状況", padding=10)
        status_frame.pack(fill=tk.X, pady=5)
        
        # ローカルMCPサーバー状況
        self.local_mcp_var = tk.StringVar(value="確認中...")
        ttk.Label(status_frame, text="ローカルMCPサーバー:").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(status_frame, textvariable=self.local_mcp_var).grid(row=0, column=1, sticky=tk.W)
        
        # X280接続状況
        self.x280_conn_var = tk.StringVar(value="確認中...")
        ttk.Label(status_frame, text="X280接続状況:").grid(row=1, column=0, sticky=tk.W)
        ttk.Label(status_frame, textvariable=self.x280_conn_var).grid(row=1, column=1, sticky=tk.W)
        
        # X280 MCPサーバー状況
        self.x280_mcp_var = tk.StringVar(value="確認中...")
        ttk.Label(status_frame, text="X280 MCPサーバー:").grid(row=2, column=0, sticky=tk.W)
        ttk.Label(status_frame, textvariable=self.x280_mcp_var).grid(row=2, column=1, sticky=tk.W)
        
        # 統合システム状況
        self.unified_var = tk.StringVar(value="確認中...")
        ttk.Label(status_frame, text="統合システム状況:").grid(row=3, column=0, sticky=tk.W)
        ttk.Label(status_frame, textvariable=self.unified_var).grid(row=3, column=1, sticky=tk.W)
        
        # ボタンフレーム
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        # ボタン
        ttk.Button(button_frame, text="🔄 状況更新", command=self.update_status).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="🧪 統合テスト", command=self.run_integration_test).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="📊 詳細監視", command=self.show_detailed_monitor).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="⚙️ 設定", command=self.show_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="🚀 AI ヘルパー", command=self.open_ai_helper).pack(side=tk.LEFT, padx=5)
        
        # ログフレーム
        log_frame = ttk.LabelFrame(main_frame, text="システムログ", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # ログテキスト
        self.log_text = tk.Text(log_frame, height=15, width=80)
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 初期状況更新
        self.update_status()
        
        # 自動更新タイマー
        self.auto_update()
    
    def update_status(self):
        def update():
            # ローカルMCPサーバー確認
            try:
                response = requests.get("http://localhost:8421/health", timeout=5)
                if response.status_code == 200:
                    self.local_mcp_var.set("✅ 正常動作")
                else:
                    self.local_mcp_var.set("❌ 応答なし")
            except:
                self.local_mcp_var.set("❌ 接続失敗")
            
            # X280接続確認
            try:
                result = subprocess.run(["ping", "-c", "1", "60.108.146.82"], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    self.x280_conn_var.set("✅ オンライン")
                else:
                    self.x280_conn_var.set("❌ オフライン")
            except:
                self.x280_conn_var.set("❌ 確認失敗")
            
            # X280 MCPサーバー確認
            try:
                response = requests.get("http://60.108.146.82:8422/health", timeout=5)
                if response.status_code == 200:
                    self.x280_mcp_var.set("✅ 正常動作")
                else:
                    self.x280_mcp_var.set("❌ 応答なし")
            except:
                self.x280_mcp_var.set("❌ 接続失敗")
            
            # 統合システム状況
            if (self.local_mcp_var.get() == "✅ 正常動作" and 
                self.x280_conn_var.get() == "✅ オンライン"):
                self.unified_var.set("✅ 完全統合システム稼働中")
            else:
                self.unified_var.set("⚠️ 部分的な統合システム")
        
        threading.Thread(target=update, daemon=True).start()
    
    def run_integration_test(self):
        def test():
            self.log_message("🧪 統合テスト実行中...")
            try:
                result = subprocess.run(["./x280_integration_test.sh"], 
                                      capture_output=True, text=True, timeout=30)
                self.log_message(result.stdout)
                if result.stderr:
                    self.log_message(f"エラー: {result.stderr}")
            except Exception as e:
                self.log_message(f"テスト実行エラー: {e}")
        
        threading.Thread(target=test, daemon=True).start()
    
    def show_detailed_monitor(self):
        def monitor():
            self.log_message("📊 詳細監視実行中...")
            try:
                result = subprocess.run(["./x280_monitor.sh"], 
                                      capture_output=True, text=True, timeout=30)
                self.log_message(result.stdout)
            except Exception as e:
                self.log_message(f"監視実行エラー: {e}")
        
        threading.Thread(target=monitor, daemon=True).start()
    
    def show_settings(self):
        settings_window = tk.Toplevel(self.root)
        settings_window.title("設定")
        settings_window.geometry("600x400")
        
        # 設定内容
        ttk.Label(settings_window, text="統合システム設定", font=("Arial", 14, "bold")).pack(pady=10)
        
        # X280設定
        x280_frame = ttk.LabelFrame(settings_window, text="X280設定", padding=10)
        x280_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(x280_frame, text="IPアドレス: 60.108.146.82").pack(anchor=tk.W)
        ttk.Label(x280_frame, text="MCPポート: 8422").pack(anchor=tk.W)
        ttk.Label(x280_frame, text="SSHポート: 22").pack(anchor=tk.W)
        
        # ローカル設定
        local_frame = ttk.LabelFrame(settings_window, text="ローカル設定", padding=10)
        local_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(local_frame, text="MCPポート: 8421").pack(anchor=tk.W)
        ttk.Label(local_frame, text="HTTPポート: 5174").pack(anchor=tk.W)
    
    def open_ai_helper(self):
        def helper():
            self.log_message("🤖 AI ヘルパー起動中...")
            try:
                subprocess.run(["./ai_helper.sh"], timeout=30)
            except Exception as e:
                self.log_message(f"AI ヘルパー起動エラー: {e}")
        
        threading.Thread(target=helper, daemon=True).start()
    
    def log_message(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
    
    def auto_update(self):
        self.update_status()
        self.root.after(30000, self.auto_update)  # 30秒ごとに更新

if __name__ == "__main__":
    root = tk.Tk()
    app = UnifiedDashboard(root)
    root.mainloop()
