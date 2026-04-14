#!/usr/bin/env python3
"""
Entropy Janitor (Garbage Collector)
Version: 1.0.0
Purpose: Detect documentation drift and context rot.
"""

import sys
from pathlib import Path


def check_schema_drift():
    """Very basic check for model vs schema documentation sync."""
    print("--- 🔍 Checking Schema Drift ---")
    models_file = Path("deals/models.py")  # Example model
    schema_doc = Path("docs/schema.md")

    if not models_file.exists() or not schema_doc.exists():
        print("[SKIP] Models or Schema doc missing.")
        return True

    mtime_models = models_file.stat().st_mtime
    mtime_schema = schema_doc.stat().st_mtime

    if mtime_models > mtime_schema:
        print("[FAIL] Schema documentation (docs/schema.md) is older than models.py!")
        print("   >> ACTION: Run Documenter agent to sync docs.")
        return False
    else:
        print("[OK] Schema doc seems up to date.")
    return True


def check_todo_emptiness():
    """Ensure AGENTS.md doesn't have hanging empty sections."""
    print("\n--- 📝 Checking AGENTS.md Hygiene ---")
    agents_file = Path("AGENTS.md")
    if not agents_file.exists():
        return True

    content = agents_file.read_text(encoding="utf-8")
    if "TODO" in content and "- [ ] " not in content:
        print("[WARN] AGENTS.md has a TODO section but no active items.")
        return False
    print("[OK] AGENTS.md is clean.")
    return True


def main():
    print("=== [Entropy Janitor] Maintenance Scan ===\n")
    success = True

    if not check_schema_drift():
        success = False

    if not check_todo_emptiness():
        # Only a warning for now
        pass

    print("\n===========================================")
    if success:
        print("✅ CLEANUP PASS: No significant drift detected.")
        sys.exit(0)
    else:
        print("⚠️ DRIFT DETECTED: Documentation out of sync.")
        sys.exit(0)  # Don't block yet, just warn


if __name__ == "__main__":
    main()
