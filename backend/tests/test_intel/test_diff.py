"""Unit tests for detect_change — pure logic, no DB / LLM / network."""

from __future__ import annotations

import pytest

from app.intel.pipeline.diff import (
    _cosine_distance,
    _parsed_diff,
    _text_similarity,
    _unified_diff,
)


def test_cosine_distance_identical():
    a = [1.0, 0.0, 0.0]
    assert _cosine_distance(a, a) == pytest.approx(0.0, abs=1e-9)


def test_cosine_distance_orthogonal():
    a = [1.0, 0.0]
    b = [0.0, 1.0]
    assert _cosine_distance(a, b) == pytest.approx(1.0, abs=1e-9)


def test_cosine_distance_handles_none():
    assert _cosine_distance(None, [1.0, 2.0]) is None
    assert _cosine_distance([1.0, 2.0], None) is None
    assert _cosine_distance([], [1.0]) is None
    assert _cosine_distance([0.0, 0.0], [1.0, 2.0]) is None


def test_cosine_distance_dim_mismatch():
    assert _cosine_distance([1.0, 2.0], [1.0]) is None


def test_text_similarity_identical():
    assert _text_similarity("hello world", "hello world") == 1.0


def test_text_similarity_empty():
    assert _text_similarity("", "") == 1.0
    assert _text_similarity("a", "") < 1.0


def test_text_similarity_substring():
    s = _text_similarity("the quick brown fox", "the slow brown fox")
    assert 0.5 < s < 1.0


def test_unified_diff_truncates():
    old = "\n".join(f"line {i}" for i in range(500))
    new = "\n".join(f"line {i}" for i in range(500, 1000))
    diff = _unified_diff(old, new)
    assert len(diff) <= 200  # TEXT_DIFF_MAX_LINES


def test_parsed_diff_added_removed_changed():
    diff = _parsed_diff({"a": 1, "b": 2}, {"a": 1, "c": 3})
    assert diff["added"] == ["c"]
    assert diff["removed"] == ["b"]
    assert diff["changed"] == []

    diff = _parsed_diff({"a": 1}, {"a": 2})
    assert diff["changed"] == ["a"]
