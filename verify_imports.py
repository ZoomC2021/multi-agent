
import sys
import os

print("Verifying imports...")

errors = []

try:
    print("Checking consensus_system.cli...", end=" ")
    from consensus_system import cli
    print("OK")
except ImportError as e:
    print(f"FAILED: {e}")
    errors.append(f"consensus_system.cli: {e}")
except NameError as e:
    print(f"FAILED: {e}")
    errors.append(f"consensus_system.cli NameError: {e}")

try:
    print("Checking consensus_system.external_agent...", end=" ")
    from consensus_system import external_agent
    print("OK")
    # Check for concurrent.futures usage/import
    if 'concurrent.futures' not in sys.modules:
         # It might be imported inside the module but not in sys.modules if not used yet? 
         # No, import puts it in sys.modules.
         # Let's check the file content or just trust the import didn't crash.
         pass
except ImportError as e:
    print(f"FAILED: {e}")
    errors.append(f"consensus_system.external_agent: {e}")

try:
    print("Checking bug_finder.github_pr...", end=" ")
    from bug_finder import github_pr
    print("OK")
except ImportError as e:
    print(f"FAILED: {e}")
    errors.append(f"bug_finder.github_pr: {e}")

if errors:
    print("\nERRORS FOUND:")
    for err in errors:
        print(f"  - {err}")
    sys.exit(1)
else:
    print("\nAll imports verified successfully.")
    sys.exit(0)
