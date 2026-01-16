# Linuxサーバー（このはサーバー）でのセットアップ手順

## 実行方法

### 方法1: SSH接続して直接実行（推奨）

```bash
# 1. LinuxサーバーにSSH接続
ssh user@konoha-server

# 2. スクリプトを転送（Windowsから実行）
# PowerShellで実行:
scp setup_visidata.sh setup_ollama_quick.sh setup_excel_llm_integration.sh setup_visidata_ollama_complete.sh excel_llm_processor.py user@konoha-server:~/manaos_integrations/

# 3. Linuxサーバーで実行
cd ~/manaos_integrations
chmod +x *.sh
./setup_visidata_ollama_complete.sh
```

### 方法2: 一括セットアップスクリプト

```bash
# 一括セットアップ
./setup_visidata_ollama_complete.sh
```

### 方法3: 個別に実行

```bash
# 1. VisiDataセットアップ
./setup_visidata.sh

# 2. Ollama確認
./setup_ollama_quick.sh

# 3. Excel/LLM統合
./setup_excel_llm_integration.sh
```

## 必要なファイル

以下のファイルをLinuxサーバーに転送してください：

- `setup_visidata.sh`
- `setup_ollama_quick.sh`
- `setup_excel_llm_integration.sh`
- `setup_visidata_ollama_complete.sh`
- `excel_llm_processor.py`

## 実行前の確認事項

1. **Python3がインストールされているか**
   ```bash
   python3 --version
   ```

2. **SSH接続ができるか**
   ```bash
   ssh user@konoha-server
   ```

3. **作業ディレクトリの準備**
   ```bash
   mkdir -p ~/manaos_integrations
   cd ~/manaos_integrations
   ```

## 使い方（セットアップ後）

```bash
# 1. VisiDataでExcelファイルを開く
vd data.xlsx

# 2. LLMでデータを分析
python3 excel_llm_processor.py data.xlsx 異常値検出

# 3. 結果を確認
cat data_llm_analysis.txt
```

## トラブルシューティング

### 実行権限エラー

```bash
chmod +x *.sh
```

### Python3が見つからない

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3 python3-pip

# CentOS/RHEL
sudo yum install python3 python3-pip
```

### Ollamaが見つからない

```bash
# Ollamaをインストール
curl -fsSL https://ollama.com/install.sh | sh
```
