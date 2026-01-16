#!/bin/bash
# Stable Diffusion 専用プロンプターコマンド
# Uncensored Llama3モデルを使用して画像生成プロンプトを生成

MODEL_NAME="llama3-uncensored"
OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"

# 使用方法を表示
usage() {
    cat << EOF
使用方法: sd-prompt [オプション] <日本語の説明>

Stable Diffusion用の画像生成プロンプトを生成します。

オプション:
  -m, --model NAME     使用するモデル名（デフォルト: llama3-uncensored）
  -t, --temperature N  温度パラメータ（0.0-1.0、デフォルト: 0.9）
  -h, --help           このヘルプを表示

例:
  sd-prompt "猫がベッドで寝ている"
  sd-prompt "美しい夕日と海"
  sd-prompt -t 0.8 "宇宙船が星間空間を航行している"

EOF
}

# 引数解析
TEMPERATURE=0.9
PROMPT=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -m|--model)
            MODEL_NAME="$2"
            shift 2
            ;;
        -t|--temperature)
            TEMPERATURE="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        -*)
            echo "不明なオプション: $1"
            usage
            exit 1
            ;;
        *)
            if [ -z "$PROMPT" ]; then
                PROMPT="$1"
            else
                PROMPT="$PROMPT $1"
            fi
            shift
            ;;
    esac
done

# プロンプトが指定されていない場合
if [ -z "$PROMPT" ]; then
    echo "エラー: プロンプトを指定してください"
    usage
    exit 1
fi

# Ollamaサービスが起動しているか確認
if ! curl -s "$OLLAMA_URL/api/tags" > /dev/null 2>&1; then
    echo "エラー: Ollamaサービスに接続できません ($OLLAMA_URL)"
    echo "Ollamaが起動しているか確認してください: ollama serve"
    exit 1
fi

# モデルが存在するか確認（オプション）
if ! curl -s "$OLLAMA_URL/api/show" -d "{\"name\":\"$MODEL_NAME\"}" > /dev/null 2>&1; then
    echo "警告: モデル '$MODEL_NAME' が見つかりません"
    echo "モデルを作成するには: ollama create $MODEL_NAME -f Modelfile.llama3-uncensored"
    echo "続行しますか？ (y/N)"
    read -r answer
    if [ "$answer" != "y" ] && [ "$answer" != "Y" ]; then
        exit 1
    fi
fi

# プロンプト生成のリクエストを作成
SYSTEM_PROMPT="You are an expert at creating detailed prompts for Stable Diffusion image generation. Convert the following Japanese description into a detailed, descriptive English prompt suitable for Stable Diffusion. Include style, composition, lighting, and other relevant details. Output only the prompt, no explanations."

USER_INPUT="$PROMPT"

# Ollama APIを呼び出し
echo "プロンプトを生成中..."
echo ""

RESPONSE=$(curl -s "$OLLAMA_URL/api/generate" \
    -H "Content-Type: application/json" \
    -d "{
        \"model\": \"$MODEL_NAME\",
        \"prompt\": \"$SYSTEM_PROMPT\n\nJapanese description: $USER_INPUT\n\nEnglish prompt for Stable Diffusion:\",
        \"stream\": false,
        \"options\": {
            \"temperature\": $TEMPERATURE,
            \"top_p\": 0.95,
            \"top_k\": 40
        }
    }")

# エラーチェック
if [ $? -ne 0 ]; then
    echo "エラー: Ollama APIの呼び出しに失敗しました"
    exit 1
fi

# レスポンスからプロンプトを抽出
# jqが利用可能な場合は優先的に使用
if command -v jq &> /dev/null; then
    GENERATED_PROMPT=$(echo "$RESPONSE" | jq -r '.response // empty' 2>/dev/null)
else
    # jqが利用できない場合、grepとsedで抽出を試みる
    GENERATED_PROMPT=$(echo "$RESPONSE" | grep -o '"response":"[^"]*"' | sed 's/"response":"//;s/"$//' | tail -1)
    
    # 抽出に失敗した場合
    if [ -z "$GENERATED_PROMPT" ]; then
        echo "エラー: レスポンスの解析に失敗しました"
        echo ""
        echo "jqをインストールすることを推奨します:"
        echo "  Ubuntu/Debian: sudo apt-get install jq"
        echo "  macOS: brew install jq"
        echo ""
        echo "レスポンス: $RESPONSE"
        exit 1
    fi
fi

# 空の場合のチェック
if [ -z "$GENERATED_PROMPT" ]; then
    echo "エラー: プロンプトの生成に失敗しました"
    echo "レスポンス: $RESPONSE"
    exit 1
fi

# 結果を表示
echo "=========================================="
echo "生成されたプロンプト:"
echo "=========================================="
echo ""
echo "$GENERATED_PROMPT"
echo ""
echo "=========================================="
echo ""

# クリップボードにコピー（利用可能な場合）
if command -v xclip &> /dev/null; then
    echo "$GENERATED_PROMPT" | xclip -selection clipboard
    echo "✓ クリップボードにコピーしました (xclip)"
elif command -v wl-copy &> /dev/null; then
    echo "$GENERATED_PROMPT" | wl-copy
    echo "✓ クリップボードにコピーしました (wl-copy)"
elif command -v pbcopy &> /dev/null; then
    echo "$GENERATED_PROMPT" | pbcopy
    echo "✓ クリップボードにコピーしました (pbcopy)"
fi
