#!/usr/bin/env python3
"""
Instagram処理モジュール
投稿取得、プロフィール情報取得
"""

import re
import time
from typing import Dict, Optional
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup


class InstagramHandler:
    """Instagram処理"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.driver = None

    def _init_driver(self, headless: bool = True):
        """Seleniumドライバー初期化"""
        if self.driver:
            return self.driver

        chrome_options = Options()
        if headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            return self.driver
        except Exception as e:
            print(f"⚠️ Seleniumドライバー初期化エラー: {e}")
            print("💡 Playwrightを使用するか、ChromeDriverをインストールしてください")
            return None

    def get_post(self, url: str, use_selenium: bool = False) -> Dict:
        """投稿取得"""
        try:
            # URL検証
            parsed_url = self._parse_instagram_url(url)
            if not parsed_url:
                return {"success": False, "error": "無効なInstagram URL"}

            post_id = parsed_url.get('post_id')
            username = parsed_url.get('username')

            if use_selenium:
                return self._get_post_selenium(url)
            else:
                return self._get_post_requests(url, post_id, username)  # type: ignore

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get_post_requests(self, url: str, post_id: str, username: str) -> Dict:
        """requestsを使用した投稿取得（簡易版）"""
        try:
            # Instagramの公開投稿はJavaScriptで動的に読み込まれるため、
            # 基本的な情報のみ取得
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # メタ情報から基本情報を抽出
            title_tag = soup.find('title')
            title = title_tag.text if title_tag else f"{username}の投稿"

            # 説明文（メタディスクリプション）
            desc_tag = soup.find('meta', attrs={'property': 'og:description'})
            description = desc_tag.get('content', '') if desc_tag else ''

            # 画像URL
            image_tag = soup.find('meta', attrs={'property': 'og:image'})
            image_url = image_tag.get('content', '') if image_tag else ''

            return {
                "success": True,
                "post": {
                    "id": post_id,
                    "username": username,
                    "url": url,
                    "title": title,
                    "description": description,
                    "image_url": image_url,
                    "method": "requests (basic)"
                }
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get_post_selenium(self, url: str) -> Dict:
        """Seleniumを使用した投稿取得（詳細版）"""
        driver = self._init_driver()
        if not driver:
            return {"success": False, "error": "Seleniumドライバー初期化失敗"}

        try:
            driver.get(url)
            time.sleep(3)  # ページ読み込み待機

            # 投稿情報取得
            post_data = {
                "url": url,
                "method": "selenium (detailed)"
            }

            # ユーザー名取得
            try:
                username_elem = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href*="/"]'))
                )
                post_data["username"] = username_elem.text or ""
            except Exception:
                pass

            # 投稿キャプション取得
            try:
                caption_elem = driver.find_element(By.CSS_SELECTOR, 'h1, [data-testid="post-caption"]')
                post_data["caption"] = caption_elem.text
            except Exception:
                try:
                    # 代替セレクタ
                    caption_elem = driver.find_element(By.CSS_SELECTOR, 'span[dir="auto"]')
                    post_data["caption"] = caption_elem.text
                except Exception:
                    post_data["caption"] = ""

            # いいね数取得
            try:
                like_elem = driver.find_element(By.CSS_SELECTOR, 'button span, [aria-label*="いいね"]')
                post_data["likes"] = like_elem.text or "0"
            except Exception:
                post_data["likes"] = "0"

            # コメント数取得
            try:
                comment_elem = driver.find_element(By.CSS_SELECTOR, '[aria-label*="コメント"]')
                post_data["comments"] = comment_elem.text or "0"
            except Exception:
                post_data["comments"] = "0"

            # 画像URL取得
            try:
                img_elem = driver.find_element(By.CSS_SELECTOR, 'img[srcset], img[src]')
                post_data["image_url"] = img_elem.get_attribute('src') or img_elem.get_attribute('srcset', '').split()[0] if img_elem.get_attribute('srcset') else ""
            except Exception:
                post_data["image_url"] = ""

            return {
                "success": True,
                "post": post_data
            }

        except Exception as e:
            return {"success": False, "error": f"Selenium取得エラー: {str(e)}"}
        finally:
            # ドライバーは再利用のため閉じない
            pass

    def get_profile(self, username: str, use_selenium: bool = False) -> Dict:
        """プロフィール情報取得"""
        try:
            url = f"https://www.instagram.com/{username}/"

            if use_selenium:
                return self._get_profile_selenium(url, username)
            else:
                return self._get_profile_requests(url, username)

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get_profile_requests(self, url: str, username: str) -> Dict:
        """requestsを使用したプロフィール取得（簡易版）"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # メタ情報から基本情報を抽出
            title_tag = soup.find('title')
            title = title_tag.text if title_tag else f"{username} (@{username})"

            return {
                "success": True,
                "profile": {
                    "username": username,
                    "url": url,
                    "title": title,
                    "method": "requests (basic)"
                }
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get_profile_selenium(self, url: str, username: str) -> Dict:
        """Seleniumを使用したプロフィール取得（詳細版）"""
        driver = self._init_driver()
        if not driver:
            return {"success": False, "error": "Seleniumドライバー初期化失敗"}

        try:
            driver.get(url)
            time.sleep(3)

            profile_data = {
                "username": username,
                "url": url,
                "method": "selenium (detailed)"
            }

            # 投稿数、フォロワー数、フォロー数取得
            try:
                stats_elems = driver.find_elements(By.CSS_SELECTOR, 'span[title], li')
                for elem in stats_elems[:3]:
                    text = elem.text
                    if '投稿' in text or 'posts' in text.lower():
                        profile_data["posts_count"] = text
                    elif 'フォロワー' in text or 'followers' in text.lower():
                        profile_data["followers_count"] = text
                    elif 'フォロー中' in text or 'following' in text.lower():
                        profile_data["following_count"] = text
            except IOError:
                pass

            # プロフィール説明
            try:
                bio_elem = driver.find_element(By.CSS_SELECTOR, 'h1, [data-testid="profile-bio"]')
                profile_data["bio"] = bio_elem.text
            except IOError:
                profile_data["bio"] = ""

            return {
                "success": True,
                "profile": profile_data
            }

        except Exception as e:
            return {"success": False, "error": f"Selenium取得エラー: {str(e)}"}

    def _parse_instagram_url(self, url: str) -> Optional[Dict]:
        """Instagram URL解析"""
        # 例: https://www.instagram.com/p/ABC123/
        # 例: https://www.instagram.com/reel/ABC123/
        # 例: https://www.instagram.com/username/

        patterns = [
            r'instagram\.com/p/([^/?]+)',
            r'instagram\.com/reel/([^/?]+)',
            r'instagram\.com/([^/?]+)/$'
        ]

        for pattern in patterns[:2]:  # 投稿パターン
            match = re.search(pattern, url)
            if match:
                return {
                    "type": "post",
                    "post_id": match.group(1),
                    "username": None
                }

        # プロフィールパターン
        profile_match = re.search(r'instagram\.com/([^/?]+)/?$', url)
        if profile_match and profile_match.group(1) not in ['p', 'reel', 'explore', 'accounts']:
            return {
                "type": "profile",
                "username": profile_match.group(1),
                "post_id": None
            }

        return None

    def close(self):
        """リソース解放"""
        if self.driver:
            self.driver.quit()
            self.driver = None










