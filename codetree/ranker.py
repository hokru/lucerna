"""
PageRank computation for the CodeGraph.
For query-based relevance scoring and co-ranking, see search.py.
"""
from typing import Dict
from .graph import CodeGraph

def calculate_pagerank(graph: CodeGraph, damping: float = 0.85, max_iter: int = 50, tol: float = 1e-6) -> Dict[str, float]:
    """
    Computes a PageRank score for each FileNode in the CodeGraph.
    Edges point from importer -> importee, so widely-imported files score higher.
    """
    nodes = list(graph.nodes.keys())
    N = len(nodes)
    if N == 0:
        return {}
        
    # Initialize uniform PageRank
    pr = {node: 1.0 / N for node in nodes}
    
    # Pre-calculate out-degree for each node (number of files this node imports)
    out_degree = {node: len(graph.successors(node)) for node in nodes}
    
    # Find dangling nodes (nodes that don't import anything)
    dangling_nodes = [node for node in nodes if out_degree[node] == 0]
    
    for _ in range(max_iter):
        new_pr = {}
        diff = 0.0
        
        # Handle dangling nodes: their rank is distributed evenly to all nodes
        dangling_sum = sum(pr[n] for n in dangling_nodes)
        
        for node in nodes:
            rank_sum = 0.0
            # Predecessors are modules that import this `node`
            for pred in graph.predecessors(node):
                if out_degree[pred] > 0:
                    rank_sum += pr[pred] / out_degree[pred]
                    
            # PageRank formula
            new_val = (1 - damping) / N + damping * (rank_sum + dangling_sum / N)
            new_pr[node] = new_val
            diff += abs(new_pr[node] - pr[node])
            
        pr = new_pr
        
        # Check convergence
        if diff < tol:
            break
            
    return pr
