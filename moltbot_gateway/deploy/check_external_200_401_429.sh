#!/bin/bash
# 母艦で実行: 外から 200 / 401 / 429 を一発で取る
# 使い方: DOMAIN=mrl-mana.com USER=mana PASS=xxx ./check_external_200_401_429.sh

DOMAIN="${MOLTBOT_CHECK_DOMAIN:-$DOMAIN}"
USER="${MOLTBOT_CHECK_USER:-$USER}"
PASS="${MOLTBOT_CHECK_PASS:-$PASS}"

if [ -z "$DOMAIN" ]; then
  echo "Usage: DOMAIN=mrl-mana.com USER=mana PASS=xxx $0"
  exit 1
fi

BASE="https://$DOMAIN/moltbot"

echo "=== ① 200 (health, no auth) ==="
curl -I -s "$BASE/health" | head -n 1

echo ""
echo "=== ② 401 (/moltbot/ without auth) ==="
curl -I -s -o /dev/null -w "%{http_code}\n" "$BASE/"

echo ""
echo "=== ③ 429 (rate limit, with auth, 30 hits) ==="
if [ -z "$USER" ] || [ -z "$PASS" ]; then
  echo "Skip (set USER and PASS for 429 check)"
else
  for i in $(seq 1 30); do
    curl -s -o /dev/null -u "$USER:$PASS" -w "%{http_code}\n" "$BASE/"
  done | sort | uniq -c
fi

echo ""
echo "--- 上の結果をそのまま貼ればOK ---"
