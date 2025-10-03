# Causal Backtracking

Implement an algorithm to find events that influence failures in a distributed system.

## What is Causal Relationship?

In distributed systems, events are connected by the **"happens-before"** relationship (denoted as →):

1. **Process ordering**: If events `a` and `b` occur in the same process, and `a` happens before `b`, then `a → b`
2. **Message passing**: If `a` is a send event and `b` is the corresponding receive event, then `a → b` 
3. **Transitivity**: If `a → b` and `b → c`, then `a → c`

Events are **causally related** if one could potentially influence the other through this happens-before chain.

## Vector Clocks

Vector clocks help determine causal ordering:
- Each process maintains a vector of logical timestamps
- Event `a` causally precedes event `b` if `VC(a) < VC(b)` (component-wise comparison)
- If neither `VC(a) < VC(b)` nor `VC(b) < VC(a)`, events are concurrent

### Vector Clock Comparison Rules

For vector clocks `VC(a) = (a₁, a₂, ..., aₙ)` and `VC(b) = (b₁, b₂, ..., bₙ)`:

**Causal precedence** (`VC(a) < VC(b)`):
- `aᵢ ≤ bᵢ` for all components `i` (component-wise ≤), AND
- `aⱼ < bⱼ` for at least one component `j` (strict inequality)

**Examples:**
- `(1, 0, 0) < (2, 0, 0)` ✓ (a₁ < b₁, others equal)
- `(1, 2, 0) < (1, 3, 1)` ✓ (a₂ < b₂ and a₃ < b₃, a₁ equal)  
- `(2, 1, 0) < (1, 2, 0)` ✗ (a₁ > b₁, so not ≤ in all components)
- `(1, 2, 0)` and `(2, 1, 0)` are **concurrent** (neither < nor >)

## Problem Statement

Given a distributed system log, find all events that could have causally influenced any system failure.

## Example

Consider this system with 3 processes:

```
Process 0: e1(1,0,0) → e2(2,0,0) → e3(3,1,0) → e4(4,1,0)[ERROR]
Process 1: e5(0,1,0) → e6(2,2,0) → e7(3,3,0)  
Process 2: e8(0,0,1) → e9(0,0,2)[FAILURE]
```

**Input logs:**
```
ID: e1, PID: 0, VC: (1, 0, 0), MSG: local
ID: e2, PID: 0, VC: (2, 0, 0), MSG: send->1
ID: e3, PID: 0, VC: (3, 1, 0), MSG: recv<-1
ID: e4, PID: 0, VC: (4, 1, 0), MSG: error: timeout
ID: e5, PID: 1, VC: (0, 1, 0), MSG: local
ID: e6, PID: 1, VC: (2, 2, 0), MSG: recv<-0
ID: e7, PID: 1, VC: (3, 3, 0), MSG: send->0
ID: e8, PID: 2, VC: (0, 0, 1), MSG: local
ID: e9, PID: 2, VC: (0, 0, 2), MSG: failure: connection lost
```

**Step-by-step causal analysis:**

1. **Vector clock comparisons for e4**:
   - `e1(1,0,0) < e4(4,1,0)` ✓ (1≤4, 0≤1, 0≤0 and 1<4)
   - `e2(2,0,0) < e4(4,1,0)` ✓ (2≤4, 0≤1, 0≤0 and 2<4)  
   - `e3(3,1,0) < e4(4,1,0)` ✓ (3≤4, 1≤1, 0≤0 and 3<4)
   - `e5(0,1,0) < e4(4,1,0)` ✓ (0≤4, 1≤1, 0≤0 and 0<4)
   - `e6(2,2,0) < e4(4,1,0)` ✗ (2≤4, but 2>1, so not ≤ in all components)
   - `e7(3,3,0) < e4(4,1,0)` ✗ (3≤4, but 3>1, so not ≤ in all components)

2. **Vector clock comparisons for e9**:
   - `e8(0,0,1) < e9(0,0,2)` ✓ (0≤0, 0≤0, 1≤2 and 1<2)

**Causal analysis:**
- **Failures detected**: `e4` (error), `e9` (failure)
- **Events influencing e4**: `e1 → e2 → e3 → e4` (causal chain in process 0)
- **Events influencing e9**: `e8 → e9` (causal chain in process 2)
- **Result**: `["e1", "e2", "e3", "e5", "e8"]`

**Note**: `e6` and `e7` do NOT influence `e4` because their vector clocks show they happened after receiving information that `e4` couldn't have known about (Process 1's counter is higher than Process 0's counter at `e4`).

## Your Task

Implement `find_events_influencing_failures(logs: List[str]) -> List[str]` that:

1. **Parse logs** into events with vector clocks
2. **Identify failures** (messages containing: "error", "failure", "exception", "timeout", "crash", "abort")  
3. **Build causality graph** using vector clock ordering (`VC(a) < VC(b)` means `a → b`)
4. **Find all predecessors** of failure events
5. **Return sorted list** of event IDs that could influence failures