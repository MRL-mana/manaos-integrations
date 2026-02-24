import argparse
import base64
import json
import os
import sys
import urllib.request
import urllib.error


def _read_image_b64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def ollama_chat_with_image(
    image_path: str,
    prompt: str,
    model: str = "llava:latest",
    host: str = "http://127.0.0.1:11434",
) -> str:
    url = host.rstrip("/") + "/api/chat"

    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {
                "role": "user",
                "content": prompt,
                "images": [_read_image_b64(image_path)],
            }
        ],
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
    )

    with urllib.request.urlopen(req, timeout=120) as resp:
        body = resp.read().decode("utf-8")

    obj = json.loads(body)
    msg = obj.get("message") or {}
    return (msg.get("content") or "").strip()


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Ask a vision model about an image via Ollama"
    )
    ap.add_argument("image", help="Path to image (png/jpg)")
    ap.add_argument("--prompt", default="この画像に何が写ってる？", help="Question/prompt")
    ap.add_argument(
        "--model",
        default=os.getenv("MANA_VISION_MODEL", "llava:latest"),
        help="Ollama model name",
    )
    ap.add_argument(
        "--host",
        default=os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434"),
        help="Ollama host",
    )

    args = ap.parse_args()

    if not os.path.exists(args.image):
        print(f"ERROR: image not found: {args.image}", file=sys.stderr)
        return 2

    try:
        answer = ollama_chat_with_image(
            args.image,
            args.prompt,
            model=args.model,
            host=args.host,
        )
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    print(answer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
