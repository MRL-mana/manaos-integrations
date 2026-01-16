
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path.cwd()))

from obsidian_integration import ObsidianIntegration

def debug_read():
    print("Debug: Direct Obsidian Access Check")
    print("=" * 50)
    
    # 1. Initialize Obsidian Integration
    vault_path = os.getenv("OBSIDIAN_VAULT_PATH", "C:/Users/mana4/Documents/Obsidian Vault")
    print(f"Vault Path: {vault_path}")
    
    obsidian = ObsidianIntegration(vault_path)
    print(f"Is Available: {obsidian.is_available()}")
    
    if not obsidian.is_available():
        print("Obsidian not available. Aborting.")
        return

    # 2. Search for the note
    query = "Verification"
    print(f"\nSearching for '{query}'...")
    results = obsidian.search_notes(query)
    print(f"Found {len(results)} results (Paths):")
    for p in results:
        print(f" - {p}")
        
    # 3. Read the first result
    if results:
        target_path = results[0]
        print(f"\nAttempting to read: {target_path}")
        
        # Note: read_note expects a relative path or filename usually? 
        # let's check what read_note expects by trying relative path from vault
        try:
            rel_path = target_path.relative_to(Path(vault_path))
            print(f"Relative path: {rel_path}")
            content = obsidian.read_note(str(rel_path))
            print("\n--- CONTENT START ---")
            print(content[:200] + "..." if content and len(content) > 200 else content)
            print("--- CONTENT END ---")
        except Exception as e:
            print(f"Error reading note: {e}")
            # Try reading directly with python open just in case read_note is buggy
            try:
                print("Trying direct open()...")
                with open(target_path, 'r', encoding='utf-8') as f:
                    print(f.read()[:200])
            except Exception as e2:
                print(f"Direct open failed too: {e2}")

if __name__ == "__main__":
    debug_read()
