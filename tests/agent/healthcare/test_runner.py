"""Test runner script for healthcare agent upload functionality."""

import subprocess
import sys
from pathlib import Path


def run_tests():
    """Run all upload-related tests."""
    test_files = [
        "tests/agent/healthcare/test_upload.py",
        "tests/agent/healthcare/test_upload_integration.py", 
        "tests/agent/healthcare/test_upload_error_scenarios.py"
    ]
    
    print("Running Healthcare Agent Upload Tests...")
    print("=" * 50)
    
    all_passed = True
    
    for test_file in test_files:
        print(f"\nRunning {test_file}...")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", test_file, "-v"],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent.parent.parent
            )
            
            if result.returncode == 0:
                print(f"✓ {test_file} - PASSED")
                print(result.stdout)
            else:
                print(f"✗ {test_file} - FAILED")
                print(result.stdout)
                print(result.stderr)
                all_passed = False
                
        except Exception as e:
            print(f"✗ {test_file} - ERROR: {e}")
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All upload tests passed!")
        return True
    else:
        print("❌ Some tests failed!")
        return False


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
