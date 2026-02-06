# Agent Roles — Podbridge

Overview of the AI and automated agent roles within the Podbridge pipeline dashboard.

## 1. Pipeline Stage Runners

Automated agents that process podcast content through pipeline stages:

- **Transcription**: Processes raw audio to generate transcripts (coordinated via `podcast-whisper-transcription` sibling)
- **Publisher**: Pushes content from PRX feeds to Ghost CMS (via `prx-to-ghost-publisher` sibling)
- **Audiogram Generator**: Creates animated video audiograms (via `audiogram-tools` sibling)
- **Social Distributor**: Distributes content to social platforms (via `robo-social` sibling)

## 2. Dashboard Agents

Agents that operate within the Podbridge dashboard itself:

- **Analyst**: Processes transcripts to generate draft metadata (titles, descriptions, keywords)
- **Formatter**: Reformats raw transcripts according to style conventions
- **Timestamp Generator**: Creates timestamp/chapter files for long-form content

## 3. Development Agents

- **Claude Code**: Primary development agent for the Podbridge codebase
