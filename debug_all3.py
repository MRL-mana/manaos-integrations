"""auto_reflection_improvement test_statistics の失敗原因を調査"""
import subprocess, sys, os, json
os.chdir(r"C:\Users\mana4\Desktop\manaos_integrations")

# 1. Find auto_reflection_improvement
import glob
hits = glob.glob(r"C:\Users\mana4\Desktop\manaos_integrations\**\auto_reflection_improvement*", recursive=True)
print("Found files:", hits)

# 2. Try importing it
sys.path.insert(0, r"C:\Users\mana4\Desktop\manaos_integrations\scripts\misc")
sys.path.insert(0, r"C:\Users\mana4\Desktop\manaos_integrations\archive\legacy_improved")
sys.path.insert(0, r"C:\Users\mana4\Desktop\manaos_integrations")
try:
    m = __import__("auto_reflection_improvement", fromlist=["*"])
    print("Module file:", m.__file__)
    rs = m.get_auto_reflection_system()
    print("reflection_system:", rs)
    stats = rs.get_statistics()
    print("stats:", stats)
    print("total_evaluations" in stats, "average_score" in stats)
except Exception as e:
    print("Error:", e)

# 3. debug: check the always_ready_llm_client
venv_python = r"C:\Users\mana4\Desktop\.venv\Scripts\python.exe"
res = subprocess.run(
    [venv_python, "-c",
     "import sys; sys.path.insert(0, 'llm'); import always_ready_llm_client; print(always_ready_llm_client.__file__); print(hasattr(always_ready_llm_client, 'LLMResponse'))"],
    capture_output=True, text=True, cwd=r"C:\Users\mana4\Desktop\manaos_integrations"
)
print("\nalways_ready_llm_client check:\n", res.stdout, res.stderr)

# 4. debug drive_integration
res2 = subprocess.run(
    [venv_python, "-c", """
import sys
sys.path.insert(0, 'file_secretary')
sys.path.insert(0, 'scripts/misc')
from file_secretary_drive_indexer import GoogleDriveIndexer
from file_secretary_db import FileSecretaryDB
db = FileSecretaryDB('file_secretary_test.db')
indexer = GoogleDriveIndexer(db, drive_folder_name='INBOX')
print('drive_integration:', indexer.drive_integration)
print('has is_available:', hasattr(indexer.drive_integration, 'is_available'))
db.close()
"""],
    capture_output=True, text=True, cwd=r"C:\Users\mana4\Desktop\manaos_integrations"
)
print("\ndrive_integration check:\n", res2.stdout, res2.stderr[-500:])
