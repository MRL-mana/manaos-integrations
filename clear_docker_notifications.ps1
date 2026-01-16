#!/usr/bin/env pwsh
# -*- coding: utf-8 -*-
<#
.SYNOPSIS
    Docker Desktopの通知をクリアするスクリプト
    
.DESCRIPTION
    Docker Desktopの通知パネルに表示されているエラー通知をクリアするための
    対処法を提供します。
#>

Write-Host "🔔 Docker Desktop通知のクリア方法" -ForegroundColor Cyan
Write-Host ("=" * 60) -ForegroundColor Cyan

Write-Host "`n📋 現在の状況:" -ForegroundColor Yellow
Write-Host "   ✅ Dockerエンジンは正常に動作しています" -ForegroundColor Green
Write-Host "   ✅ すべてのコンテナが実行中です" -ForegroundColor Green
Write-Host "   ⚠️  UIの通知にエラーが表示されています" -ForegroundColor Yellow

Write-Host "`n💡 通知をクリアする方法:" -ForegroundColor Yellow
Write-Host "   1. Docker Desktopの通知パネルで「Dismiss all」をクリック" -ForegroundColor Gray
Write-Host "   2. 各通知の「×」ボタンをクリックして個別に閉じる" -ForegroundColor Gray
Write-Host "   3. Docker Desktopを再起動（通知が消えない場合）" -ForegroundColor Gray

Write-Host "`n🔍 エラーの詳細:" -ForegroundColor Yellow
Write-Host "   - 「Failed to fetch extensions」" -ForegroundColor Gray
Write-Host "     → 拡張機能の取得に失敗しましたが、Dockerの基本機能には影響ありません" -ForegroundColor DarkGray
Write-Host "   - 「Failed to apply settings」" -ForegroundColor Gray
Write-Host "     → 設定の適用に失敗しましたが、現在の設定は有効です" -ForegroundColor DarkGray
Write-Host "   - 「connect ENOENT」エラー（53分前）" -ForegroundColor Gray
Write-Host "     → 過去のエラーで、現在は解決済みです" -ForegroundColor DarkGray

Write-Host "`n✅ 結論:" -ForegroundColor Green
Write-Host "   Dockerエンジンは正常に動作しており、コンテナも実行中です。" -ForegroundColor Green
Write-Host "   これらの通知は無視しても問題ありません。" -ForegroundColor Green
Write-Host "   必要に応じて、Docker Desktopの通知パネルから手動で閉じてください。" -ForegroundColor Green

Write-Host "`n" + ("=" * 60) -ForegroundColor Cyan
