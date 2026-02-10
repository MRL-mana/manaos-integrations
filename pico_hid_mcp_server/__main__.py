"""Entry point for python -m pico_hid_mcp_server"""
import asyncio
from .server import main

if __name__ == "__main__":
    asyncio.run(main())
