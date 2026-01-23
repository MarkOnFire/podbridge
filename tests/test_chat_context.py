"""
Tests for chat context builder service
"""

import pytest
from pathlib import Path
from api.services.chat_context import (
    load_editor_personality,
    get_project_data,
    build_chat_context,
    DEFAULT_PERSONALITY,
    EDITOR_PERSONALITY_PATH,
    OUTPUT_DIR
)


def test_load_editor_personality():
    """Test loading editor personality from file."""
    personality = load_editor_personality()

    # Should return a non-empty string
    assert isinstance(personality, str)
    assert len(personality) > 0

    # If file exists, should contain expected content
    if EDITOR_PERSONALITY_PATH.exists():
        assert "professional video content editor" in personality.lower()
        assert "seo specialist" in personality.lower()


def test_load_editor_personality_graceful_fallback():
    """Test that fallback works if file doesn't exist."""
    # Even if file doesn't exist, should return default
    personality = load_editor_personality()
    assert isinstance(personality, str)
    assert len(personality) > 0


def test_get_project_data_not_found():
    """Test getting data for non-existent project."""
    result = get_project_data("NONEXISTENT_PROJECT_999")
    assert result is None


def test_get_project_data_real_project():
    """Test getting data for a real project (if one exists)."""
    # Find first real project in OUTPUT directory
    if not OUTPUT_DIR.exists():
        pytest.skip("OUTPUT directory not found")

    projects = [p for p in OUTPUT_DIR.iterdir() if p.is_dir() and (p / "manifest.json").exists()]

    if not projects:
        pytest.skip("No projects with manifests found")

    # Test with first available project
    project_name = projects[0].name
    result = get_project_data(project_name)

    assert result is not None
    assert "manifest" in result
    assert "brainstorming" in result
    assert "transcript_excerpt" in result

    # Manifest should be a dict
    assert isinstance(result["manifest"], dict)
    assert "job_id" in result["manifest"]

    # Strings should be present (even if empty)
    assert isinstance(result["brainstorming"], str)
    assert isinstance(result["transcript_excerpt"], str)


def test_get_project_data_transcript_truncation():
    """Test that transcript is truncated to 10k chars."""
    # Find a project with a transcript
    if not OUTPUT_DIR.exists():
        pytest.skip("OUTPUT directory not found")

    for project_path in OUTPUT_DIR.iterdir():
        if not project_path.is_dir():
            continue

        transcript_path = project_path / "formatter_output.md"
        if transcript_path.exists():
            # Check if transcript is longer than 10k chars
            full_text = transcript_path.read_text()
            if len(full_text) > 10000:
                # Test with this project
                result = get_project_data(project_path.name)
                assert result is not None

                excerpt = result["transcript_excerpt"]
                # Should be truncated to ~10k (plus truncation message)
                assert len(excerpt) <= 10200  # Allow for truncation message (generous margin)
                assert "Transcript truncated" in excerpt
                return

    pytest.skip("No projects with long transcripts found")


def test_build_chat_context_no_project():
    """Test building context without a project."""
    context = build_chat_context()

    # Should contain editor personality
    assert isinstance(context, str)
    assert len(context) > 0

    # Should not contain project context section
    assert "CURRENT PROJECT CONTEXT" not in context


def test_build_chat_context_with_project():
    """Test building context with a project."""
    if not OUTPUT_DIR.exists():
        pytest.skip("OUTPUT directory not found")

    projects = [p for p in OUTPUT_DIR.iterdir() if p.is_dir() and (p / "manifest.json").exists()]

    if not projects:
        pytest.skip("No projects with manifests found")

    # Test with first available project
    project_name = projects[0].name
    context = build_chat_context(project_name)

    # Should contain editor personality
    assert isinstance(context, str)
    assert len(context) > 0

    # Should contain project context section
    assert "CURRENT PROJECT CONTEXT" in context
    assert f"Project: {project_name}" in context

    # Should contain project metadata
    assert "Job ID" in context


def test_build_chat_context_nonexistent_project():
    """Test building context with non-existent project."""
    context = build_chat_context("NONEXISTENT_PROJECT_999")

    # Should still return base personality (project context just won't be added)
    assert isinstance(context, str)
    assert len(context) > 0

    # Should not contain project context section
    assert "CURRENT PROJECT CONTEXT" not in context
