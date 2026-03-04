"""
Grok Imagineから画像をダウンロードするスクリプト（対話型）
手動でサインインしてから画像をダウンロードできます
"""
import os
import requests
from playwright.sync_api import sync_playwright
import time
from pathlib import Path

def download_grok_images_interactive(output_dir="downloaded_grok_images"):
    """Grok Imagineから画像をダウンロード（対話型）"""
    # 出力ディレクトリを作成
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    browser = None
    try:
        with sync_playwright() as p:
            # ブラウザを起動（ヘッドレスモードをオフにして確認可能に）
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(viewport={"width": 1920, "height": 1080})
            page = context.new_page()
            
            # Grok Imagineにアクセス
            print("=" * 60)
            print("Grok Imagineにアクセス中...")
            print("=" * 60)
            page.goto("https://grok.com/imagine", wait_until="domcontentloaded", timeout=30000)
            
            print("\nブラウザが開きました。")
            print("1. 必要に応じてサインインしてください")
            print("2. 画像が表示されるまでページをスクロールしてください")
            print("3. 準備ができたら、このコンソールでEnterキーを押してください")
            print("\n（ブラウザは開いたままにしておいてください）\n")
            
            # ユーザーの入力を待つ
            input("Enterキーを押して続行...")
            
            # ページをスクロールして画像を読み込む
            print("\nページをスクロールして画像を読み込み中...")
            for i in range(5):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(2)
                page.evaluate("window.scrollTo(0, 0)")
                time.sleep(1)
            
            # ページのスクリーンショットを取得
            try:
                page.screenshot(path=str(output_path / "page_screenshot.png"), full_page=True)
                print(f"✓ ページスクリーンショットを保存: {output_path / 'page_screenshot.png'}")
            except Exception as e:
                print(f"スクリーンショット保存エラー: {e}")
            
            print(f"\nページタイトル: {page.title()}")
            print(f"現在のURL: {page.url}")
            
            # 画像要素を探す（複数の方法で）
            print("\n画像を検索中...")
            
            # 方法1: imgタグ
            images = page.query_selector_all("img")
            print(f"imgタグ: {len(images)}個")
            
            # 方法2: 背景画像
            bg_images = page.query_selector_all("[style*='background-image']")
            print(f"背景画像: {len(bg_images)}個")
            
            # 方法3: pictureタグ
            pictures = page.query_selector_all("picture img")
            print(f"pictureタグ: {len(pictures)}個")
            
            # 方法4: すべての画像URLを取得（JavaScript実行）
            print("\nJavaScriptで画像URLを取得中...")
            image_urls = page.evaluate("""
                () => {
                    const images = [];
                    document.querySelectorAll('img').forEach(img => {
                        if (img.src && !img.src.startsWith('data:')) {
                            images.push(img.src);
                        }
                    });
                    // 背景画像も取得
                    document.querySelectorAll('[style*="background-image"]').forEach(el => {
                        const style = window.getComputedStyle(el);
                        const bgImage = style.backgroundImage;
                        if (bgImage && bgImage !== 'none') {
                            const url = bgImage.match(/url\\(["']?([^"']+)["']?\\)/);
                            if (url && url[1] && !url[1].startsWith('data:')) {
                                images.push(url[1]);
                            }
                        }
                    });
                    return [...new Set(images)]; // 重複を除去
                }
            """)
            
            print(f"見つかった画像URL: {len(image_urls)}個")
            
            downloaded_count = 0
            failed_count = 0
            
            for i, url in enumerate(image_urls):
                try:
                    print(f"\n[{i+1}/{len(image_urls)}] ダウンロード中: {url[:80]}...")
                    
                    # 完全なURLを作成
                    if not url.startswith("http"):
                        if url.startswith("//"):
                            url = f"https:{url}"
                        elif url.startswith("/"):
                            url = f"https://grok.com{url}"
                        else:
                            url = f"https://grok.com/{url}"
                    
                    # 画像をダウンロード
                    try:
                        response = requests.get(url, timeout=15, headers={
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                            'Referer': 'https://grok.com/'
                        }, allow_redirects=True)
                        
                        if response.status_code == 200:
                            # Content-Typeから拡張子を推測
                            content_type = response.headers.get('Content-Type', '').lower()
                            ext = "png"
                            if 'jpeg' in content_type or '.jpg' in url.lower():
                                ext = "jpg"
                            elif 'webp' in content_type or '.webp' in url.lower():
                                ext = "webp"
                            elif 'gif' in content_type or '.gif' in url.lower():
                                ext = "gif"
                            elif '.png' in url.lower():
                                ext = "png"
                            
                            filename = output_path / f"grok_image_{downloaded_count+1:03d}.{ext}"
                            with open(filename, "wb") as f:
                                f.write(response.content)
                            
                            file_size = len(response.content) / 1024  # KB
                            print(f"  ✓ 保存完了: {filename.name} ({file_size:.1f} KB)")
                            downloaded_count += 1
                        else:
                            print(f"  ✗ ダウンロード失敗: HTTP {response.status_code}")
                            failed_count += 1
                    except requests.RequestException as e:
                        print(f"  ✗ リクエストエラー: {e}")
                        failed_count += 1
                        
                except Exception as e:
                    print(f"  ✗ エラー: {e}")
                    failed_count += 1
            
            print("\n" + "=" * 60)
            print(f"ダウンロード完了!")
            print(f"  成功: {downloaded_count} 枚")
            print(f"  失敗: {failed_count} 枚")
            print(f"保存先: {output_path.absolute()}")
            print("=" * 60)
            
            # ブラウザを少し開いたままにして確認できるように
            print("\nブラウザを10秒間開いたままにします（確認用）...")
            time.sleep(10)
            
    except KeyboardInterrupt:
        print("\n\nユーザーによって中断されました")
    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if browser:
            try:
                browser.close()
            except:
                pass

if __name__ == "__main__":
    download_grok_images_interactive()






