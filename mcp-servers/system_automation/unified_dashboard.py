#!/usr/bin/env python3
"""
統合ダッシュボード
全システムを統合的に管理・監視
"""

import streamlit as st
from pathlib import Path
from datetime import datetime
import sys

# モジュールパス追加
sys.path.insert(0, str(Path(__file__).parent))

from file_organizer.file_organizer import FileOrganizer
from file_organizer.duplicate_detector import DuplicateDetector
from maintenance.maintenance_scheduler import MaintenanceScheduler
from monitoring.monitor_engine import MonitorEngine

# ページ設定
st.set_page_config(
    page_title="ManaOS 統合ダッシュボード",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# カスタムCSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E88E5;
        text-align: center;
        padding: 1rem;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #667eea;
    }
    .status-good {
        color: #4CAF50;
        font-weight: bold;
    }
    .status-warning {
        color: #FF9800;
        font-weight: bold;
    }
    .status-critical {
        color: #F44336;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# 初期化
@st.cache_resource
def init_engines():
    """エンジン初期化"""
    return {
        "organizer": FileOrganizer(),
        "detector": DuplicateDetector(),
        "scheduler": MaintenanceScheduler(),
        "monitor": MonitorEngine()
    }

engines = init_engines()

# ヘッダー
st.markdown('<h1 class="main-header">🚀 ManaOS 統合ダッシュボード</h1>', unsafe_allow_html=True)
st.markdown("---")

# サイドバー
with st.sidebar:
    st.title("📋 メニュー")
    
    page = st.radio(
        "ページを選択",
        [
            "📊 ダッシュボード",
            "📁 ファイル整理",
            "🔍 重複検出",
            "🔧 メンテナンス",
            "📈 監視システム",
            "⚙️ 設定"
        ]
    )

# ダッシュボード
if page == "📊 ダッシュボード":
    st.title("📊 システムダッシュボード")
    
    # ヘルススコア
    health = engines["monitor"].get_health_score()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "ヘルススコア",
            f"{health['health_score']}/100",
            delta=f"{health['health_level']}"
        )
    
    with col2:
        status = engines["monitor"].get_system_status()
        st.metric(
            "アラート数（24時間）",
            status["alert_count_24h"]
        )
    
    with col3:
        metrics = engines["monitor"].collect_all_metrics()
        cpu = metrics.get("cpu", {}).get("cpu_percent", 0)
        st.metric(
            "CPU使用率",
            f"{cpu:.1f}%"
        )
    
    with col4:
        mem = metrics.get("memory", {}).get("memory_percent", 0)
        st.metric(
            "メモリ使用率",
            f"{mem:.1f}%"
        )
    
    st.markdown("---")
    
    # システムメトリクス
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 システムリソース")
        
        if "disk" in metrics:
            disk = metrics["disk"]
            st.metric("ディスク使用率", f"{disk.get('disk_percent', 0):.1f}%")
            st.progress(disk.get('disk_percent', 0) / 100)
            st.caption(f"使用: {disk.get('disk_used_gb', 0):.1f} GB / {disk.get('disk_total_gb', 0):.1f} GB")
        
        if "processes" in metrics:
            proc = metrics["processes"]
            st.metric("実行中プロセス", f"{proc.get('process_count', 0)}個")
    
    with col2:
        st.subheader("⚠️ 最近のアラート")
        
        if status["recent_alerts"]:
            for alert in status["recent_alerts"][:5]:
                level_class = {
                    "WARNING": "status-warning",
                    "CRITICAL": "status-critical"
                }.get(alert["level"], "")
                
                st.markdown(f"<div class='{level_class}'>[{alert['level']}] {alert['message']}</div>", unsafe_allow_html=True)
        else:
            st.success("アラートなし")
    
    st.markdown("---")
    
    # クイックアクション
    st.subheader("⚡ クイックアクション")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🔄 監視更新", use_container_width=True):
            with st.spinner("更新中..."):
                engines["monitor"].run_monitoring_cycle()
            st.success("更新完了")
    
    with col2:
        if st.button("🧹 メンテナンス", use_container_width=True):
            with st.spinner("実行中..."):
                engines["scheduler"].run_daily_maintenance()
            st.success("完了")
    
    with col3:
        if st.button("🔍 重複検出", use_container_width=True):
            with st.spinner("検出中..."):
                results = engines["detector"].scan_duplicates()
            st.success(f"{results['duplicate_groups']}組の重複を発見")
    
    with col4:
        if st.button("📁 ファイル整理", use_container_width=True):
            with st.spinner("整理中..."):
                results = engines["organizer"].organize_files(dry_run=True)
            st.info(f"{results['organized']}個のファイルを整理予定")

# ファイル整理
elif page == "📁 ファイル整理":
    st.title("📁 ファイル整理システム")
    
    tab1, tab2 = st.tabs(["📦 ファイル整理", "📊 統計情報"])
    
    with tab1:
        st.subheader("自動ファイル整理")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**整理ルール:**")
            config = engines["organizer"].config
            for category, rules in config.get("organize_rules", {}).items():
                st.write(f"  • {category}: {', '.join(rules['extensions'][:3])}...")
        
        with col2:
            st.write("**除外ディレクトリ:**")
            for exclude in config.get("exclude_dirs", [])[:5]:
                st.write(f"  • {exclude}")
        
        if st.button("🚀 ファイル整理実行", type="primary"):
            with st.spinner("整理中..."):
                results = engines["organizer"].organize_files(dry_run=False)
            
            st.success(f"✅ 整理完了: {results['organized']}個のファイルを整理")
            
            if results['categories']:
                st.write("**カテゴリ別:**")
                for cat, count in results['categories'].items():
                    st.write(f"  • {cat}: {count}個")
    
    with tab2:
        st.subheader("システム統計")
        
        stats = engines["organizer"].get_system_stats()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("総ファイル数", f"{stats['total_files']:,}")
        
        with col2:
            st.metric("総サイズ", f"{stats['total_size_mb']:.2f} MB")
        
        with col3:
            organized = stats['stats'].get('total_files_organized', 0)
            st.metric("整理済み", f"{organized:,}")

# 重複検出
elif page == "🔍 重複検出":
    st.title("🔍 重複ファイル検出")
    
    tab1, tab2 = st.tabs(["🔍 スキャン", "📊 結果"])
    
    with tab1:
        st.subheader("重複ファイルスキャン")
        
        if st.button("🔍 スキャン実行", type="primary"):
            with st.spinner("スキャン中... しばらくお待ちください"):
                results = engines["detector"].scan_duplicates()
            
            st.success("✅ スキャン完了")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("重複グループ", f"{results['duplicate_groups']}組")
            
            with col2:
                st.metric("重複ファイル数", f"{results['total_duplicate_files']}個")
            
            with col3:
                wasted_gb = results['wasted_space'] / (1024**3)
                st.metric("無駄な容量", f"{wasted_gb:.2f} GB")
    
    with tab2:
        st.subheader("重複ファイル結果")
        
        summary = engines["detector"].get_duplicate_summary()
        
        if "message" not in summary:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("重複グループ", f"{summary['total_groups']}組")
            
            with col2:
                st.metric("重複ファイル数", f"{summary['total_files']}個")
            
            with col3:
                st.metric("無駄な容量", f"{summary['wasted_space_gb']} GB")
            
            st.markdown("---")
            
            if summary['top_duplicates']:
                st.write("**トップ10の重複:**")
                for i, dup in enumerate(summary['top_duplicates'][:10], 1):
                    with st.expander(f"{i}. {dup['size_mb']} MB × {dup['count']}個"):
                        for file in dup['files']:
                            st.code(file)

# メンテナンス
elif page == "🔧 メンテナンス":
    st.title("🔧 メンテナンス自動化")
    
    tab1, tab2, tab3 = st.tabs(["⚙️ メンテナンス", "📊 ログ", "📈 統計"])
    
    with tab1:
        st.subheader("メンテナンスタスク")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 日次メンテナンス", type="primary", use_container_width=True):
                with st.spinner("実行中..."):
                    results = engines["scheduler"].run_daily_maintenance()
                st.success("✅ 日次メンテナンス完了")
        
        with col2:
            if st.button("📅 週次メンテナンス", use_container_width=True):
                with st.spinner("実行中..."):
                    results = engines["scheduler"].run_weekly_maintenance()
                st.success("✅ 週次メンテナンス完了")
        
        st.markdown("---")
        
        st.write("**個別タスク:**")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📝 ログローテーション", use_container_width=True):
                with st.spinner("実行中..."):
                    results = engines["scheduler"].rotate_logs()
                st.success(f"✅ {results['rotated']}個ローテート")
        
        with col2:
            if st.button("🧹 一時ファイル削除", use_container_width=True):
                with st.spinner("実行中..."):
                    results = engines["scheduler"].cleanup_temp_files()
                st.success(f"✅ {results['deleted']}個削除")
        
        with col3:
            if st.button("💾 データベース最適化", use_container_width=True):
                with st.spinner("実行中..."):
                    results = engines["scheduler"].optimize_databases()
                st.success(f"✅ {results['optimized']}個最適化")
    
    with tab2:
        st.subheader("メンテナンスログ")
        
        log_path = engines["scheduler"].log_path
        if log_path.exists():
            with open(log_path, 'r', encoding='utf-8') as f:
                logs = f.readlines()
            
            st.text_area("ログ", "".join(logs[-50:]), height=400)
        else:
            st.info("ログファイルがありません")
    
    with tab3:
        st.subheader("メンテナンス統計")
        
        status = engines["scheduler"].get_status()
        
        st.metric("最終実行", status['last_maintenance'])
        st.metric("有効", "✅" if status['enabled'] else "❌")
        
        if status['disk_usage']:
            st.metric("ディスク使用率", f"{status['disk_usage']['use_percent']:.1f}%")

# 監視システム
elif page == "📈 監視システム":
    st.title("📈 統合監視システム")
    
    tab1, tab2, tab3 = st.tabs(["📊 リアルタイム", "⚠️ アラート", "📈 メトリクス"])
    
    with tab1:
        st.subheader("リアルタイム監視")
        
        if st.button("🔄 更新", type="primary"):
            with st.spinner("更新中..."):
                engines["monitor"].run_monitoring_cycle()
        
        metrics = engines["monitor"].collect_all_metrics()
        
        # CPU
        if "cpu" in metrics:
            st.write("**CPU:**")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("CPU使用率", f"{metrics['cpu'].get('cpu_percent', 0):.1f}%")
                st.progress(metrics['cpu'].get('cpu_percent', 0) / 100)
            
            with col2:
                st.metric("ロードアベレージ", f"{metrics['cpu'].get('load_avg_1m', 0):.2f}")
            
            with col3:
                st.metric("CPUコア数", f"{metrics['cpu'].get('cpu_count', 0)}")
        
        # メモリ
        if "memory" in metrics:
            st.write("**メモリ:**")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("メモリ使用率", f"{metrics['memory'].get('memory_percent', 0):.1f}%")
                st.progress(metrics['memory'].get('memory_percent', 0) / 100)
            
            with col2:
                st.metric("使用中", f"{metrics['memory'].get('memory_used_gb', 0):.1f} GB")
            
            with col3:
                st.metric("利用可能", f"{metrics['memory'].get('memory_available_gb', 0):.1f} GB")
        
        # ディスク
        if "disk" in metrics:
            st.write("**ディスク:**")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("ディスク使用率", f"{metrics['disk'].get('disk_percent', 0):.1f}%")
                st.progress(metrics['disk'].get('disk_percent', 0) / 100)
            
            with col2:
                st.metric("使用中", f"{metrics['disk'].get('disk_used_gb', 0):.1f} GB")
            
            with col3:
                st.metric("空き", f"{metrics['disk'].get('disk_free_gb', 0):.1f} GB")
    
    with tab2:
        st.subheader("アラート一覧")
        
        alerts = engines["monitor"].alerts
        
        if alerts:
            for alert in alerts[-20:]:
                level_emoji = {
                    "WARNING": "⚠️",
                    "CRITICAL": "🚨"
                }.get(alert.get("level", ""), "ℹ️")
                
                st.markdown(f"**{level_emoji} [{alert['level']}] {alert['type']}**")
                st.write(alert['message'])
                st.caption(alert.get('timestamp', ''))
                st.markdown("---")
        else:
            st.success("アラートなし")
    
    with tab3:
        st.subheader("メトリクス履歴")
        
        history = engines["monitor"].metrics.get("history", [])
        
        if history:
            st.write(f"履歴: {len(history)}件")
            
            # 最新のメトリクスを表示
            latest = history[-1]
            st.json(latest)
        else:
            st.info("メトリクス履歴がありません")

# 設定
elif page == "⚙️ 設定":
    st.title("⚙️ システム設定")
    
    tab1, tab2, tab3 = st.tabs(["📁 ファイル整理", "🔧 メンテナンス", "📈 監視"])
    
    with tab1:
        st.subheader("ファイル整理設定")
        
        config = engines["organizer"].config
        
        st.write("**整理ルール:**")
        st.json(config.get("organize_rules", {}))
        
        st.write("**除外ディレクトリ:**")
        st.json(config.get("exclude_dirs", []))
    
    with tab2:
        st.subheader("メンテナンス設定")
        
        config = engines["scheduler"].config
        
        st.write("**タスク設定:**")
        st.json(config.get("tasks", {}))
    
    with tab3:
        st.subheader("監視設定")
        
        config = engines["monitor"].config
        
        st.write("**閾値設定:**")
        st.json(config.get("alert_thresholds", {}))
        
        st.write("**監視項目:**")
        st.json(config.get("monitoring", {}))

# フッター
st.markdown("---")
st.markdown(
    f'<div style="text-align: center; color: #666; padding: 1rem;">'
    f'© 2025 ManaOS - 統合ダッシュボード | '
    f'最終更新: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
    f'</div>',
    unsafe_allow_html=True
)

