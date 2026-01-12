from flowtask.graph import would_create_cycle, topo_sort


def test_cycle_detection_direct_self():
    assert would_create_cycle([], task_id=1, prereq_id=1) is True


def test_cycle_detection_indirect():
    edges = [(2, 1), (3, 2)]
    assert would_create_cycle(edges, task_id=1, prereq_id=3) is True


def test_cycle_detection_ok():
    edges = [(2, 1), (3, 2)]
    assert would_create_cycle(edges, task_id=4, prereq_id=3) is False


def test_toposort_basic():
    tasks = [1, 2, 3]
    edges = [(2, 1), (3, 2)]
    order = topo_sort(tasks, edges)
    assert order.index(1) < order.index(2) < order.index(3)