import sys, os
os.chdir(r"C:\Users\mana4\Desktop\manaos_integrations")
sys.path.insert(0, r"C:\Users\mana4\Desktop\manaos_integrations\llm")

import always_ready_llm_client
print("file:", always_ready_llm_client.__file__)
print("has LLMResponse:", hasattr(always_ready_llm_client, "LLMResponse"))

try:
    from always_ready_llm_client import LLMResponse
    print("import LLMResponse: OK")
except ImportError as e:
    print("import LLMResponse: FAIL", e)

# now check the chain
try:
    from always_ready_llm_integrated import LLMResponse as LR2
    print("import from integrated: OK")
except Exception as e:
    print("import from integrated: FAIL", e)

try:
    from always_ready_llm_ultra_integrated import UltraIntegratedLLMClient
    print("import UltraIntegratedLLMClient: OK")
except Exception as e:
    print("import UltraIntegratedLLMClient: FAIL", e)
