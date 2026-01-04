# ピクセル7ワイヤレスADB接続ガイド

## 概要

母艦（このはサーバー）からピクセル7にワイヤレスADB接続を設定する手順です。

## 前提条件

- ピクセル7と母艦が同じTailscaleネットワークに接続されていること
- ピクセル7のTailscale IP: `100.127.121.20`（設定に応じて変更可能）

## セットアップ手順

**重要**: この手順は**母艦（Windows PC）**から実行します。

### 1. ピクセル7側の設定

#### 1.1 開発者オプションを有効化

1. 設定 > デバイス情報
2. 「ビルド番号」を7回タップ
3. 「開発者になりました」と表示されればOK

#### 1.2 USBデバッグを有効化

1. 設定 > 開発者オプション
2. 「USBデバッグ」を有効化
3. 確認ダイアログで「OK」をタップ

#### 1.3 ワイヤレスデバッグを有効化

1. 設定 > 開発者オプション
2. 「ワイヤレスデバッグ」を有効化
3. 「ワイヤレスデバッグ」をタップ
4. 「ペア設定コードを使用してデバイスをペア設定」をタップ
5. 表示されたIPアドレスとポート番号をメモ（例: `192.168.1.100:12345`）

**重要**: このポート番号は初回接続時に必要です。

### 2. 母艦（Windows PC）側の設定

#### 2.1 ADBのインストール確認

**WindowsでのADBインストール方法:**

1. **Android SDK Platform Toolsをダウンロード**
   - https://developer.android.com/studio/releases/platform-tools
   - `platform-tools-windows.zip` をダウンロード

2. **展開して環境変数に追加**
   - zipを展開（例: `C:\platform-tools\`）
   - システムの環境変数PATHに `C:\platform-tools` を追加

3. **または、Chocolateyを使用**
   ```powershell
   choco install adb
   ```

4. **インストール確認**
   ```powershell
   adb version
   ```

#### 2.2 自動セットアップスクリプトの実行

**PowerShellで実行:**

```powershell
# 作業ディレクトリに移動
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations

# セットアップスクリプトを実行
.\setup_pixel7_adb.ps1
```

スクリプトが以下を実行します：
1. ピクセル7側の設定確認
2. ワイヤレスデバッグポートの入力
3. ADB接続の確立
4. TCP/IPモードへの切り替え
5. 接続確認

#### 2.3 手動セットアップ（スクリプトを使わない場合）

**PowerShellで実行:**

```powershell
# 1. ワイヤレスデバッグポート経由で接続（初回のみ）
# ピクセル7に表示されたポート番号を使用（例: 12345）
adb connect 100.127.121.20:12345

# 2. TCP/IPモードに切り替え
adb tcpip 5555

# 3. 通常ポートで再接続
adb disconnect 100.127.121.20:12345
adb connect 100.127.121.20:5555

# 4. 接続確認
adb devices
```

### 3. 接続確認

**PowerShellで実行:**

```powershell
# デバイス一覧を表示
adb devices

# ピクセル7の情報を取得
adb shell getprop ro.product.model
adb shell getprop ro.build.version.release

# シェルに接続（テスト）
adb shell
```

## 日常的な接続

初回セットアップ後は、以下のコマンドで簡単に接続できます：

**PowerShellで実行:**

```powershell
# 簡易接続スクリプトを使用
.\connect_pixel7_adb.ps1

# または直接コマンド実行
adb connect 100.127.121.20:5555
```

## よくある問題と解決方法

### 接続できない場合

1. **Tailscale接続の確認**
   ```powershell
   # 母艦（Windows）からピクセル7にping
   ping 100.127.121.20
   ```

2. **ワイヤレスデバッグの再有効化**
   - ピクセル7でワイヤレスデバッグを一度OFFにしてから再度ON

3. **ADBサーバーの再起動**
   ```powershell
   adb kill-server
   adb start-server
   adb connect 100.127.121.20:5555
   ```

4. **ポート番号の確認**
   - ピクセル7のワイヤレスデバッグ設定でポート番号を確認
   - ファイアウォールでポートがブロックされていないか確認

### "device unauthorized" エラー

- ピクセル7側で「USBデバッグの承認」ダイアログが表示されるので、「常にこのコンピューターから許可する」にチェックを入れて承認

### 接続が切れる場合

- ピクセル7の省電力設定を確認
- 「開発者オプション > スリープ中もUSBデバッグを維持」を有効化

## ManaOS統合での使用

接続が確立されたら、Pixel7 Node ManagerからADB経由でコマンドを実行できます：

```python
# pixel7_node_manager.py が自動的にADBを使用
from pixel7_node_manager import node_manager

# コマンド実行
result = await node_manager.execute_command("getprop ro.product.model")
print(result.stdout)
```

## セキュリティ注意事項

1. **Tailscaleネットワーク内でのみ使用**
   - ワイヤレスADB接続はセキュアなネットワーク（Tailscale）でのみ使用してください

2. **不要な場合は無効化**
   - 使用しない場合は、ピクセル7でワイヤレスデバッグを無効化してください

3. **ポートの制限**
   - ファイアウォールでADBポート（5555）へのアクセスを制限することを推奨

## 参考

- [ADB公式ドキュメント](https://developer.android.com/studio/command-line/adb)
- [ワイヤレスデバッグの設定](https://developer.android.com/studio/command-line/adb#wireless)
- [ピクセル7統合ガイド](./PIXEL7_INTEGRATION_GUIDE.md)

