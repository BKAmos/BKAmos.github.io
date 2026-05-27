"""Tests for top-gene stability metrics."""
from orchestrator.stability import compare_top_genes, jaccard_similarity


def test_jaccard_empty_both():
    assert jaccard_similarity([], []) == 1.0


def test_jaccard_disjoint():
    assert jaccard_similarity(["A", "B"], ["C", "D"]) == 0.0


def test_jaccard_partial_overlap():
    assert jaccard_similarity(["A", "B", "C"], ["B", "C", "D"]) == 0.5


def test_compare_top_genes_stable():
    result = compare_top_genes(["G1", "G2", "G3"], ["G1", "G2", "G3"], top_n=3)
    assert result["stable"] is True
    assert result["jaccard"] == 1.0


def test_compare_top_genes_unstable():
    result = compare_top_genes(["G1", "G2", "G3"], ["G4", "G5", "G6"], top_n=3, stable_threshold=0.5)
    assert result["stable"] is False
