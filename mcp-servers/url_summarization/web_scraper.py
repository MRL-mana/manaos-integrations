#!/usr/bin/env python3
"""
Webスクレイピングモジュール
Webページからテキストを抽出
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import re
from typing import Dict


class WebScraper:
    """Webページスクレイピング"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    
    def scrape(self, url: str) -> Dict:
        """Webページをスクレイピング"""
        try:
            # URL検証
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return {"success": False, "error": "無効なURL"}
            
            # リクエスト送信
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            
            # HTML解析
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 不要なタグを削除
            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe']):
                tag.decompose()
            
            # タイトル取得
            title = self._get_title(soup)
            
            # 本文取得
            content = self._get_content(soup)
            
            # メタ情報取得
            meta = self._get_meta(soup)
            
            # 画像URL取得
            images = self._get_images(soup, url)
            
            return {
                "success": True,
                "url": url,
                "title": title,
                "content": content,
                "meta": meta,
                "images": images,
                "word_count": len(content.split())
            }
        
        except requests.RequestException as e:
            return {"success": False, "error": f"リクエストエラー: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": f"スクレイピングエラー: {str(e)}"}
    
    def _get_title(self, soup: BeautifulSoup) -> str:
        """タイトル取得"""
        # Open Graph
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            return og_title['content']
        
        # Twitter Card
        twitter_title = soup.find('meta', attrs={'name': 'twitter:title'})
        if twitter_title and twitter_title.get('content'):
            return twitter_title['content']
        
        # HTML title
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.get_text().strip()
        
        # h1
        h1 = soup.find('h1')
        if h1:
            return h1.get_text().strip()
        
        return "タイトルなし"
    
    def _get_content(self, soup: BeautifulSoup) -> str:
        """本文取得"""
        # メインコンテンツを探す
        main_content = None
        
        # articleタグ
        article = soup.find('article')
        if article:
            main_content = article
        
        # mainタグ
        if not main_content:
            main_tag = soup.find('main')
            if main_tag:
                main_content = main_tag
        
        # クラス名で探す
        if not main_content:
            for class_name in ['content', 'post', 'entry', 'article-content', 'main-content']:
                main_content = soup.find(class_=class_name)
                if main_content:
                    break
        
        # 見つからない場合はbody全体
        if not main_content:
            main_content = soup.find('body')
        
        if main_content:
            # テキスト抽出
            text = main_content.get_text(separator='\n', strip=True)
            # 余分な改行を削除
            text = re.sub(r'\n{3,}', '\n\n', text)
            return text.strip()
        
        return ""
    
    def _get_meta(self, soup: BeautifulSoup) -> Dict:
        """メタ情報取得"""
        meta = {}
        
        # 説明
        og_desc = soup.find('meta', property='og:description')
        if og_desc and og_desc.get('content'):
            meta['description'] = og_desc['content']
        else:
            desc = soup.find('meta', attrs={'name': 'description'})
            if desc and desc.get('content'):
                meta['description'] = desc['content']
        
        # 著者
        author = soup.find('meta', attrs={'name': 'author'})
        if author and author.get('content'):
            meta['author'] = author['content']
        
        # 公開日
        pub_date = soup.find('meta', property='article:published_time')
        if pub_date and pub_date.get('content'):
            meta['published_time'] = pub_date['content']
        
        return meta
    
    def _get_images(self, soup: BeautifulSoup, base_url: str) -> list:
        """画像URL取得"""
        images = []
        
        # imgタグ
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src')
            if src:
                # 相対URLを絶対URLに変換
                if src.startswith('//'):
                    src = 'https:' + src
                elif src.startswith('/'):
                    parsed = urlparse(base_url)
                    src = f"{parsed.scheme}://{parsed.netloc}{src}"
                
                images.append(src)
        
        # Open Graph画像
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            images.insert(0, og_image['content'])
        
        return images[:10]  # 最大10枚


