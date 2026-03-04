"""
Grok Imagineから画像をダウンロードするスクリプト（自動版）
ブラウザを開いて、一定時間待機後に自動で画像をダウンロードします
"""
import os
import requests
from playwright.sync_api import sync_playwright
import time
from pathlib import Path

def download_grok_images_auto(output_dir="downloaded_grok_images", wait_time=30):
    """Grok Imagineから画像をダウンロード（自動版）"""
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
            
            print(f"\nブラウザが開きました。")
            print(f"{wait_time}秒間待機します。")
            print("この間に以下を行ってください:")
            print("  1. Cloudflareの検証を完了")
            print("  2. 必要に応じてサインイン")
            print("  3. 画像が表示されるまでページをスクロール")
            print(f"\n{wait_time}秒後に自動的に画像をダウンロードします...\n")
            
            # 待機中に少しずつスクロール
            for i in range(wait_time // 5):
                time.sleep(5)
                try:
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    print(f"  スクロール中... ({i+1}/{wait_time//5})")
                except:
                    pass
            
            print("\n画像を検索中...")
            
            # ページをさらにスクロールして画像を読み込む
            for i in range(3):
                try:
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(2)
                    page.evaluate("window.scrollTo(0, 0)")
                    time.sleep(1)
                except:
                    pass
            
            # ページのスクリーンショットを取得
            try:
                page.screenshot(path=str(output_path / "page_screenshot.png"), full_page=True)
                print(f"✓ ページスクリーンショットを保存: {output_path / 'page_screenshot.png'}")
            except Exception as e:
                print(f"スクリーンショット保存エラー: {e}")
            
            print(f"\nページタイトル: {page.title()}")
            print(f"現在のURL: {page.url}")
            
            # JavaScriptで画像URLを取得
            print("\nJavaScriptで画像URLを取得中...")
            image_urls = page.evaluate("""
                () => {
                    const images = [];
                    // imgタグから取得
                    document.querySelectorAll('img').forEach(img => {
                        if (img.src && !img.src.startsWith('data:')) {
                            images.push({
                                url: img.src,
                                type: 'img'
                            });
                        }
                    });
                    // 背景画像も取得
                    document.querySelectorAll('[style*="background-image"], [class*="image"], [class*="img"]').forEach(el => {
                        try {
                            const style = window.getComputedStyle(el);
                            const bgImage = style.backgroundImage;
                            if (bgImage && bgImage !== 'none') {
                                const url = bgImage.match(/url\\(["']?([^"']+)["']?\\)/);
                                if (url && url[1] && !url[1].startsWith('data:')) {
                                    images.push({
                                        url: url[1],
                                        type: 'background'
                                    });
                                }
                            }
                        } catch(e) {}
                    });
                    // 重複を除去
                    const uniqueUrls = [...new Set(images.map(i => i.url))];
                    return uniqueUrls;
                }
            """)
            
            print(f"見つかった画像URL: {len(image_urls)}個")
            
            if len(image_urls) == 0:
                print("\n⚠ 画像が見つかりませんでした。")
                print("以下の可能性があります:")
                print("  - サインインが必要")
                print("  - ページの読み込みが完了していない")
                print("  - 画像が動的に読み込まれる")
                print("\nスクリーンショットを確認してください: downloaded_grok_images/page_screenshot.png")
            
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
                            'Referer': 'https://grok.com/',
                            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8'
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
    # 待機時間を秒で指定（デフォルト30秒）
    download_grok_images_auto(wait_time=30)






