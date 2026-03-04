#!/usr/bin/env python3
"""slack_llm_integration を port 5115 で起動するラッパー"""
import os
import sys

# パス追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "slack_integration"))

import slack_llm_integration  # noqa: E402

port = int(os.getenv("SLACK_LLM_PORT", "5115"))
slack_llm_integration.app.run(host="0.0.0.0", port=port, debug=False)
