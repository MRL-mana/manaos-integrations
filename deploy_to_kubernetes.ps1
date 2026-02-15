# ManaOS Kubernetes Deployment Script
# Kubernetesクラスタへの自動デプロイスクリプト

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("kubectl", "helm")]
    [string]$Method = "helm",
    
    [Parameter(Mandatory=$false)]
    [string]$Namespace = "manaos",
    
    [Parameter(Mandatory=$false)]
    [string]$Context = "",
    
    [switch]$DryRun,
    [switch]$WaitForReady,
    [int]$Timeout = 600
)

$ErrorActionPreference = "Stop"

Write-Host "🚀 ManaOS Kubernetes Deployment" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Gray

# ============================================================================
# 1. 前提条件チェック
# ============================================================================

Write-Host "`n📋 前提条件チェック中..." -ForegroundColor Yellow

# kubectlのインストール確認
$kubectlCmd = Get-Command kubectl -ErrorAction SilentlyContinue
if (-not $kubectlCmd) {
    Write-Host "  ❌ kubectl がインストールされていません" -ForegroundColor Red
    Write-Host "  https://kubernetes.io/docs/tasks/tools/" -ForegroundColor Blue
    exit 1
}
Write-Host "  ✅ kubectl: $((kubectl version --client --short 2>$null) -replace 'Client Version: ', '')" -ForegroundColor Green

# Helmのインストール確認（Helmメソッドの場合）
if ($Method -eq "helm") {
    $helmCmd = Get-Command helm -ErrorAction SilentlyContinue
    if (-not $helmCmd) {
        Write-Host "  ❌ helm がインストールされていません" -ForegroundColor Red
        Write-Host "  https://helm.sh/docs/intro/install/" -ForegroundColor Blue
        exit 1
    }
    Write-Host "  ✅ helm: $(helm version --short)" -ForegroundColor Green
}

# クラスタ接続確認
Write-Host "  → クラスタ接続確認..." -ForegroundColor Gray

if ($Context) {
    kubectl config use-context $Context 2>&1 | Out-Null
}

$clusterInfo = kubectl cluster-info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ❌ Kubernetesクラスタに接続できません" -ForegroundColor Red
    Write-Host "  kubectl config view でクラスタ設定を確認してください" -ForegroundColor Yellow
    exit 1
}

$currentContext = kubectl config current-context
Write-Host "  ✅ 接続中のクラスタ: $currentContext" -ForegroundColor Green

# ============================================================================
# 2. Namespace作成
# ============================================================================

Write-Host "`n📦 Namespace準備中..." -ForegroundColor Yellow

$namespaceExists = kubectl get namespace $Namespace 2>$null
if (-not $namespaceExists) {
    Write-Host "  → Namespace '$Namespace' を作成中..." -ForegroundColor Gray
    
    if ($DryRun) {
        Write-Host "  [DRY RUN] kubectl create namespace $Namespace" -ForegroundColor DarkGray
    } else {
        kubectl create namespace $Namespace
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✅ Namespace作成完了" -ForegroundColor Green
        } else {
            Write-Host "  ❌ Namespace作成失敗" -ForegroundColor Red
            exit 1
        }
    }
} else {
    Write-Host "  ✓ Namespace '$Namespace' は既に存在します" -ForegroundColor Gray
}

# ============================================================================
# 3. Secretsの作成（環境変数から）
# ============================================================================

Write-Host "`n🔐 Secrets準備中..." -ForegroundColor Yellow

$secretsToCreate = @()

if ($env:BRAVE_API_KEY) { $secretsToCreate += "--from-literal=BRAVE_API_KEY=$env:BRAVE_API_KEY" }
if ($env:CIVITAI_API_KEY) { $secretsToCreate += "--from-literal=CIVITAI_API_KEY=$env:CIVITAI_API_KEY" }
if ($env:OPENAI_API_KEY) { $secretsToCreate += "--from-literal=OPENAI_API_KEY=$env:OPENAI_API_KEY" }
if ($env:ANTHROPIC_API_KEY) { $secretsToCreate += "--from-literal=ANTHROPIC_API_KEY=$env:ANTHROPIC_API_KEY" }
if ($env:GRAFANA_PASSWORD) { $secretsToCreate += "--from-literal=GRAFANA_PASSWORD=$env:GRAFANA_PASSWORD" }

if ($secretsToCreate.Count -gt 0) {
    $secretExists = kubectl get secret manaos-secrets -n $Namespace 2>$null
    
    if ($secretExists) {
        Write-Host "  → Secret 'manaos-secrets' を更新中..." -ForegroundColor Gray
        kubectl delete secret manaos-secrets -n $Namespace 2>&1 | Out-Null
    }
    
    $secretCmd = "kubectl create secret generic manaos-secrets -n $Namespace $($secretsToCreate -join ' ')"
    
    if ($DryRun) {
        Write-Host "  [DRY RUN] $secretCmd" -ForegroundColor DarkGray
    } else {
        Invoke-Expression $secretCmd | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✅ Secrets作成完了 ($($secretsToCreate.Count) 件のキー)" -ForegroundColor Green
        } else {
            Write-Host "  ⚠️ Secrets作成失敗（スキップします）" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "  ℹ️ 環境変数からSecretsを作成できません" -ForegroundColor Gray
    Write-Host "  💡 環境変数を設定してください: BRAVE_API_KEY, CIVITAI_API_KEY, 等" -ForegroundColor Yellow
}

# ============================================================================
# 4. デプロイメント実行
# ============================================================================

Write-Host "`n🚢 デプロイメント実行中..." -ForegroundColor Yellow

if ($Method -eq "helm") {
    # Helmデプロイ
    Write-Host "  → Helmチャートをデプロイ中..." -ForegroundColor Gray
    
    $helmArgs = @(
        "upgrade",
        "--install",
        "manaos",
        ".\helm",
        "-n", $Namespace,
        "--create-namespace"
    )
    
    if ($DryRun) {
        $helmArgs += "--dry-run"
        $helmArgs += "--debug"
    }
    
    if ($WaitForReady) {
        $helmArgs += "--wait"
        $helmArgs += "--timeout"
        $helmArgs += "${Timeout}s"
    }
    
    Write-Host "  実行コマンド: helm $($helmArgs -join ' ')" -ForegroundColor DarkGray
    
    & helm $helmArgs
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ Helmデプロイ完了" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Helmデプロイ失敗" -ForegroundColor Red
        exit 1
    }
    
} else {
    # kubectlデプロイ
    Write-Host "  → Kubernetesマニフェストを適用中..." -ForegroundColor Gray
    
    $manifests = @(
        "kubernetes/configmap.yaml",
        "kubernetes/persistent-volumes.yaml",
        "kubernetes/unified-api-deployment.yaml",
        "kubernetes/mrl-memory-deployment.yaml",
        "kubernetes/learning-system-deployment.yaml",
        "kubernetes/hpa.yaml",
        "kubernetes/ingress.yaml"
    )
    
    foreach ($manifest in $manifests) {
        if (Test-Path $manifest) {
            Write-Host "  → 適用中: $manifest" -ForegroundColor Gray
            
            if ($DryRun) {
                kubectl apply -f $manifest -n $Namespace --dry-run=client
            } else {
                kubectl apply -f $manifest -n $Namespace
            }
            
            if ($LASTEXITCODE -ne 0) {
                Write-Host "  ❌ 適用失敗: $manifest" -ForegroundColor Red
            }
        } else {
            Write-Host "  ⚠️ ファイルが見つかりません: $manifest" -ForegroundColor Yellow
        }
    }
    
    Write-Host "  ✅ マニフェスト適用完了" -ForegroundColor Green
}

# ============================================================================
# 5. デプロイメント状態確認
# ============================================================================

if (-not $DryRun) {
    Write-Host "`n🔍 デプロイメント状態確認中..." -ForegroundColor Yellow
    
    Write-Host "`n📦 Pods:" -ForegroundColor Cyan
    kubectl get pods -n $Namespace
    
    Write-Host "`n🌐 Services:" -ForegroundColor Cyan
    kubectl get svc -n $Namespace
    
    Write-Host "`n📊 HPA:" -ForegroundColor Cyan
    kubectl get hpa -n $Namespace
    
    if ($WaitForReady) {
        Write-Host "`n⏱️ Podの準備完了を待機中..." -ForegroundColor Yellow
        
        $endTime = (Get-Date).AddSeconds($Timeout)
        $allReady = $false
        
        while ((Get-Date) -lt $endTime) {
            $pods = kubectl get pods -n $Namespace -o json | ConvertFrom-Json
            $totalPods = $pods.items.Count
            $readyPods = ($pods.items | Where-Object { 
                $_.status.conditions | Where-Object { 
                    $_.type -eq "Ready" -and $_.status -eq "True" 
                }
            }).Count
            
            Write-Host "  準備完了: $readyPods / $totalPods" -ForegroundColor Gray
            
            if ($readyPods -eq $totalPods -and $totalPods -gt 0) {
                $allReady = $true
                break
            }
            
            Start-Sleep -Seconds 5
        }
        
        if ($allReady) {
            Write-Host "  ✅ すべてのPodが準備完了" -ForegroundColor Green
        } else {
            Write-Host "  ⚠️ タイムアウト: 一部のPodがまだ準備中です" -ForegroundColor Yellow
        }
    }
}

# ============================================================================
# 6. アクセス情報表示
# ============================================================================

Write-Host "`n" + ("=" * 80) -ForegroundColor Gray
Write-Host "✅ デプロイメント完了！" -ForegroundColor Green
Write-Host ("=" * 80) -ForegroundColor Gray

if (-not $DryRun) {
    Write-Host "`n🌐 アクセス方法:" -ForegroundColor Cyan
    
    # LoadBalancerのExternal IPを取得
    $unifiedApiSvc = kubectl get svc unified-api -n $Namespace -o json 2>$null | ConvertFrom-Json
    
    if ($unifiedApiSvc -and $unifiedApiSvc.status.loadBalancer.ingress) {
        $externalIp = $unifiedApiSvc.status.loadBalancer.ingress[0].ip
        if (-not $externalIp) {
            $externalIp = $unifiedApiSvc.status.loadBalancer.ingress[0].hostname
        }
        
        if ($externalIp) {
            Write-Host "  Unified API: http://${externalIp}:9502" -ForegroundColor Gray
        }
    }
    
    Write-Host "`n  またはPort-Forwardを使用:" -ForegroundColor Yellow
    Write-Host "  kubectl port-forward -n $Namespace svc/unified-api 9502:9502" -ForegroundColor Gray
    Write-Host "  kubectl port-forward -n $Namespace svc/grafana 3000:3000" -ForegroundColor Gray
    Write-Host "  kubectl port-forward -n $Namespace svc/prometheus 9090:9090" -ForegroundColor Gray
    
    Write-Host "`n📝 便利なコマンド:" -ForegroundColor Cyan
    Write-Host "  ログ確認:         kubectl logs -n $Namespace -l app=unified-api -f" -ForegroundColor Gray
    Write-Host "  Pod確認:          kubectl get pods -n $Namespace -w" -ForegroundColor Gray
    Write-Host "  サービス確認:     kubectl get svc -n $Namespace" -ForegroundColor Gray
    Write-Host "  リソース使用量:   kubectl top pods -n $Namespace" -ForegroundColor Gray
    Write-Host "  アンインストール: " -ForegroundColor Gray
    if ($Method -eq "helm") {
        Write-Host "                    helm uninstall manaos -n $Namespace" -ForegroundColor Gray
    } else {
        Write-Host "                    kubectl delete namespace $Namespace" -ForegroundColor Gray
    }
}

Write-Host "`n🎉 Happy Kubernetes!" -ForegroundColor Cyan
