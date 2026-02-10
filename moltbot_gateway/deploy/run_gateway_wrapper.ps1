Set-Location 'C:\Users\mana4\Desktop\manaos_integrations'
$env:MOLTBOT_GATEWAY_DATA_DIR = 'C:\Users\mana4\Desktop\manaos_integrations\moltbot_gateway_data'
$env:MOLTBOT_GATEWAY_SECRET = 'local_secret'
$env:EXECUTOR = 'mock'
python -m uvicorn moltbot_gateway.gateway_app:app --host 127.0.0.1 --port 8088
