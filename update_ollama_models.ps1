# Ollamaモデル更新スクリプト
# RAGタスクに最適なモデルをインストール・設定

Write-Host "=== Ollamaモデル更新スクリプト ===" -ForegroundColor Cyan
Write-Host ""

# 推奨モデル一覧
$recommendedModels = @(
    @{
        Name = "qwen3:4b"
        Description = "最新モデル（Qwen2.5-72B相当の性能、4Bパラメータ）"
        Priority = "Highest"
    },
    @{
        Name = "qwen3-4b"
        Description = "Qwen3（別名、上記と同じ）"
        Priority = "Highest"
    },
    @{
        Name = "qwen2.5:7b"
        Description = "RAGタスクに最適（日本語対応優秀、安定版）"
        Priority = "High"
    },
    @{
        Name = "mistral-nemo:12b"
        Description = "多言語RAG、長文処理"
        Priority = "Medium"
    },
    @{
        Name = "llama3.1:8b"
        Description = "長文処理、多段階推論"
        Priority = "Medium"
    },
    @{
        Name = "phi3:mini"
        Description = "軽量・高速（小規模RAG用）"
        Priority = "Low"
    }
)

Write-Host "📋 推奨モデル一覧:" -ForegroundColor Yellow
foreach ($model in $recommendedModels) {
    $priorityColor = switch ($model.Priority) {
        "High" { "Green" }
        "Medium" { "Yellow" }
        "Low" { "Gray" }
    }
    Write-Host "  [$($model.Priority)] $($model.Name) - $($model.Description)" -ForegroundColor $priorityColor
}

Write-Host ""
Write-Host "どのモデルをインストールしますか？" -ForegroundColor Cyan
Write-Host "1. qwen3:4b (最新・最推奨: Qwen2.5-72B相当の性能)"
Write-Host "2. qwen2.5:7b (安定版: RAGタスクに最適)"
Write-Host "3. mistral-nemo:12b (高性能: 多言語RAG)"
Write-Host "4. llama3.1:8b (長文処理)"
Write-Host "5. phi3:mini (軽量)"
Write-Host "6. すべてインストール"
Write-Host "7. 現在のモデル一覧を確認"
Write-Host "0. キャンセル"

$choice = Read-Host "選択 (1-7)"

switch ($choice) {
    "1" {
        Write-Host "`nqwen3:4b をインストール中..." -ForegroundColor Yellow
        Write-Host "注意: Qwen3がOllamaにまだ追加されていない場合、エラーが出る可能性があります" -ForegroundColor Yellow
        try {
            ollama pull qwen3:4b
            Write-Host "✅ インストール完了" -ForegroundColor Green
            Write-Host "`n環境変数を設定しますか？ (Y/N)" -ForegroundColor Cyan
            $setEnv = Read-Host
            if ($setEnv -eq "Y" -or $setEnv -eq "y") {
                [System.Environment]::SetEnvironmentVariable("OLLAMA_DEFAULT_MODEL", "qwen3:4b", "User")
                [System.Environment]::SetEnvironmentVariable("OLLAMA_RAG_MODEL", "qwen3:4b", "User")
                Write-Host "✅ 環境変数を設定しました" -ForegroundColor Green
            }
        } catch {
            Write-Host "⚠️ Qwen3のインストールに失敗しました。Qwen2.5を使用してください。" -ForegroundColor Yellow
            Write-Host "代替として qwen2.5:7b をインストールしますか？ (Y/N)" -ForegroundColor Cyan
            $fallback = Read-Host
            if ($fallback -eq "Y" -or $fallback -eq "y") {
                ollama pull qwen2.5:7b
                Write-Host "✅ qwen2.5:7b をインストールしました" -ForegroundColor Green
            }
        }
    }
    "2" {
        Write-Host "`nqwen2.5:7b をインストール中..." -ForegroundColor Yellow
        ollama pull qwen2.5:7b
        Write-Host "✅ インストール完了" -ForegroundColor Green
        Write-Host "`n環境変数を設定しますか？ (Y/N)" -ForegroundColor Cyan
        $setEnv = Read-Host
        if ($setEnv -eq "Y" -or $setEnv -eq "y") {
            [System.Environment]::SetEnvironmentVariable("OLLAMA_DEFAULT_MODEL", "qwen2.5:7b", "User")
            [System.Environment]::SetEnvironmentVariable("OLLAMA_RAG_MODEL", "qwen2.5:7b", "User")
            Write-Host "✅ 環境変数を設定しました" -ForegroundColor Green
        }
    }
    "3" {
        Write-Host "`nmistral-nemo:12b をインストール中..." -ForegroundColor Yellow
        ollama pull mistral-nemo:12b
        Write-Host "✅ インストール完了" -ForegroundColor Green
    }
    "4" {
        Write-Host "`nllama3.1:8b をインストール中..." -ForegroundColor Yellow
        ollama pull llama3.1:8b
        Write-Host "✅ インストール完了" -ForegroundColor Green
    }
    "5" {
        Write-Host "`nphi3:mini をインストール中..." -ForegroundColor Yellow
        ollama pull phi3:mini
        Write-Host "✅ インストール完了" -ForegroundColor Green
    }
    "6" {
        Write-Host "`nすべての推奨モデルをインストール中..." -ForegroundColor Yellow
        foreach ($model in $recommendedModels) {
            Write-Host "`n  $($model.Name) をインストール中..." -ForegroundColor Cyan
            try {
                ollama pull $model.Name
            } catch {
                Write-Host "  ⚠️ $($model.Name) のインストールに失敗しました（スキップ）" -ForegroundColor Yellow
            }
        }
        Write-Host "`n✅ すべてのモデルのインストールが完了しました" -ForegroundColor Green
    }
    "7" {
        Write-Host "`n現在インストール済みのモデル:" -ForegroundColor Yellow
        ollama list
    }
    "0" {
        Write-Host "`nキャンセルしました" -ForegroundColor Yellow
        exit
    }
    default {
        Write-Host "`n無効な選択です" -ForegroundColor Red
        exit
    }
}

Write-Host "`n完了しました！" -ForegroundColor Green
Write-Host "`n📝 設定方法:" -ForegroundColor Cyan
Write-Host "  環境変数 OLLAMA_DEFAULT_MODEL でデフォルトモデルを設定"
Write-Host "  環境変数 OLLAMA_RAG_MODEL でRAGシステム用モデルを設定"
Write-Host "`n例:"
Write-Host "  [System.Environment]::SetEnvironmentVariable('OLLAMA_DEFAULT_MODEL', 'qwen2.5:7b', 'User')"
Write-Host "  [System.Environment]::SetEnvironmentVariable('OLLAMA_RAG_MODEL', 'qwen2.5:7b', 'User')"

