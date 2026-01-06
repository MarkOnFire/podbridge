# Claude Desktop Setup for Cardigan

Everything you need to set up Cardigan in Claude Desktop is in this folder.

## Quick Setup (3 steps)

### 1. Configure the MCP Server

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "cardigan": {
      "command": "/Users/mriechers/Developer/ai-editorial-assistant-v3/venv/bin/python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "/Users/mriechers/Developer/ai-editorial-assistant-v3"
    }
  }
}
```

### 2. Create a Claude Desktop Project

1. Open Claude Desktop
2. Create a new project called **"The Metadata Neighborhood"**
3. Open project settings

### 3. Add Custom Instructions & Knowledge

**Custom Instructions:**
- Copy the contents of `CUSTOM_INSTRUCTIONS.md` into the project's custom instructions field

**Knowledge Files (drag into project):**
- `knowledge/ap_styleguide.pdf` — AP Style reference
- `knowledge/Transcript Style Guide.pdf` — PBS Wisconsin transcript formatting
- `knowledge/WPM Generative AI Guidelines.pdf` — Editorial AI usage policy
- `knowledge/Media Manager timestamp sample.png` — Timestamp format example
- `knowledge/YouTube timestamp sample.png` — YouTube chapter format example

### 4. Restart Claude Desktop

Quit and reopen Claude Desktop for the MCP server to connect.

---

## Before Using Cardigan

Start the API server first:

```bash
cd /Users/mriechers/Developer/ai-editorial-assistant-v3
./scripts/start.sh
```

Cardigan queries the API for job metadata. Without it running, you can still browse OUTPUT folders but won't see job details.

---

## Test It

Say hello:

> "Hello, Cardigan! What projects are ready for editing?"

---

## What's in This Folder

| File | Description |
|------|-------------|
| `CUSTOM_INSTRUCTIONS.md` | Full editor workflow, templates, PBS style rules (symlink) |
| `knowledge/` | Style guides and examples for project knowledge (symlinks) |

All files are symlinks to avoid duplication. Original files remain in their source locations.

---

## Troubleshooting

See `docs/CLAUDE_DESKTOP_SETUP.md` for detailed troubleshooting steps.

**Common issues:**
- MCP server not connecting → Check Python path in config matches your venv
- "Project not found" → Ensure API is running with `./scripts/start.sh`
- Missing context → Add knowledge files to project
