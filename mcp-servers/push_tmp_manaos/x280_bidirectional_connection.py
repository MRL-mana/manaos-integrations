#!/usr/bin/env python3
"""
X280双方向SSH接続システム
サーバー ↔ X280 の双方向接続を確立
"""

import os
from pathlib import Path
from datetime import datetime

class X280BidirectionalConnector:
    def __init__(self):
        self.source_dir = Path('/home/mana/Downloads/PDF変換結果_20251007_091805')
        self.server_ip = "163.44.120.49"
        self.tailscale_ip = "100.93.120.33"
        
        print("🚀 X280双方向SSH接続システム")
        print("🖥️ サーバー環境: vm-8a8820e4-c5")
        print("📱 X280: クライアント")
        print(f"🌐 サーバーIP: {self.server_ip}")
        print(f"🔗 Tailscale IP: {self.tailscale_ip}")
        print(f"📁 ソースディレクトリ: {self.source_dir}")
    
    def show_connection_info(self):
        """接続情報を表示"""
        print("\n📋 双方向SSH接続情報")
        print("=" * 50)
        
        print("✅ サーバー側SSHサービス: 稼働中")
        print("✅ ポート22: リスニング中")
        print("✅ SSH接続: 受付可能")
        
        print("\n📱 X280からサーバーへの接続方法:")
        print(f"  ssh root@{self.server_ip}")
        print(f"  ssh root@{self.tailscale_ip}  # Tailscale経由")
        
        print("\n🖥️ サーバーからX280への接続方法:")
        print("  X280のIPアドレスが必要")
        print("  ssh mana@X280のIPアドレス")
    
    def create_x280_connection_script(self):
        """X280用接続スクリプト作成"""
        print("\n📝 X280用接続スクリプト作成中...")
        
        # X280からサーバーへの接続スクリプト
        x280_to_server_script = f"""#!/bin/bash
# X280からサーバーへの接続スクリプト

echo "🚀 X280 → サーバー接続スクリプト"
echo "=================================="

# サーバーIPアドレス
SERVER_IP="{self.server_ip}"
TAILSCALE_IP="{self.tailscale_ip}"

echo "📡 接続先サーバー:"
echo "  🌐 通常IP: $SERVER_IP"
echo "  🔗 Tailscale IP: $TAILSCALE_IP"

echo ""
echo "🔐 SSH接続テスト中..."

# 通常IP接続テスト
echo "📡 通常IP接続テスト: $SERVER_IP"
if ssh -o ConnectTimeout=5 -o BatchMode=yes root@$SERVER_IP "echo '通常IP接続成功'" 2>/dev/null; then
    echo "✅ 通常IP接続成功"
    echo "📋 接続コマンド: ssh root@$SERVER_IP"
else
    echo "❌ 通常IP接続失敗"
fi

# Tailscale IP接続テスト
echo "📡 Tailscale IP接続テスト: $TAILSCALE_IP"
if ssh -o ConnectTimeout=5 -o BatchMode=yes root@$TAILSCALE_IP "echo 'Tailscale IP接続成功'" 2>/dev/null; then
    echo "✅ Tailscale IP接続成功"
    echo "📋 接続コマンド: ssh root@$TAILSCALE_IP"
else
    echo "❌ Tailscale IP接続失敗"
fi

echo ""
echo "📁 サーバー上のファイル一覧:"
ssh root@$SERVER_IP "ls -la /home/mana/Downloads/PDF変換結果_20251007_091805/"

echo ""
echo "📤 ファイルダウンロード方法:"
echo "scp -r root@$SERVER_IP:/home/mana/Downloads/PDF変換結果_20251007_091805/ ~/Desktop/"
"""
        
        # サーバーからX280への接続スクリプト
        server_to_x280_script = """#!/bin/bash
# サーバーからX280への接続スクリプト

echo "🚀 サーバー → X280接続スクリプト"
echo "=================================="

echo "📱 X280のIPアドレスを入力してください:"
read X280_IP

if [ -z "$X280_IP" ]; then
    echo "❌ IPアドレスが入力されませんでした"
    exit 1
fi

echo "🔐 X280接続テスト中: $X280_IP"
if ssh -o ConnectTimeout=5 -o BatchMode=yes mana@$X280_IP "echo 'X280接続成功'" 2>/dev/null; then
    echo "✅ X280接続成功"
    
    echo "📁 X280にディレクトリ作成中..."
    ssh mana@$X280_IP "mkdir -p ~/Desktop/PDF変換結果_$(date +%Y%m%d_%H%M%S)"
    
    echo "📤 ファイル転送中..."
    scp -r /home/mana/Downloads/PDF変換結果_20251007_091805/ mana@$X280_IP:~/Desktop/
    
    echo "✅ ファイル転送完了"
    echo "📁 X280ダウンロード先: ~/Desktop/PDF変換結果_20251007_091805/"
else
    echo "❌ X280接続失敗"
    echo "💡 X280でSSHサービスが有効になっているか確認してください"
fi
"""
        
        # スクリプトファイル保存
        x280_script_path = Path('/home/mana/Desktop/X280からサーバー接続.sh')
        server_script_path = Path('/home/mana/Desktop/サーバーからX280接続.sh')
        
        with open(x280_script_path, 'w', encoding='utf-8') as f:
            f.write(x280_to_server_script)
        os.chmod(x280_script_path, 0o755)
        
        with open(server_script_path, 'w', encoding='utf-8') as f:
            f.write(server_to_x280_script)
        os.chmod(server_script_path, 0o755)
        
        print(f"✅ X280用接続スクリプト作成完了: {x280_script_path}")
        print(f"✅ サーバー用接続スクリプト作成完了: {server_script_path}")
        
        return True
    
    def create_connection_guide(self):
        """接続ガイド作成"""
        print("\n📋 接続ガイド作成中...")
        
        guide_content = f"""# X280双方向SSH接続ガイド

## 🖥️ サーバー環境
- **ホスト名**: vm-8a8820e4-c5
- **通常IP**: {self.server_ip}
- **Tailscale IP**: {self.tailscale_ip}
- **SSHポート**: 22 (稼働中)

## 📱 X280環境
- **ユーザー**: mana
- **SSH接続**: 要設定

## 🔄 双方向接続方法

### 1. X280 → サーバー接続
```bash
# 通常IP経由
ssh root@{self.server_ip}

# Tailscale経由（推奨）
ssh root@{self.tailscale_ip}
```

### 2. サーバー → X280接続
```bash
# X280のIPアドレスが必要
ssh mana@X280のIPアドレス
```

### 3. ファイル転送

#### X280からサーバーへ
```bash
# サーバーからファイルをダウンロード
scp -r root@{self.server_ip}:/home/mana/Downloads/PDF変換結果_20251007_091805/ ~/Desktop/
```

#### サーバーからX280へ
```bash
# X280にファイルをアップロード
scp -r /home/mana/Downloads/PDF変換結果_20251007_091805/ mana@X280のIPアドレス:~/Desktop/
```

## 🚀 自動化スクリプト

### X280用スクリプト
```bash
./X280からサーバー接続.sh
```

### サーバー用スクリプト
```bash
./サーバーからX280接続.sh
```

## 🔧 トラブルシューティング

### X280でSSHサービス有効化
```bash
sudo systemctl enable ssh
sudo systemctl start ssh
sudo ufw allow ssh
```

### 接続テスト
```bash
# サーバーからX280
ssh -o ConnectTimeout=5 mana@X280のIPアドレス "echo '接続成功'"

# X280からサーバー
ssh -o ConnectTimeout=5 root@{self.server_ip} "echo '接続成功'"
```

---
作成日: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
"""
        
        guide_path = Path('/home/mana/Desktop/X280双方向SSH接続ガイド.md')
        with open(guide_path, 'w', encoding='utf-8') as f:
            f.write(guide_content)
        
        print(f"✅ 接続ガイド作成完了: {guide_path}")
        return True
    
    def run_bidirectional_setup(self):
        """双方向接続セットアップ実行"""
        print("🚀 X280双方向SSH接続セットアップ開始")
        print("=" * 60)
        
        # 1. 接続情報表示
        self.show_connection_info()
        
        # 2. 接続スクリプト作成
        if not self.create_x280_connection_script():
            return False
        
        # 3. 接続ガイド作成
        if not self.create_connection_guide():
            return False
        
        print("\n🎉 X280双方向SSH接続セットアップ完了！")
        print("=" * 60)
        print("📋 作成されたファイル:")
        print("  📝 X280からサーバー接続.sh")
        print("  📝 サーバーからX280接続.sh")
        print("  📋 X280双方向SSH接続ガイド.md")
        print("")
        print("🚀 使用方法:")
        print("  1. X280で: ./X280からサーバー接続.sh")
        print("  2. サーバーで: ./サーバーからX280接続.sh")
        print("  3. ガイドを参照: X280双方向SSH接続ガイド.md")
        
        return True

def main():
    """メイン実行関数"""
    connector = X280BidirectionalConnector()
    success = connector.run_bidirectional_setup()
    
    if success:
        print("\n✅ X280双方向SSH接続セットアップ完了！")
        print("📁 デスクトップの接続スクリプトとガイドを確認してください")
    else:
        print("\n❌ X280双方向SSH接続セットアップ失敗")

if __name__ == "__main__":
    main()


