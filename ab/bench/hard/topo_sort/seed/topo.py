def topo_sort(graph):
    """Topologically sort a dependency graph.

    graph: dict mapping each node to a list of nodes it DEPENDS ON (its
    dependencies must appear before it in the output). Every node appears as a
    key. Return a list containing all nodes in a valid topological order.

    Tie-break: whenever several nodes are simultaneously free to be placed next,
    choose the smallest one (so the output is deterministic).

    Raise ValueError if the graph contains a cycle.
    """
    raise NotImplementedError
