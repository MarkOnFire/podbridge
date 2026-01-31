"""
Chat Context Builder Service

Builds system prompts with project context for the chat prototype.
Follows the pattern from mcp_server/server.py load_project_for_editing().
"""

import json
from pathlib import Path
from typing import Optional

# Path constants
AGENT_INSTRUCTIONS_DIR = Path(__file__).parent.parent.parent / "claude-desktop-project"
EDITOR_PERSONALITY_PATH = AGENT_INSTRUCTIONS_DIR / "EDITOR_AGENT_INSTRUCTIONS.md"
OUTPUT_DIR = Path(__file__).parent.parent.parent / "OUTPUT"

# Default personality if file not found
DEFAULT_PERSONALITY = """You are a professional video content editor and SEO specialist.
You help refine metadata for video content following AP Style guidelines.
You work collaboratively with users through conversational editing."""


def load_editor_personality() -> str:
    """
    Load the editor personality from agent instructions.

    Returns:
        str: The editor personality/instructions content
    """
    try:
        if EDITOR_PERSONALITY_PATH.exists():
            return EDITOR_PERSONALITY_PATH.read_text()
        else:
            # Fallback to default if file not found
            return DEFAULT_PERSONALITY
    except Exception:
        # Gracefully handle any read errors
        return DEFAULT_PERSONALITY


def get_project_data(project_name: str) -> Optional[dict]:
    """
    Load project context data from OUTPUT folder.

    Args:
        project_name: The project ID (e.g., '2WLI1209HD')

    Returns:
        dict with keys: manifest, brainstorming, transcript_excerpt
        None if project not found
    """
    project_path = OUTPUT_DIR / project_name

    # Check if project exists
    if not project_path.exists() or not project_path.is_dir():
        return None

    # Load manifest
    manifest_path = project_path / "manifest.json"
    if not manifest_path.exists():
        return None

    try:
        with open(manifest_path) as f:
            manifest = json.load(f)
    except Exception:
        return None

    # Load brainstorming (analyst_output.md)
    brainstorming = ""
    brainstorming_path = project_path / "analyst_output.md"
    if brainstorming_path.exists():
        try:
            brainstorming = brainstorming_path.read_text()
        except Exception:
            pass

    # Load transcript excerpt (formatter_output.md, truncated to 10k chars)
    transcript_excerpt = ""
    transcript_path = project_path / "formatter_output.md"
    if transcript_path.exists():
        try:
            full_transcript = transcript_path.read_text()
            # Truncate to 10k chars
            transcript_excerpt = full_transcript[:10000]
            if len(full_transcript) > 10000:
                transcript_excerpt += "\n\n[... Transcript truncated to 10,000 characters. Use get_formatted_transcript() for full content ...]"
        except Exception:
            pass

    return {"manifest": manifest, "brainstorming": brainstorming, "transcript_excerpt": transcript_excerpt}


def build_chat_context(project_name: Optional[str] = None) -> str:
    """
    Build complete system prompt with project context.

    Args:
        project_name: Optional project ID. If provided, includes project context.

    Returns:
        str: Complete system prompt string
    """
    # Start with editor personality
    context_parts = [load_editor_personality()]

    # Add project context if provided
    if project_name:
        project_data = get_project_data(project_name)

        if project_data:
            context_parts.append("\n\n---\n## CURRENT PROJECT CONTEXT\n")

            # Add project metadata from manifest
            manifest = project_data["manifest"]
            context_parts.append(f"\n### Project: {project_name}\n")
            context_parts.append(f"- **Job ID**: {manifest.get('job_id', 'N/A')}")
            context_parts.append(f"- **Completed**: {manifest.get('completed_at', 'N/A')}")
            if manifest.get("media_id"):
                context_parts.append(f"- **Media ID**: {manifest['media_id']}")
            if manifest.get("airtable_record_id"):
                context_parts.append(f"- **Airtable Record**: {manifest['airtable_record_id']}")
                if manifest.get("airtable_url"):
                    context_parts.append(f"- **SST Link**: {manifest['airtable_url']}")
            if manifest.get("duration_minutes"):
                mins = manifest["duration_minutes"]
                context_parts.append(f"- **Duration**: {int(mins)}:{int((mins % 1) * 60):02d}")

            # Add brainstorming notes
            if project_data["brainstorming"]:
                context_parts.append("\n\n### AI-Generated Brainstorming\n")
                context_parts.append(project_data["brainstorming"])

            # Add transcript excerpt
            if project_data["transcript_excerpt"]:
                context_parts.append("\n\n### Transcript Excerpt (First 10k chars)\n")
                context_parts.append(project_data["transcript_excerpt"])

    return "\n".join(context_parts)
