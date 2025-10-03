import pytest
from causal_backtracking import find_events_influencing_failures


@pytest.fixture
def sample_logs():
    return [
        "ID: e1, PID: 0, VC: (1, 0, 0), MSG: local",
        "ID: e2, PID: 1, VC: (0, 1, 0), MSG: send->0",
        "ID: e3, PID: 0, VC: (2, 1, 0), MSG: recv<-1",
        "ID: e4, PID: 0, VC: (3, 1, 0), MSG: error: database timeout",
        "ID: e5, PID: 2, VC: (0, 0, 1), MSG: local",
        "ID: e6, PID: 2, VC: (0, 0, 2), MSG: failure: connection lost",
        "ID: e7, PID: 1, VC: (0, 2, 0), MSG: local"
    ]


def test_basic_influencing_events(sample_logs):
    result = find_events_influencing_failures(sample_logs)

    expected_influencing = ["e1", "e2", "e3", "e5"]

    for event_id in expected_influencing:
        assert event_id in result

    assert "e4" not in result
    assert "e6" not in result

    assert result == sorted(result)


def test_no_failures_error():
    logs_without_failures = [
        "ID: e1, PID: 0, VC: (1, 0), MSG: local",
        "ID: e2, PID: 1, VC: (0, 1), MSG: send->0"
    ]

    with pytest.raises(ValueError) as excinfo:
        find_events_influencing_failures(logs_without_failures)

    assert "No failure events found" in str(excinfo.value)


def test_empty_logs_error():
    with pytest.raises(ValueError) as excinfo:
        find_events_influencing_failures([])

    assert "cannot be empty" in str(excinfo.value)


def test_crash_keyword_detection():
    logs = [
        "ID: e1, PID: 0, VC: (1, 0), MSG: local",
        "ID: e2, PID: 1, VC: (1, 1), MSG: crash detected"
    ]

    result = find_events_influencing_failures(logs)

    assert "e1" in result
    assert len(result) == 1


def test_result_is_sorted(sample_logs):
    result = find_events_influencing_failures(sample_logs)
    assert result == sorted(result)


def test_no_influencing_events():
    logs = [
        "ID: e1, PID: 0, VC: (1, 0), MSG: error: isolated failure"
    ]

    result = find_events_influencing_failures(logs)
    assert len(result) == 0


def test_basic_functionality():
    logs = [
        "ID: e1, PID: 0, VC: (1, 0, 0), MSG: local",
        "ID: e2, PID: 1, VC: (0, 1, 0), MSG: send->2",
        "ID: e3, PID: 2, VC: (0, 1, 1), MSG: recv<-1",
        "ID: e4, PID: 2, VC: (0, 1, 2), MSG: error: timeout"
    ]

    result = find_events_influencing_failures(logs)

    assert isinstance(result, list)
    for event_id in result:
        assert isinstance(event_id, str)
    assert result == sorted(result)
    assert "e2" in result
    assert "e3" in result


def test_no_failures_raises_error():
    logs = [
        "ID: e1, PID: 0, VC: (1, 0), MSG: local",
        "ID: e2, PID: 1, VC: (0, 1), MSG: send->0",
        "ID: e3, PID: 0, VC: (2, 1), MSG: recv<-1"
    ]

    with pytest.raises(ValueError) as excinfo:
        find_events_influencing_failures(logs)
    assert "failure events found" in str(excinfo.value)


def test_single_failure_no_predecessors():
    logs = [
        "ID: e1, PID: 0, VC: (1, 0), MSG: error: system failure"
    ]

    result = find_events_influencing_failures(logs)
    assert result == []


def test_multiple_failures():
    logs = [
        "ID: e1, PID: 0, VC: (1, 0, 0), MSG: local",
        "ID: e2, PID: 1, VC: (0, 1, 0), MSG: send->0",
        "ID: e3, PID: 0, VC: (2, 1, 0), MSG: recv<-1",
        "ID: e4, PID: 0, VC: (3, 1, 0), MSG: error: timeout",
        "ID: e5, PID: 2, VC: (0, 0, 1), MSG: failure: connection lost"
    ]

    result = find_events_influencing_failures(logs)

    assert "e1" in result
    assert "e2" in result
    assert "e3" in result

    assert result == sorted(result)


def test_complex_causality_chain():
    logs = [
        "ID: e1, PID: 0, VC: (1, 0, 0), MSG: local",
        "ID: e2, PID: 0, VC: (2, 0, 0), MSG: send->1",
        "ID: e3, PID: 1, VC: (2, 1, 0), MSG: recv<-0",
        "ID: e4, PID: 1, VC: (2, 2, 0), MSG: send->2",
        "ID: e5, PID: 2, VC: (2, 2, 1), MSG: recv<-1",
        "ID: e6, PID: 2, VC: (2, 2, 2), MSG: error: processing failed"
    ]

    result = find_events_influencing_failures(logs)

    expected_influencers = ["e1", "e2", "e3", "e4", "e5"]
    for event_id in expected_influencers:
        assert event_id in result

    assert "e6" not in result

    assert result == sorted(result)


def test_database_timeout_scenario():
    logs = [
        "ID: e1, PID: 0, VC: (1, 0, 0), MSG: local",
        "ID: e2, PID: 0, VC: (2, 0, 0), MSG: send->1",
        "ID: e3, PID: 1, VC: (2, 1, 0), MSG: recv<-0",
        "ID: e4, PID: 1, VC: (2, 2, 0), MSG: local",
        "ID: e5, PID: 1, VC: (2, 3, 0), MSG: error: database timeout",
        "ID: e6, PID: 2, VC: (0, 0, 1), MSG: local"
    ]

    result = find_events_influencing_failures(logs)

    expected_influencing = {"e1", "e2", "e3", "e4"}
    actual_influencing = set(result)
    assert expected_influencing.issubset(actual_influencing)

    assert "e6" not in result


def test_branched_system_single_failure_branch():
    logs = [
        "ID: e1, PID: 0, VC: (1, 0, 0), MSG: send->1",
        "ID: e2, PID: 0, VC: (2, 2, 0), MSG: recv<-1",
        "ID: e3, PID: 0, VC: (3, 2, 0), MSG: local",
        "ID: e4, PID: 1, VC: (1, 1, 0), MSG: recv<-0",
        "ID: e5, PID: 1, VC: (1, 2, 0), MSG: send->0",
        "ID: e6, PID: 1, VC: (1, 3, 1), MSG: send->2",
        "ID: e7, PID: 1, VC: (1, 4, 1), MSG: error: network timeout",
        "ID: e8, PID: 2, VC: (1, 1, 1), MSG: recv<-1",
        "ID: e9, PID: 2, VC: (1, 3, 2), MSG: recv<-1",
        "ID: e10, PID: 2, VC: (1, 3, 3), MSG: local"
    ]

    result = find_events_influencing_failures(logs)

    expected_influencers = {"e1", "e4", "e5", "e6", "e8"}

    for event_id in expected_influencers:
        assert event_id in result

    assert expected_influencers.issubset(set(result))

    definitely_not_influencing = {"e3", "e10"}
    for event_id in definitely_not_influencing:
        assert event_id not in result

    assert "e7" not in result

    assert len(result) > 0
    assert result == sorted(result)


def test_multiple_branches_isolated_failure():
    logs = [
        "ID: e1, PID: 0, VC: (1, 0, 0, 0), MSG: send->2",
        "ID: e2, PID: 0, VC: (2, 0, 0, 0), MSG: send->3",
        "ID: e3, PID: 0, VC: (3, 0, 0, 0), MSG: local",
        "ID: e4, PID: 0, VC: (4, 0, 0, 0), MSG: local",
        "ID: e5, PID: 1, VC: (0, 1, 0, 0), MSG: local",
        "ID: e6, PID: 1, VC: (0, 2, 0, 0), MSG: failure: system crash",
        "ID: e7, PID: 2, VC: (1, 0, 1, 0), MSG: recv<-0",
        "ID: e8, PID: 2, VC: (1, 0, 2, 0), MSG: local",
        "ID: e9, PID: 2, VC: (1, 0, 3, 0), MSG: local",
        "ID: e10, PID: 3, VC: (2, 0, 0, 1), MSG: recv<-0",
        "ID: e11, PID: 3, VC: (2, 0, 0, 2), MSG: local",
        "ID: e12, PID: 3, VC: (2, 0, 0, 3), MSG: local"
    ]

    result = find_events_influencing_failures(logs)

    expected_influencers = {"e5"}
    actual_influencers = set(result)

    assert actual_influencers == expected_influencers

    non_influencing = {"e1", "e2", "e3", "e4", "e7", "e8", "e9", "e10",
                       "e11", "e12"}
    for event_id in non_influencing:
        assert event_id not in result


def test_complex_distributed_system_partial_failure():
    logs = [
        "ID: e1, PID: 0, VC: (1, 0, 0, 0), MSG: local",
        "ID: e2, PID: 0, VC: (2, 0, 0, 0), MSG: send->1",
        "ID: e3, PID: 0, VC: (3, 5, 0, 0), MSG: recv<-1",
        "ID: e4, PID: 1, VC: (2, 1, 0, 0), MSG: recv<-0",
        "ID: e5, PID: 1, VC: (2, 2, 0, 0), MSG: send->2",
        "ID: e6, PID: 1, VC: (2, 3, 0, 0), MSG: send->3",
        "ID: e7, PID: 1, VC: (2, 4, 4, 1), MSG: recv<-2",
        "ID: e8, PID: 1, VC: (2, 5, 4, 1), MSG: send->0",
        "ID: e9, PID: 2, VC: (2, 2, 1, 0), MSG: recv<-1",
        "ID: e10, PID: 2, VC: (2, 2, 2, 0), MSG: local",
        "ID: e11, PID: 2, VC: (2, 2, 3, 0), "
        "MSG: error: database connection timeout",
        "ID: e12, PID: 2, VC: (2, 4, 4, 0), MSG: send->1",
        "ID: e13, PID: 3, VC: (2, 3, 0, 1), MSG: recv<-1",
        "ID: e14, PID: 3, VC: (2, 3, 0, 2), MSG: local",
        "ID: e15, PID: 3, VC: (2, 3, 0, 3), MSG: local"
    ]

    result = find_events_influencing_failures(logs)

    expected_influencers = {"e1", "e2", "e4", "e5", "e9", "e10"}

    for event_id in expected_influencers:
        assert event_id in result

    healthy_events = {"e6", "e13", "e14", "e15"}
    for event_id in healthy_events:
        assert event_id not in result

    assert "e11" not in result

    assert result == sorted(result)


def test_parallel_branches_with_cascading_failure():
    logs = [
        "ID: e1, PID: 0, VC: (1, 0, 0, 0), MSG: local",
        "ID: e2, PID: 0, VC: (2, 0, 0, 0), MSG: send->1",
        "ID: e3, PID: 0, VC: (3, 0, 0, 0), MSG: local",
        "ID: e4, PID: 1, VC: (2, 1, 0, 0), MSG: recv<-0",
        "ID: e5, PID: 1, VC: (2, 2, 0, 0), MSG: error: service unavailable",
        "ID: e6, PID: 2, VC: (2, 1, 1, 0), MSG: recv<-1",
        "ID: e7, PID: 2, VC: (2, 2, 2, 0), MSG: recv<-1",
        "ID: e8, PID: 2, VC: (2, 2, 3, 0), MSG: error: dependency failure",
        "ID: e9, PID: 3, VC: (0, 0, 0, 1), MSG: local",
        "ID: e10, PID: 3, VC: (0, 0, 0, 2), MSG: local"
    ]

    result = find_events_influencing_failures(logs)

    expected_influencers = {"e1", "e2", "e4", "e6", "e7"}

    for event_id in expected_influencers:
        assert event_id in result

    healthy_events = {"e9", "e10"}
    for event_id in healthy_events:
        assert event_id not in result

    failure_events = {"e5", "e8"}
    for event_id in failure_events:
        assert event_id not in result

    assert len(result) >= 4
