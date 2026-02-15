# デプロイメント セキュリティスキャン設定

## SAST （Static Application Security Testing）

### 1. Bandit（Pythonセキュリティスキャナー）

```bash
# インストール
pip install bandit

# スキャン実行
bandit -r . -f json -o bandit-report.json

# 設定ファイル（.bandit）
[bandit]
# スキップするテスト
skips = B404, B603
exclude = /test,venv

# 除外ファイル
exclude_dirs = /tests
```

### 2. Safety（依存関係セキュリティチェック）

```bash
# インストール
pip install safety

# スキャン実行
safety check --json > safety-report.json

# 既知の脆弱性がないか確認
safety check --full-report
```

### 3. SonarQube（コード品質＆セキュリティ）

```yaml
# docker-compose.yml に追加
sonarqube:
  image: sonarqube:developer
  ports:
    - "9000:9000"
  environment:
    SONAR_JDBC_URL: jdbc:postgresql://postgres:5432/sonar
    SONAR_JDBC_USERNAME: sonar
    SONAR_JDBC_PASSWORD: sonar
  volumes:
    - sonarqube_data:/opt/sonarqube/data
    - sonarqube_logs:/opt/sonarqube/logs
```

## DAST （Dynamic Application Security Testing）

### 1. OWASP ZAP（ウェブアプリケーション脆弱性スキャナー）

```bash
# スキャン実行
zaproxy -cmd -quickurl http://localhost:9502 -quickout zap-report.html
```

### 2. Burp Suite Community（インタラクティブテスト）

- ブラウザプロキシとして設定
- 手動での脅威検証
- API エンドポイントテスト

## コンテナセキュリティ

### 1. Trivy（コンテナ脆弱性スキャナー）

```bash
# インストール
brew install aquasecurity/trivy/trivy

# スキャン実行
trivy image mrlmana/manaos-unified-api:latest

# JSON形式で出力
trivy image -f json mrlmana/manaos-unified-api:latest > trivy-report.json
```

### 2. Grype（SBOM脆弱性スキャナー）

```bash
# インストール
curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | sh -s -- -b /usr/local/bin

# スキャン実行
grype mrlmana/manaos-unified-api:latest
```

## インフラストラクチャセキュリティ

### 1. Checkov（Infrastructure as Codeスキャナー）

```bash
# インストール
pip install checkov

# Kubernetesマニフェストスキャン
checkov -d kubernetes/ --framework kubernetes

# Terraformスキャン
checkov -d terraform/ --framework terraform
```

### 2. Kube-bench（Kubernetesセキュリティベンチマーク）

```bash
# インストール
kubectl apply -f https://raw.githubusercontent.com/aquasecurity/kube-bench/main/job.yaml

# 確認
kubectl logs -l app=kube-bench -n kube-system
```

## CI/CD統合

### GitHub Actions パイプライン

```yaml
# .github/workflows/security-scan.yml
name: Security Scanning

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * *'  # 日本時間11時

jobs:
  sast:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Bandit Security Scan
        run: |
          pip install bandit
          bandit -r . -f json -o bandit-report.json
      
      - name: Safety Check
        run: |
          pip install safety
          safety check --json > safety-report.json
      
      - name: Upload reports
        uses: actions/upload-artifact@v4
        with:
          name: security-reports
          path: |
            bandit-report.json
            safety-report.json

  dast:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Start application
        run: |
          docker-compose up -d unified-api
          sleep 30
      
      - name: OWASP ZAP Scan
        uses: zaproxy/action-full-scan@v0.4.0
        with:
          target: 'http://localhost:9502'
          rules_file_name: '.zap/rules.tsv'
          cmd_options: '-a'

  container:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Trivy Scan
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'mrlmana/manaos-unified-api:latest'
          format: 'sarif'
          output: 'trivy-results.sarif'
      
      - name: Upload to GitHub Security
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'

  infrastructure:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Checkov Scan
        uses: bridgecrewio/checkov-action@master
        with:
          directory: kubernetes/
          framework: kubernetes
          quiet: false
          soft_fail: false
```

## セキュリティベストプラクティス

### 1. シークレット管理

```bash
# git-secretsインストール
brew install git-secrets

# 有効化
git secrets --install
git secrets --register-aws

# スキャン
git secrets --scan
```

### 2. 依存関係管理

```bash
# Dependabot有効化（GitHub）
# Repository → Settings → Code security & analysis → Dependabot

# 定期的にアップデート
pip install -U pip setuptools wheel
pip install -U -r requirements.txt
```

### 3. SBOM生成

```bash
# Syft でSBOM生成
curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin
syft mrlmana/manaos-unified-api:latest -o spdx > sbom.spdx.json
```

## セキュリティプリンシパル

✅ **最小権限の原則** - 必要な権限のみを付与  
✅ **多要素認証** - 本番環境でのアクセス保護  
✅ **監査ログ** - すべての変更を記録  
✅ **定期スキャン** - 継続的な脆弱性監視  
✅ **パッチ管理** - セキュリティパッチを迅速に適用  
✅ **ネットワーク分離** - サービス間のトラフィック制限  

## 参考リンク

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [CVSS Calculator](https://www.first.org/cvss/calculator/3.1)
- [Kubernetes Security Policy](https://kubernetes.io/docs/concepts/security/pod-security-standards/)
