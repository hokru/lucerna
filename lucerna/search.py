from typing import Dict
from .graph import CodeGraph


def score_query(graph: CodeGraph, query: str) -> Dict[str, float]:
    """
    Scores each file node against the query tokens using weighted keyword matching.
    Returns normalized scores [0, 1].
    """
    if not query:
        return {node: 0.0 for node in graph.nodes}

    tokens = [t.lower() for t in query.split()]
    raw_scores = {}

    for module, node in graph.nodes.items():
        score = 0.0

        # Match path/module (weight 3)
        path_lower = node.path.lower()
        module_lower = node.module_name.lower()
        for token in tokens:
            if token in path_lower or token in module_lower:
                score += 3.0

        # Match symbol names (weight 2)
        symbol_names_lower = " ".join([sym.name.lower() for sym in node.symbols])
        for token in tokens:
            if token in symbol_names_lower:
                score += 2.0

        # Match docstrings (weight 1)
        doc_strings = []
        if node.docstring:
            doc_strings.append(node.docstring.lower())
        for sym in node.symbols:
            if sym.docstring:
                doc_strings.append(sym.docstring.lower())

        all_docs_lower = " ".join(doc_strings)
        for token in tokens:
            if token in all_docs_lower:
                score += 1.0

        raw_scores[module] = score

    # Normalize
    max_score = max(raw_scores.values()) if raw_scores else 0.0
    if max_score > 0:
        return {m: s / max_score for m, s in raw_scores.items()}
    else:
        return {m: 0.0 for m in raw_scores.keys()}


def combine_scores(
    relevance: Dict[str, float], pagerank: Dict[str, float], alpha: float = 0.6
) -> Dict[str, float]:
    """
    Combines normalized relevance and PageRank scores using a weighted sum.
    """
    # Normalize pagerank
    max_pr = max(pagerank.values()) if pagerank else 0.0
    pr_norm = {m: (pr / max_pr) if max_pr > 0 else 0.0 for m, pr in pagerank.items()}

    combined = {}
    for m in pr_norm.keys():
        rel = relevance.get(m, 0.0)
        pr = pr_norm.get(m, 0.0)
        combined[m] = alpha * rel + (1 - alpha) * pr

    return combined
