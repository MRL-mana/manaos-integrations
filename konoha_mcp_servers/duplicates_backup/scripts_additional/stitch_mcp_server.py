#!/usr/bin/env python3
"""
Stitch MCP Server
Cursor から直接 Stitch を操作できる MCP サーバー
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("/root/logs/stitch_mcp.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class StitchMCPServer:
    def __init__(self):
        self.output_dir = Path("/root/stitch_outputs")
        self.output_dir.mkdir(exist_ok=True)
        self.browser = None
        self.context = None
        self.page = None
        self.p = None

    async def initialize(self):
        """ブラウザを初期化"""
        try:
            self.p = await async_playwright().start()
            self.browser = await self.p.chromium.launch(headless=True)
            self.context = await self.browser.new_context(
                viewport={"width": 1920, "height": 1080}
            )
            logger.info("✅ Stitch MCP Server initialized")
        except Exception as e:
            logger.error(f"❌ 初期化エラー: {e}")
            raise

    async def shutdown(self):
        """ブラウザを終了"""
        try:
            if self.browser:
                await self.browser.close()
            if self.p:
                await self.p.stop()
            logger.info("✅ Stitch MCP Server shutdown")
        except Exception as e:
            logger.error(f"❌ 終了エラー: {e}")

    async def generate_ui(self, prompt: str, design_type: str = "web") -> dict:
        """
        StitchでUIデザインを生成

        Args:
            prompt: UI生成の指示文
            design_type: "web" or "mobile"

        Returns:
            生成結果の辞書
        """
        logger.info(f"🎨 UI生成開始: {prompt}")

        try:
            page = await self.context.new_page()
            await page.goto("https://stitch.withgoogle.com", timeout=30000)
            await asyncio.sleep(2)

            prompt_input = None
            for selector in ["textarea", 'input[type="text"]', '[contenteditable="true"]']:
                try:
                    prompt_input = await page.wait_for_selector(selector, timeout=3000)
                    if prompt_input:
                        break
                except Exception:
                    continue

            if prompt_input:
                await prompt_input.fill(prompt)
                logger.info("✅ プロンプト入力完了")

            generate_btn = await page.query_selector('button:has-text("Generate")')
            if generate_btn:
                await generate_btn.click()
                logger.info("✅ 生成ボタンクリック")

            await asyncio.sleep(15)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = self.output_dir / f"stitch_{timestamp}.png"
            await page.screenshot(path=str(screenshot_path))

            result = {
                "prompt": prompt,
                "design_type": design_type,
                "screenshot": str(screenshot_path),
                "timestamp": timestamp,
            }

            output_file = self.output_dir / f"stitch_{timestamp}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            await page.close()

            logger.info(f"✅ デザイン生成完了: {output_file}")
            return result

        except Exception as e:
            logger.error(f"❌ 生成エラー: {e}")
            return {"error": str(e)}

    async def get_stitch_code(self, design_url: str) -> str:
        """
        生成されたデザインのコードを取得

        Args:
            design_url: StitchのデザインURL

        Returns:
            生成されたコード
        """
        logger.info(f"📝 コード取得開始: {design_url}")

        try:
            page = await self.context.new_page()
            await page.goto(design_url, timeout=30000)

            code_btn = await page.wait_for_selector('button:has-text("View code")', timeout=10000)
            await code_btn.click()

            code_element = await page.wait_for_selector('pre.code-block', timeout=10000)
            code = await code_element.text_content()

            await page.close()
            logger.info("✅ コード取得完了")
            return code or ""

        except Exception as e:
            logger.error(f"❌ コード取得エラー: {e}")
            return ""

    async def health_check(self) -> dict:
        """ヘルスチェック"""
        try:
            page = await self.context.new_page()
            await page.goto("https://stitch.withgoogle.com", timeout=30000)
            title = await page.title()
            await page.close()

            return {
                "status": "healthy",
                "stitch_accessible": True,
                "stitch_title": title,
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}


async def main():
    server = StitchMCPServer()

    try:
        await server.initialize()
        logger.info("🚀 Stitch MCP Server started")

        health = await server.health_check()
        logger.info(f"📊 Health: {health}")

        result = await server.generate_ui("シンプルなログインフォーム", "web")
        logger.info(f"🎨 サンプル生成: {result}")

        await asyncio.Event().wait()
    except asyncio.CancelledError:
        logger.info("🛑 Stitch MCP Server cancelled")
    finally:
        await server.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Keyboard interrupt received")
