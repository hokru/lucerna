from lucerna.graph import CodeGraph, FileNode, ImportEdge


def test_neighborhood_depth_traversal():
    graph = CodeGraph()

    # Setup chain: a -> b -> c
    node_a = FileNode("a.py", "a", [], None, [], [])
    node_b = FileNode("b.py", "b", [], None, [], [])
    node_c = FileNode("c.py", "c", [], None, [], [])

    graph.add_node(node_a)
    graph.add_node(node_b)
    graph.add_node(node_c)

    graph.add_edge(ImportEdge("a", "b", []))
    graph.add_edge(ImportEdge("b", "c", []))

    # Neighborhood of 'a' with depth 1 should have 'a' and 'b', but not 'c'
    sub1 = graph.neighborhood("a", depth=1)
    assert "a" in sub1.nodes
    assert "b" in sub1.nodes
    assert "c" not in sub1.nodes

    # Neighborhood of 'a' with depth 2 should have all nodes
    sub2 = graph.neighborhood("a", depth=2)
    assert "a" in sub2.nodes
    assert "b" in sub2.nodes
    assert "c" in sub2.nodes
