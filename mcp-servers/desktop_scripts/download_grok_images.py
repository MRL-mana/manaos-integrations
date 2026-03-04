"""
Grok Imagineから画像をダウンロードするスクリプト
"""
import os
import requests
from playwright.sync_api import sync_playwright
import time
from pathlib import Path

def download_grok_images(output_dir="downloaded_grok_images"):
    """Grok Imagineから画像をダウンロード"""
    # 出力ディレクトリを作成
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    browser = None
    try:
        with sync_playwright() as p:
            # ブラウザを起動（ヘッドレスモードをオフにして確認可能に）
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()
            
            # Grok Imagineにアクセス
            print("Grok Imagineにアクセス中...")
            page.goto("https://grok.com/imagine", wait_until="domcontentloaded", timeout=30000)
            time.sleep(5)  # ページの読み込みを待つ
            
            # ページのスクリーンショットを取得（デバッグ用）
            try:
                page.screenshot(path=str(output_path / "page_screenshot.png"), full_page=True)
                print(f"ページスクリーンショットを保存: {output_path / 'page_screenshot.png'}")
            except Exception as e:
                print(f"スクリーンショット保存エラー（無視）: {e}")
            
            # ページのHTMLを取得して確認
            html_content = page.content()
            print(f"ページタイトル: {page.title()}")
            
            # 画像要素を探す
            images = page.query_selector_all("img")
            print(f"見つかった画像数: {len(images)}")
            
            # 背景画像なども探す
            all_images = page.query_selector_all("[style*='background-image'], img")
            print(f"背景画像を含む要素数: {len(all_images)}")
            
            downloaded_count = 0
            seen_urls = set()  # 重複を避ける
            
            for i, img in enumerate(images):
                try:
                    # 画像のsrc属性を取得
                    src = img.get_attribute("src")
                    if not src or src in seen_urls:
                        continue
                    
                    # データURLの場合はスキップ
                    if src.startswith("data:"):
                        continue
                    
                    seen_urls.add(src)
                    
                    # 完全なURLを作成
                    if src.startswith("http"):
                        url = src
                    else:
                        url = f"https://grok.com{src}" if src.startswith("/") else f"https://grok.com/{src}"
                    
                    print(f"画像 {i+1} をダウンロード中: {url[:80]}...")
                    
                    # 画像をダウンロード
                    try:
                        response = requests.get(url, timeout=10, headers={
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                        })
                        if response.status_code == 200:
                            # Content-Typeから拡張子を推測
                            content_type = response.headers.get('Content-Type', '')
                            ext = "png"
                            if 'jpeg' in content_type or '.jpg' in url.lower():
                                ext = "jpg"
                            elif 'webp' in content_type or '.webp' in url.lower():
                                ext = "webp"
                            elif '.png' in url.lower():
                                ext = "png"
                            
                            filename = output_path / f"grok_image_{downloaded_count+1:03d}.{ext}"
                            with open(filename, "wb") as f:
                                f.write(response.content)
                            print(f"  ✓ 保存完了: {filename.name} ({len(response.content)} bytes)")
                            downloaded_count += 1
                        else:
                            print(f"  ✗ ダウンロード失敗: HTTP {response.status_code}")
                    except requests.RequestException as e:
                        print(f"  ✗ リクエストエラー: {e}")
                        
                except Exception as e:
                    print(f"  ✗ エラー: {e}")
                    continue
            
            print(f"\n合計 {downloaded_count} 枚の画像をダウンロードしました")
            print(f"保存先: {output_path.absolute()}")
            
            # ブラウザを少し開いたままにして確認できるように
            print("\nブラウザを15秒間開いたままにします（確認用）...")
            time.sleep(15)
            
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if browser:
            try:
                browser.close()
            except:
                pass

if __name__ == "__main__":
    download_grok_images()

