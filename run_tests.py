#!/usr/bin/env python3
"""ATES FAM Fitness automated test runner.

Runs all unit, accessibility (WCAG), and Streamlit AppTest functional tests across
the tests/ directory.
"""
import glob
import importlib
import inspect
import os
import sys

# Ensure workspace root is in sys.path
WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)


def main():
    test_files = sorted(glob.glob(os.path.join(WORKSPACE_DIR, "tests", "test_*.py")))
    passed, failed = 0, 0
    failures = []

    print(f"🚀 Running ATES FAM Fitness test suite ({len(test_files)} test files)...")
    for f in test_files:
        rel = os.path.relpath(f, WORKSPACE_DIR)
        mod_name = rel.replace(os.sep, ".").replace(".py", "")
        mod = importlib.import_module(mod_name)
        test_funcs = [
            fn
            for name, fn in inspect.getmembers(mod, inspect.isfunction)
            if name.startswith("test_")
        ]
        for fn in test_funcs:
            try:
                fn()
                passed += 1
            except Exception as e:
                print(f"❌ FAIL {mod_name}.{fn.__name__}: {e}")
                failures.append(f"{mod_name}.{fn.__name__}: {e}")
                failed += 1

    total = passed + failed
    print(f"\n==================================================")
    print(f"🎯 Test Results: {passed}/{total} passed, {failed} failed.")
    print(f"==================================================")
    if failed > 0:
        for fail in failures:
            print(f" - {fail}")
        sys.exit(1)
    print("✅ All tests passed successfully!")
    sys.exit(0)


if __name__ == "__main__":
    main()
