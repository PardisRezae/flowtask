from __future__ import annotations

from collections import defaultdict, deque
from typing import Dict, Iterable, List, Set, Tuple

Edge = Tuple[int, int]  # (task_id, depends_on_id)


def build_adjacency(edges: Iterable[Edge]) -> Dict[int, Set[int]]:
    """
    adj[task] = {prereq1, prereq2, ...}
    meaning: task depends on prereq.
    """
    adj: Dict[int, Set[int]] = defaultdict(set)
    for task_id, prereq_id in edges:
        adj[task_id].add(prereq_id)
        if prereq_id not in adj:
            adj[prereq_id] = adj[prereq_id]
    return adj


def has_path(adj: Dict[int, Set[int]], start: int, target: int) -> bool:
    """
    DFS: is there a path start -> ... -> target?
    """
    if start == target:
        return True
    stack = [start]
    visited: Set[int] = set()
    while stack:
        node = stack.pop()
        if node in visited:
            continue
        visited.add(node)
        for nxt in adj.get(node, set()):
            if nxt == target:
                return True
            if nxt not in visited:
                stack.append(nxt)
    return False


def would_create_cycle(edges: Iterable[Edge], task_id: int, prereq_id: int) -> bool:
    """
    Adding edge task_id -> prereq_id creates a cycle iff prereq_id can reach task_id.
    """
    if task_id == prereq_id:
        return True
    adj = build_adjacency(edges)
    return has_path(adj, prereq_id, task_id)


def topo_sort(tasks: Iterable[int], edges: Iterable[Edge]) -> List[int]:
    """
    Topological sort (Kahn). Because edges are task->prereq, we invert them to prereq->task.
    """
    tasks_set = set(tasks)
    prereq_to_dependents: Dict[int, Set[int]] = defaultdict(set)
    indegree: Dict[int, int] = {t: 0 for t in tasks_set}

    for task, prereq in edges:
        if task not in tasks_set or prereq not in tasks_set:
            continue
        prereq_to_dependents[prereq].add(task)
        indegree[task] += 1

    q = deque([t for t, deg in indegree.items() if deg == 0])
    out: List[int] = []

    while q:
        n = q.popleft()
        out.append(n)
        for dep in prereq_to_dependents.get(n, set()):
            indegree[dep] -= 1
            if indegree[dep] == 0:
                q.append(dep)

    if len(out) != len(tasks_set):
        raise ValueError("Graph has a cycle (topo_sort failed).")
    return out