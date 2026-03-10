import asyncio
import json
import logging
import sqlite3
import time
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

class BlockchainTransaction(BaseModel):
    id: Optional[str] = None
    from_address: str
    to_address: str
    amount: float
    transaction_type: str  # data_transfer, smart_contract, nft_mint, token_transfer
    data: Dict[str, Any] = {}
    gas_fee: float = 0.0
    status: str = "pending"  # pending, confirmed, failed
    block_hash: Optional[str] = None
    created_at: Optional[str] = None
    confirmed_at: Optional[str] = None

class SmartContract(BaseModel):
    id: Optional[str] = None
    name: str
    contract_type: str  # automation, governance, token, nft, dao
    code: str
    deployed_address: Optional[str] = None
    owner: str
    status: str = "draft"  # draft, deployed, active, paused
    gas_limit: int = 1000000
    created_at: Optional[str] = None
    deployed_at: Optional[str] = None

class NFT(BaseModel):
    id: Optional[str] = None
    token_id: str
    name: str
    description: str
    image_url: str
    metadata: Dict[str, Any] = {}
    owner: str
    contract_address: str
    created_at: Optional[str] = None
    last_transfer: Optional[str] = None

class ManaBlockchainIntegrationSystem:
    def __init__(self):
        self.app = FastAPI(title="Mana Blockchain Integration System", version="1.0.0")
        self.db_path = "/root/mana_blockchain_integration.db"
        self.logger = logger
        self.blockchain_network = BlockchainNetwork()
        self.smart_contracts = {}
        self.nft_collection = {}
        self.transaction_pool = []
        self.init_database()
        self.setup_api()
        self.setup_startup_events()
        self.start_background_tasks()
        self.logger.info("🚀 Mana Blockchain Integration System 初期化完了")

    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # ブロックチェーントランザクションテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS blockchain_transactions (
                id TEXT PRIMARY KEY,
                from_address TEXT NOT NULL,
                to_address TEXT NOT NULL,
                amount REAL NOT NULL,
                transaction_type TEXT NOT NULL,
                data TEXT,
                gas_fee REAL DEFAULT 0.0,
                status TEXT DEFAULT 'pending',
                block_hash TEXT,
                created_at TEXT NOT NULL,
                confirmed_at TEXT
            )
        """)
        
        # スマートコントラクトテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS smart_contracts (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                contract_type TEXT NOT NULL,
                code TEXT NOT NULL,
                deployed_address TEXT,
                owner TEXT NOT NULL,
                status TEXT DEFAULT 'draft',
                gas_limit INTEGER DEFAULT 1000000,
                created_at TEXT NOT NULL,
                deployed_at TEXT
            )
        """)
        
        # NFTテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nfts (
                id TEXT PRIMARY KEY,
                token_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                image_url TEXT,
                metadata TEXT,
                owner TEXT NOT NULL,
                contract_address TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_transfer TEXT
            )
        """)
        
        # ブロックチェーンメトリクステーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS blockchain_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                total_transactions INTEGER,
                confirmed_transactions INTEGER,
                pending_transactions INTEGER,
                total_contracts INTEGER,
                active_contracts INTEGER,
                total_nfts INTEGER,
                network_hash_rate REAL,
                average_gas_price REAL,
                block_time REAL
            )
        """)
        
        conn.commit()
        conn.close()
        self.logger.info("データベース初期化完了")

    def setup_api(self):
        @self.app.get("/api/status", summary="ブロックチェーン統合システムのステータス")
        async def get_status():
            return {
                "timestamp": datetime.now().isoformat(),
                "system": "Mana Blockchain Integration System",
                "status": "healthy",
                "version": self.app.version,
                "network_status": self.blockchain_network.status,
                "total_transactions": len(self.transaction_pool),
                "smart_contracts": len(self.smart_contracts),
                "nft_collection": len(self.nft_collection)
            }

        @self.app.post("/api/blockchain/transaction", summary="ブロックチェーントランザクション作成")
        async def create_transaction(transaction: BlockchainTransaction):
            transaction_id = f"tx_{int(time.time())}_{hash(transaction.from_address) % 10000}"
            transaction.id = transaction_id
            transaction.created_at = datetime.now().isoformat()
            
            # トランザクションを検証
            if not await self.validate_transaction(transaction):
                raise HTTPException(status_code=400, detail="Invalid transaction")
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO blockchain_transactions 
                (id, from_address, to_address, amount, transaction_type, data, gas_fee, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                transaction.id,
                transaction.from_address,
                transaction.to_address,
                transaction.amount,
                transaction.transaction_type,
                json.dumps(transaction.data),
                transaction.gas_fee,
                transaction.status,
                transaction.created_at
            ))
            
            conn.commit()
            conn.close()
            
            # トランザクションプールに追加
            self.transaction_pool.append(transaction)
            
            # ブロックチェーンネットワークに送信
            await self.blockchain_network.submit_transaction(transaction)
            
            self.logger.info(f"ブロックチェーントランザクション作成: {transaction_id}")
            return {"status": "success", "transaction_id": transaction_id, "message": "トランザクションが作成されました"}

        @self.app.get("/api/blockchain/transactions", summary="ブロックチェーントランザクション一覧")
        async def get_transactions(status: Optional[str] = None, address: Optional[str] = None):
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = "SELECT * FROM blockchain_transactions WHERE 1=1"
            params = []
            
            if status:
                query += " AND status = ?"
                params.append(status)
            
            if address:
                query += " AND (from_address = ? OR to_address = ?)"
                params.extend([address, address])
            
            query += " ORDER BY created_at DESC"
            
            cursor.execute(query, params)
            
            transactions = []
            for row in cursor.fetchall():
                transactions.append({
                    "id": row[0],
                    "from_address": row[1],
                    "to_address": row[2],
                    "amount": row[3],
                    "transaction_type": row[4],
                    "data": json.loads(row[5]) if row[5] else {},
                    "gas_fee": row[6],
                    "status": row[7],
                    "block_hash": row[8],
                    "created_at": row[9],
                    "confirmed_at": row[10]
                })
            
            conn.close()
            return {"transactions": transactions, "count": len(transactions)}

        @self.app.post("/api/blockchain/smart-contract", summary="スマートコントラクト作成")
        async def create_smart_contract(contract: SmartContract):
            contract_id = f"contract_{int(time.time())}_{hash(contract.name) % 10000}"
            contract.id = contract_id
            contract.created_at = datetime.now().isoformat()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO smart_contracts 
                (id, name, contract_type, code, owner, status, gas_limit, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                contract.id,
                contract.name,
                contract.contract_type,
                contract.code,
                contract.owner,
                contract.status,
                contract.gas_limit,
                contract.created_at
            ))
            
            conn.commit()
            conn.close()
            
            self.smart_contracts[contract_id] = contract
            
            self.logger.info(f"スマートコントラクト作成: {contract_id} - {contract.name}")
            return {"status": "success", "contract_id": contract_id, "message": "スマートコントラクトが作成されました"}

        @self.app.post("/api/blockchain/smart-contract/{contract_id}/deploy", summary="スマートコントラクトデプロイ")
        async def deploy_smart_contract(contract_id: str):
            if contract_id not in self.smart_contracts:
                raise HTTPException(status_code=404, detail="Smart contract not found")
            
            contract = self.smart_contracts[contract_id]
            
            # スマートコントラクトをデプロイ
            deployed_address = await self.blockchain_network.deploy_contract(contract)
            
            contract.deployed_address = deployed_address
            contract.status = "deployed"
            contract.deployed_at = datetime.now().isoformat()
            
            # データベース更新
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE smart_contracts 
                SET deployed_address = ?, status = ?, deployed_at = ?
                WHERE id = ?
            """, (deployed_address, contract.status, contract.deployed_at, contract_id))
            conn.commit()
            conn.close()
            
            self.logger.info(f"スマートコントラクトデプロイ: {contract_id} - {deployed_address}")
            return {"status": "success", "deployed_address": deployed_address, "message": "スマートコントラクトがデプロイされました"}

        @self.app.get("/api/blockchain/smart-contracts", summary="スマートコントラクト一覧")
        async def get_smart_contracts(status: Optional[str] = None):
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if status:
                cursor.execute("""
                    SELECT * FROM smart_contracts 
                    WHERE status = ?
                    ORDER BY created_at DESC
                """, (status,))
            else:
                cursor.execute("""
                    SELECT * FROM smart_contracts 
                    ORDER BY created_at DESC
                """)
            
            contracts = []
            for row in cursor.fetchall():
                contracts.append({
                    "id": row[0],
                    "name": row[1],
                    "contract_type": row[2],
                    "code": row[3],
                    "deployed_address": row[4],
                    "owner": row[5],
                    "status": row[6],
                    "gas_limit": row[7],
                    "created_at": row[8],
                    "deployed_at": row[9]
                })
            
            conn.close()
            return {"contracts": contracts, "count": len(contracts)}

        @self.app.post("/api/blockchain/nft/mint", summary="NFTミント")
        async def mint_nft(nft: NFT):
            nft_id = f"nft_{int(time.time())}_{hash(nft.name) % 10000}"
            nft.id = nft_id
            nft.created_at = datetime.now().isoformat()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO nfts 
                (id, token_id, name, description, image_url, metadata, owner, contract_address, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                nft.id,
                nft.token_id,
                nft.name,
                nft.description,
                nft.image_url,
                json.dumps(nft.metadata),
                nft.owner,
                nft.contract_address,
                nft.created_at
            ))
            
            conn.commit()
            conn.close()
            
            self.nft_collection[nft_id] = nft
            
            # NFTミントトランザクション作成
            mint_transaction = BlockchainTransaction(
                from_address="0x0000000000000000000000000000000000000000",
                to_address=nft.owner,
                amount=0.0,
                transaction_type="nft_mint",
                data={"nft_id": nft_id, "token_id": nft.token_id},
                gas_fee=0.01
            )
            
            await self.create_transaction(mint_transaction)  # type: ignore
            
            self.logger.info(f"NFTミント: {nft_id} - {nft.name}")
            return {"status": "success", "nft_id": nft_id, "message": "NFTがミントされました"}

        @self.app.get("/api/blockchain/nfts", summary="NFT一覧")
        async def get_nfts(owner: Optional[str] = None, contract_address: Optional[str] = None):
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = "SELECT * FROM nfts WHERE 1=1"
            params = []
            
            if owner:
                query += " AND owner = ?"
                params.append(owner)
            
            if contract_address:
                query += " AND contract_address = ?"
                params.append(contract_address)
            
            query += " ORDER BY created_at DESC"
            
            cursor.execute(query, params)
            
            nfts = []
            for row in cursor.fetchall():
                nfts.append({
                    "id": row[0],
                    "token_id": row[1],
                    "name": row[2],
                    "description": row[3],
                    "image_url": row[4],
                    "metadata": json.loads(row[5]) if row[5] else {},
                    "owner": row[6],
                    "contract_address": row[7],
                    "created_at": row[8],
                    "last_transfer": row[9]
                })
            
            conn.close()
            return {"nfts": nfts, "count": len(nfts)}

        @self.app.get("/api/blockchain/metrics", summary="ブロックチェーンメトリクス")
        async def get_blockchain_metrics():
            return {
                "timestamp": datetime.now().isoformat(),
                "network_status": self.blockchain_network.status,
                "total_transactions": len(self.transaction_pool),
                "confirmed_transactions": len([t for t in self.transaction_pool if t.status == "confirmed"]),
                "pending_transactions": len([t for t in self.transaction_pool if t.status == "pending"]),
                "smart_contracts": len(self.smart_contracts),
                "deployed_contracts": len([c for c in self.smart_contracts.values() if c.status == "deployed"]),
                "nft_collection": len(self.nft_collection),
                "network_hash_rate": self.blockchain_network.hash_rate,
                "average_gas_price": self.blockchain_network.average_gas_price,
                "block_time": self.blockchain_network.block_time
            }

        @self.app.get("/", summary="ブロックチェーン統合ダッシュボード")
        async def blockchain_dashboard():
            return """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Mana Blockchain Integration System</title>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%); color: white; }
                    .container { max-width: 1400px; margin: 0 auto; }
                    .header { text-align: center; margin-bottom: 30px; }
                    .header h1 { font-size: 3em; margin: 0; text-shadow: 0 0 20px #00ff00; }
                    .header p { font-size: 1.3em; opacity: 0.9; }
                    .dashboard-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 30px; }
                    .card { background: rgba(0,255,0,0.1); border-radius: 15px; padding: 20px; backdrop-filter: blur(10px); border: 1px solid rgba(0,255,0,0.3); }
                    .card h3 { margin-top: 0; color: #00ff00; text-shadow: 0 0 10px #00ff00; }
                    .blockchain-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }
                    .blockchain-card { background: rgba(0,255,0,0.1); border-radius: 10px; padding: 15px; text-align: center; border: 1px solid rgba(0,255,0,0.3); }
                    .blockchain-card.confirmed { border-color: #00ff00; box-shadow: 0 0 15px rgba(0,255,0,0.5); }
                    .blockchain-card.pending { border-color: #ffff00; box-shadow: 0 0 15px rgba(255,255,0,0.5); }
                    .blockchain-card.failed { border-color: #ff0000; box-shadow: 0 0 15px rgba(255,0,0,0.5); }
                    .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; }
                    .stat-card { background: rgba(0,255,0,0.1); border-radius: 10px; padding: 15px; text-align: center; border: 1px solid rgba(0,255,0,0.3); }
                    .stat-number { font-size: 2em; font-weight: bold; color: #00ff00; text-shadow: 0 0 10px #00ff00; }
                    .stat-label { font-size: 0.9em; opacity: 0.9; margin-top: 5px; }
                    .action-btn { background: linear-gradient(45deg, #00ff00, #0080ff); color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-size: 16px; margin: 5px; }
                    .action-btn:hover { background: linear-gradient(45deg, #0080ff, #00ff00); }
                    .blockchain-animation { animation: blockchain-pulse 3s infinite; }
                    @keyframes blockchain-pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.7; } }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1 class="blockchain-animation">⛓️ Mana Blockchain Integration System</h1>
                        <p>ブロックチェーン統合・スマートコントラクト・NFT・DAOシステム</p>
                    </div>
                    
                    <div class="dashboard-grid">
                        <div class="card">
                            <h3>📊 ブロックチェーン概要</h3>
                            <div id="blockchain-overview"></div>
                        </div>
                        
                        <div class="card">
                            <h3>⚡ ネットワークメトリクス</h3>
                            <div id="network-metrics"></div>
                        </div>
                        
                        <div class="card">
                            <h3>🔗 スマートコントラクト</h3>
                            <div id="smart-contracts"></div>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h3>💎 NFTコレクション</h3>
                        <div class="blockchain-grid" id="nft-collection"></div>
                    </div>
                    
                    <div class="card">
                        <h3>🔄 トランザクション一覧</h3>
                        <div class="blockchain-grid" id="transactions-grid"></div>
                    </div>
                    
                    <div class="card">
                        <h3>🚀 ブロックチェーン操作</h3>
                        <div style="text-align: center;">
                            <button class="action-btn" onclick="createTransaction()">トランザクション作成</button>
                            <button class="action-btn" onclick="deployContract()">コントラクトデプロイ</button>
                            <button class="action-btn" onclick="mintNFT()">NFTミント</button>
                            <button class="action-btn" onclick="createDAO()">DAO作成</button>
                        </div>
                    </div>
                </div>
                
                <script>
                    async function refreshDashboard() {{
                        try {{
                            // ブロックチェーン概要取得
                            const statusResponse = await fetch('/api/status');
                            const statusData = await statusResponse.json();
                            
                            const blockchainOverview = document.getElementById('blockchain-overview');
                            blockchainOverview.innerHTML = `
                                <div class="stats-grid">
                                    <div class="stat-card">
                                        <div class="stat-number">${{statusData.total_transactions}}</div>
                                        <div class="stat-label">総トランザクション</div>
                                    </div>
                                    <div class="stat-card">
                                        <div class="stat-number">${{statusData.smart_contracts}}</div>
                                        <div class="stat-label">スマートコントラクト</div>
                                    </div>
                                    <div class="stat-card">
                                        <div class="stat-number">${{statusData.nft_collection}}</div>
                                        <div class="stat-label">NFTコレクション</div>
                                    </div>
                                </div>
                            `;
                            
                            // ネットワークメトリクス取得
                            const metricsResponse = await fetch('/api/blockchain/metrics');
                            const metricsData = await metricsResponse.json();
                            
                            const networkMetrics = document.getElementById('network-metrics');
                            networkMetrics.innerHTML = `
                                <div class="stats-grid">
                                    <div class="stat-card">
                                        <div class="stat-number">${{metricsData.network_hash_rate.toFixed(2)}} TH/s</div>
                                        <div class="stat-label">ハッシュレート</div>
                                    </div>
                                    <div class="stat-card">
                                        <div class="stat-number">${{metricsData.average_gas_price.toFixed(4)}} ETH</div>
                                        <div class="stat-label">平均ガス価格</div>
                                    </div>
                                    <div class="stat-card">
                                        <div class="stat-number">${{metricsData.block_time.toFixed(1)}}s</div>
                                        <div class="stat-label">ブロック時間</div>
                                    </div>
                                </div>
                            `;
                            
                            // スマートコントラクト取得
                            const contractsResponse = await fetch('/api/blockchain/smart-contracts');
                            const contractsData = await contractsResponse.json();
                            
                            const smartContracts = document.getElementById('smart-contracts');
                            smartContracts.innerHTML = `
                                <div class="stats-grid">
                                    <div class="stat-card">
                                        <div class="stat-number">${{contractsData.count}}</div>
                                        <div class="stat-label">総コントラクト</div>
                                    </div>
                                    <div class="stat-card">
                                        <div class="stat-number">${{contractsData.contracts.filter(c => c.status === 'deployed').length}}</div>
                                        <div class="stat-label">デプロイ済み</div>
                                    </div>
                                    <div class="stat-card">
                                        <div class="stat-number">${{contractsData.contracts.filter(c => c.status === 'active').length}}</div>
                                        <div class="stat-label">アクティブ</div>
                                    </div>
                                </div>
                            `;
                            
                            // NFTコレクション取得
                            const nftsResponse = await fetch('/api/blockchain/nfts');
                            const nftsData = await nftsResponse.json();
                            
                            const nftCollection = document.getElementById('nft-collection');
                            if (nftsData.nfts && nftsData.nfts.length > 0) {{
                                nftCollection.innerHTML = nftsData.nfts.slice(0, 12).map(nft => `
                                    <div class="blockchain-card">
                                        <div style="font-weight: bold; margin-bottom: 5px;">
                                            🎨 ${{nft.name}}
                                        </div>
                                        <div style="font-size: 0.8em; opacity: 0.8;">
                                            Token ID: ${{nft.token_id}}<br>
                                            Owner: ${{nft.owner.slice(0, 10)}}...<br>
                                            Contract: ${{nft.contract_address.slice(0, 10)}}...
                                        </div>
                                    </div>
                                `).join('');
                            }} else {{
                                nftCollection.innerHTML = '<div style="text-align: center; opacity: 0.7;">NFTはありません</div>';
                            }}
                            
                            // トランザクション一覧取得
                            const transactionsResponse = await fetch('/api/blockchain/transactions');
                            const transactionsData = await transactionsResponse.json();
                            
                            const transactionsGrid = document.getElementById('transactions-grid');
                            if (transactionsData.transactions && transactionsData.transactions.length > 0) {{
                                transactionsGrid.innerHTML = transactionsData.transactions.slice(0, 12).map(tx => {{
                                    const statusClass = tx.status;
                                    const statusIcon = tx.status === 'confirmed' ? '✅' : 
                                                     tx.status === 'pending' ? '⏳' : '❌';
                                    
                                    return `
                                        <div class="blockchain-card ${{statusClass}}">
                                            <div style="font-weight: bold; margin-bottom: 5px;">
                                                ${{statusIcon}} ${{tx.transaction_type.toUpperCase()}}
                                            </div>
                                            <div style="font-size: 0.8em; opacity: 0.8;">
                                                From: ${{tx.from_address.slice(0, 10)}}...<br>
                                                To: ${{tx.to_address.slice(0, 10)}}...<br>
                                                Amount: ${{tx.amount}} ETH<br>
                                                Gas: ${{tx.gas_fee}} ETH
                                            </div>
                                        </div>
                                    `;
                                }}).join('');
                            }} else {{
                                transactionsGrid.innerHTML = '<div style="text-align: center; opacity: 0.7;">トランザクションはありません</div>';
                            }}
                            
                        }} catch (error) {{
                            console.error('ダッシュボード更新エラー:', error);
                        }}
                    }}
                    
                    async function createTransaction() {{
                        const fromAddress = prompt('送信者アドレス:');
                        const toAddress = prompt('受信者アドレス:');
                        const amount = prompt('送金額 (ETH):');
                        const transactionType = prompt('トランザクションタイプ (data_transfer, smart_contract, nft_mint, token_transfer):');
                        
                        if (fromAddress && toAddress && amount && transactionType) {{
                            try {{
                                const response = await fetch('/api/blockchain/transaction', {{
                                    method: 'POST',
                                    headers: {{'Content-Type': 'application/json'}},
                                    body: JSON.stringify({{
                                        from_address: fromAddress,
                                        to_address: toAddress,
                                        amount: parseFloat(amount),
                                        transaction_type: transactionType,
                                        gas_fee: 0.001
                                    }})
                                }});
                                const result = await response.json();
                                alert('トランザクション作成: ' + result.message);
                                refreshDashboard();
                            }} catch (error) {{
                                console.error('トランザクション作成エラー:', error);
                            }}
                        }}
                    }}
                    
                    async function deployContract() {{
                        const name = prompt('コントラクト名:');
                        const contractType = prompt('コントラクトタイプ (automation, governance, token, nft, dao):');
                        const code = prompt('コントラクトコード (簡易):');
                        const owner = prompt('オーナーアドレス:');
                        
                        if (name && contractType && code && owner) {{
                            try {{
                                const response = await fetch('/api/blockchain/smart-contract', {{
                                    method: 'POST',
                                    headers: {{'Content-Type': 'application/json'}},
                                    body: JSON.stringify({{
                                        name: name,
                                        contract_type: contractType,
                                        code: code,
                                        owner: owner
                                    }})
                                }});
                                const result = await response.json();
                                alert('スマートコントラクト作成: ' + result.message);
                                refreshDashboard();
                            }} catch (error) {{
                                console.error('スマートコントラクト作成エラー:', error);
                            }}
                        }}
                    }}
                    
                    async function mintNFT() {{
                        const name = prompt('NFT名:');
                        const description = prompt('説明:');
                        const imageUrl = prompt('画像URL:');
                        const owner = prompt('オーナーアドレス:');
                        const contractAddress = prompt('コントラクトアドレス:');
                        
                        if (name && description && imageUrl && owner && contractAddress) {{
                            try {{
                                const response = await fetch('/api/blockchain/nft/mint', {{
                                    method: 'POST',
                                    headers: {{'Content-Type': 'application/json'}},
                                    body: JSON.stringify({{
                                        token_id: `nft_${{Date.now()}}`,
                                        name: name,
                                        description: description,
                                        image_url: imageUrl,
                                        owner: owner,
                                        contract_address: contractAddress
                                    }})
                                }});
                                const result = await response.json();
                                alert('NFTミント: ' + result.message);
                                refreshDashboard();
                            }} catch (error) {{
                                console.error('NFTミントエラー:', error);
                            }}
                        }}
                    }}
                    
                    async function createDAO() {{
                        alert('DAO作成機能は開発中です。スマートコントラクトとして実装予定。');
                    }}
                    
                    // 初期読み込み
                    refreshDashboard();
                    
                    // 30秒ごとに自動更新
                    setInterval(refreshDashboard, 30000);
                </script>
            </body>
            </html>
            """

    def setup_startup_events(self):
        @self.app.on_event("startup")
        async def startup_event():
            asyncio.create_task(self._blockchain_processor())
            asyncio.create_task(self._blockchain_miner())
            asyncio.create_task(self._blockchain_metrics_collector())
            self.logger.info("バックグラウンドタスク開始")

    async def validate_transaction(self, transaction: BlockchainTransaction) -> bool:
        """トランザクションを検証"""
        # 基本的な検証ロジック
        if transaction.amount < 0:
            return False
        if not transaction.from_address or not transaction.to_address:
            return False
        return True

    async def _blockchain_processor(self):
        """ブロックチェーンプロセッサー"""
        while True:
            try:
                await self.process_transactions()
                await asyncio.sleep(10)  # 10秒ごとに処理
            except Exception as e:
                self.logger.error(f"ブロックチェーンプロセッサーエラー: {e}")
                await asyncio.sleep(10)

    async def process_transactions(self):
        """トランザクションを処理"""
        for transaction in self.transaction_pool:
            if transaction.status == "pending":
                # トランザクションを確認
                transaction.status = "confirmed"
                transaction.confirmed_at = datetime.now().isoformat()
                transaction.block_hash = hashlib.sha256(f"{transaction.id}{time.time()}".encode()).hexdigest()
                
                # データベース更新
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE blockchain_transactions 
                    SET status = ?, confirmed_at = ?, block_hash = ?
                    WHERE id = ?
                """, (transaction.status, transaction.confirmed_at, transaction.block_hash, transaction.id))
                conn.commit()
                conn.close()
                
                self.logger.info(f"トランザクション確認: {transaction.id}")

    async def _blockchain_miner(self):
        """ブロックチェーンマイナー"""
        while True:
            try:
                await self.mine_block()
                await asyncio.sleep(30)  # 30秒ごとにマイニング
            except Exception as e:
                self.logger.error(f"ブロックチェーンマイナーエラー: {e}")
                await asyncio.sleep(30)

    async def mine_block(self):
        """ブロックをマイニング"""
        # 実際の実装では、Proof of WorkやProof of Stakeアルゴリズムを実装
        self.logger.info("ブロックマイニング実行")

    async def _blockchain_metrics_collector(self):
        """ブロックチェーンメトリクス収集器"""
        while True:
            try:
                await self.collect_blockchain_metrics()
                await asyncio.sleep(60)  # 1分ごとに収集
            except Exception as e:
                self.logger.error(f"ブロックチェーンメトリクス収集器エラー: {e}")
                await asyncio.sleep(60)

    async def collect_blockchain_metrics(self):
        """ブロックチェーンメトリクスを収集"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO blockchain_metrics 
            (timestamp, total_transactions, confirmed_transactions, pending_transactions, 
             total_contracts, active_contracts, total_nfts, network_hash_rate, average_gas_price, block_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            len(self.transaction_pool),
            len([t for t in self.transaction_pool if t.status == "confirmed"]),
            len([t for t in self.transaction_pool if t.status == "pending"]),
            len(self.smart_contracts),
            len([c for c in self.smart_contracts.values() if c.status == "deployed"]),
            len(self.nft_collection),
            self.blockchain_network.hash_rate,
            self.blockchain_network.average_gas_price,
            self.blockchain_network.block_time
        ))
        
        conn.commit()
        conn.close()

    def start_background_tasks(self):
        # バックグラウンドタスクはFastAPIのstartupイベントで開始
        self.logger.info("バックグラウンドタスク準備完了")

class BlockchainNetwork:
    def __init__(self):
        self.status = "active"
        self.hash_rate = 100.0  # TH/s
        self.average_gas_price = 0.0001  # ETH
        self.block_time = 15.0  # seconds
        self.blocks = []

    async def submit_transaction(self, transaction: BlockchainTransaction):
        """トランザクションをネットワークに送信"""
        self.logger.info(f"トランザクション送信: {transaction.id}")  # type: ignore

    async def deploy_contract(self, contract: SmartContract) -> str:
        """スマートコントラクトをデプロイ"""
        # 実際の実装では、ブロックチェーンネットワークにデプロイ
        deployed_address = f"0x{hashlib.sha256(f'{contract.id}{time.time()}'.encode()).hexdigest()[:40]}"
        return deployed_address

def main():
    system = ManaBlockchainIntegrationSystem()
    uvicorn.run(system.app, host="0.0.0.0", port=5035)

if __name__ == "__main__":
    main()
