"""
ABD Atomic Register Test Runner with Parametrized Tests

This module provides a Python test interface for the ABD Atomic Register
implementation using pytest parametrization for cleaner test organization.
The actual tests are implemented in Rust and run using the cargo test runner.

To run tests manually:
    cd tests
    cargo run -- -i ../solution.py                    # Run all tests
    cargo run -- -i ../solution.py -t "SINGLE WRITE-READ"  # Specific test
    cargo run -- -i ../solution.py -d                 # Run with debug output
"""

import pytest
import subprocess
import os
from pathlib import Path
from typing import Optional, Tuple


# Test cases configuration
TEST_CASES = [
    ("SINGLE WRITE-READ", "Test single write followed by read operation."),
    ("WRITE-WRITE-READ", "Test two writes followed by read operation."),
    ("QUORUM READ", "Test quorum-based read operations."),
    ("QUORUM WRITE", "Test quorum-based write operations."),
    ("MULTIPLE CLIENTS CONCURRENT WRITES",
     "Test multiple clients performing concurrent writes."),
    ("WRITE READ CONFLICT", "Test write-read conflict scenarios."),
    ("MANY CONCURRENT OPERATIONS", "Test many concurrent operations."),
    ("CASCADING WRITES", "Test cascading write operations."),
    ("UNRELIABLE NETWORK WITH QUORUM FAILURE",
     "Test behavior with unreliable network and quorum failures."),
    ("LINEARIZABILITY WITH FAILURES",
     "Test linearizability properties with failures."),
    ("TWO PHASE READ NECESSITY",
     "Test necessity of two-phase read protocol."),
    ("TWO PHASE WRITE NECESSITY",
     "Test necessity of two-phase write protocol."),
    ("PARTIAL REPLICA UPDATES REQUIRE WRITE BACK",
     "Test that partial replica updates require write-back."),
]


def run_rust_test(test_name: Optional[str] = None,
                  debug: bool = False
                  ) -> Optional[subprocess.CompletedProcess]:
    """
    Run Rust tests using cargo with proper error handling.

    Args:
        test_name: Optional specific test name to run
        debug: Enable debug output

    Returns:
        subprocess.CompletedProcess or None if failed
    """
    cmd = ["cargo", "run", "--", "-i", "../solution.py"]

    if test_name:
        cmd.extend(["-t", test_name])
    if debug:
        cmd.append("-d")

    try:
        # Change to tests directory
        original_dir = os.getcwd()
        tests_dir = Path(__file__).parent / "tests"
        os.chdir(tests_dir)

        result = subprocess.run(cmd, capture_output=True, text=True,
                                timeout=30)
        return result

    except subprocess.TimeoutExpired:
        return None
    except Exception:
        return None
    finally:
        os.chdir(original_dir)


def check_rust_environment() -> Tuple[bool, str]:
    """
    Check if Rust environment is properly configured.

    Returns:
        Tuple of (is_ok, message)
    """
    try:
        # Check if cargo is available
        result = subprocess.run(["cargo", "--version"],
                                capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            return False, "Cargo not working properly"

        tests_dir = Path(__file__).parent / "tests"
        if not tests_dir.exists():
            return False, "Tests directory not found"

        return True, "Environment appears functional"
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
        return False, f"Environment check failed: {e}"


def assert_test_success(result: Optional[subprocess.CompletedProcess],
                        test_name: str) -> None:
    """
    Assert that a test result indicates success.

    Args:
        result: subprocess.CompletedProcess result
        test_name: Name of the test for error reporting
    """
    if result is None:
        pytest.fail(f"Test {test_name} failed: No result returned "
                    f"(timeout or exception)")

    print(f"\n=== {test_name} OUTPUT ===")
    if result.stdout:
        print(f"STDOUT:\n{result.stdout}")
    if result.stderr:
        print(f"STDERR:\n{result.stderr}")

    # Check for specific errors that indicate environment issues rather than
    # test failures
    if result.stderr:
        error_indicators = [
            "ld: symbol(s) not found",
            "linking with `cc` failed",
            "found architecture 'x86_64', required architecture 'arm64'",
            "error: could not compile"
        ]

        if any(indicator in result.stderr for indicator in error_indicators):
            pytest.fail(f"Test {test_name} failed due to compilation/linking "
                        f"issues: {result.stderr}")
            return

    assert result.returncode == 0, (
        f"{test_name} failed with return code {result.returncode}\n"
        f"STDOUT: {result.stdout}\n"
        f"STDERR: {result.stderr}"
    )


@pytest.mark.parametrize("test_name,description", TEST_CASES)
def test_abd_register(test_name: str, description: str):
    """
    Parametrized test for all ABD Register test cases.

    Args:
        test_name: Name of the Rust test to run
        description: Description of what the test does
    """
    env_ok, env_msg = check_rust_environment()
    if not env_ok:
        pytest.fail(f"Test environment not ready: {env_msg}")

    result = run_rust_test(test_name)
    assert_test_success(result, test_name)
