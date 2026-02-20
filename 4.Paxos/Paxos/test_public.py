"""
Paxos Test Runner with Parametrized Tests

This module provides a Python test interface for the Paxos implementation
using pytest parametrization for cleaner test organization.
The actual tests are implemented in Rust and run using the cargo test runner.

To run tests manually:
    cd tests
    cargo run -- -i ../solution.py                    # Run all tests
    cargo run -- -i ../solution.py -t "BASIC"         # Specific test
    cargo run -- -i ../solution.py -d                 # Run with debug output
    cargo run -- -i ../solution.py -n 5               # Run with 5 nodes
"""

import pytest
import subprocess
import os
from pathlib import Path
from typing import Optional


TEST_CASES = [
    ("BASIC", "Test basic Paxos consensus with multiple proposers."),
    ("NETWORK DELAY", "Test Paxos with network delays."),
    ("MESSAGE LOSS", "Test Paxos with message loss in the network."),
    ("NETWORK PARTITION", "Test Paxos behavior during network partition."),
    ("QUORUM", "Test Paxos with minority of nodes unavailable."),
    ("DUELING PROPOSERS", "Test Paxos with competing proposers."),
    ("SINGLE ACCEPTOR FAILURE", "Test Paxos with one acceptor failure."),
    ("LATE JOINER", "Test Paxos with late joining proposer."),
]


def run_rust_test(test_name: Optional[str] = None,
                  debug: bool = False,
                  nodes: int = 3
                  ) -> Optional[subprocess.CompletedProcess]:
    cmd = ["cargo", "run", "--", "-i", "../solution.py"]

    if test_name:
        cmd.extend(["-t", test_name])
    if debug:
        cmd.append("-d")
    if nodes != 3:
        cmd.extend(["-n", str(nodes)])

    try:
        original_dir = os.getcwd()
        tests_dir = Path(__file__).parent / "tests"
        os.chdir(tests_dir)

        result = subprocess.run(cmd, capture_output=True, text=True,
                                timeout=60)
        return result

    except subprocess.TimeoutExpired:
        return None
    except Exception:
        return None
    finally:
        os.chdir(original_dir)


def assert_test_success(result: Optional[subprocess.CompletedProcess],
                        test_name: str) -> None:
    if result is None:
        pytest.fail(f"Test {test_name} failed: No result returned "
                    f"(timeout or exception)")

    print(f"\n=== {test_name} OUTPUT ===")
    if result.stdout:
        print(f"STDOUT:\n{result.stdout}")
    if result.stderr:
        print(f"STDERR:\n{result.stderr}")

    assert result.returncode == 0, (
        f"{test_name} failed with return code {result.returncode}\n"
        f"STDOUT: {result.stdout}\n"
        f"STDERR: {result.stderr}"
    )


@pytest.mark.parametrize("test_name,description", TEST_CASES)
def test_paxos(test_name: str, description: str):
    result = run_rust_test(test_name)
    assert_test_success(result, test_name)
