import re

from typing import List
from dataclasses import dataclass


@dataclass
class LogLine:
    id: str
    pid: int
    vtime: List[int]
    message: str
    is_error: bool
    error_level: str


LOG_REGEX = re.compile(r"ID: (\w+), PID: (\d+), VC: (\(\d+(, \d+)*\)), MSG: (.*)")
FAILURE_LEVELS = ["error", "failure", "exception", "timeout", "crash", "abort"]
OK_LEVEL = "OK"


def vtime_convert(regex_group: str) -> List[int]:
    return list(map(lambda el: int(el.strip()), regex_group[1:-1].split(",")))


def vtime_less(a: List[int], b: List[int]) -> bool:
    return \
        all(map(lambda el: el[0] <= el[1],
                zip(a, b))) and \
        any(map(lambda el: el[0] != el[1], 
                zip(a, b)))


def find_events_influencing_failures(logs: List[str]) -> List[str]:
    log_lines = []

    for log in logs:
        regex_match = LOG_REGEX.match(log)
        assert regex_match is not None

        id = str(regex_match.group(1))
        pid = int(regex_match.group(2))
        vtime = vtime_convert(regex_match.group(3))
        message = str(regex_match.group(5))
        is_error = False
        error_level = OK_LEVEL
        for level in FAILURE_LEVELS:
            if message.startswith(level):
                is_error = True
                error_level = level
                break

        ll = LogLine(id=id,
                     pid=pid,
                     vtime=vtime,
                     message=message,
                     is_error=is_error,
                     error_level=error_level)
        log_lines.append(ll)

    if len(log_lines) == 0:
        raise ValueError("cannot be empty")
    if all(map(lambda ll: not ll.is_error, log_lines)):
        raise ValueError("No failure events found")
        

    predecessors = []
    for ll in log_lines:
        next_log_lines = []
        for (ll2_index, ll2) in zip(range(len(log_lines)), log_lines):
            if vtime_less(ll2.vtime, ll.vtime):
                next_log_lines.append(ll2_index)
        predecessors.append(next_log_lines)
    

    result = set()
    for (ll, ll_predecessors) in zip(log_lines, predecessors):
        if ll.is_error:
            result.update(ll_predecessors)

    return list(sorted(map(
        lambda ll: ll.id,
        filter(
            lambda ll: not ll.is_error,
            map(
                lambda ind: log_lines[ind], 
                result
            )
        )))
    )
