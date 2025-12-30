"""Job processing worker for Editorial Assistant v3.0.

Polls the queue for pending jobs and processes them through agent phases.
"""
import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List

from api.models.job import JobStatus, JobPhase, PhaseStatus
from api.services.database import (
    get_next_job,
    update_job_status,
    update_job_phase,
    update_job_heartbeat,
    log_event,
)
from api.services.llm import (
    get_llm_client,
    start_run_tracking,
    end_run_tracking,
    LLMResponse,
)
from api.models.events import EventType, EventCreate, EventData


# Default paths
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "OUTPUT"))
TRANSCRIPTS_DIR = Path(os.getenv("TRANSCRIPTS_DIR", "transcripts"))
AGENTS_DIR = Path(".claude/agents")


class WorkerConfig:
    """Configuration for the job worker."""

    def __init__(
        self,
        poll_interval: int = 30,
        heartbeat_interval: int = 60,
        max_retries: int = 3,
    ):
        self.poll_interval = poll_interval
        self.heartbeat_interval = heartbeat_interval
        self.max_retries = max_retries


class JobWorker:
    """Processes jobs from the queue through agent phases."""

    PHASES = ["analyst", "formatter", "seo", "copy_editor"]

    def __init__(self, config: Optional[WorkerConfig] = None):
        self.config = config or WorkerConfig()
        self.llm = get_llm_client()
        self.running = False
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._current_job_id: Optional[int] = None

    async def start(self):
        """Start the worker polling loop."""
        self.running = True
        print(f"[Worker] Starting job worker (poll interval: {self.config.poll_interval}s)")

        while self.running:
            try:
                job = await get_next_job()
                if job:
                    await self.process_job(job)
                else:
                    await asyncio.sleep(self.config.poll_interval)
            except Exception as e:
                print(f"[Worker] Error in polling loop: {e}")
                await asyncio.sleep(self.config.poll_interval)

    async def stop(self):
        """Stop the worker."""
        self.running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()

    async def process_job(self, job: Dict[str, Any]):
        """Process a single job through all phases."""
        job_id = job["id"]
        self._current_job_id = job_id

        print(f"[Worker] Processing job {job_id}: {job.get('project_name', 'Unknown')}")

        # Start cost tracking for this run
        tracker = start_run_tracking(job_id)

        # Start heartbeat
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop(job_id))

        try:
            # Update job status to in_progress
            await update_job_status(job_id, JobStatus.in_progress)

            # Log job started event
            await log_event(EventCreate(
                job_id=job_id,
                event_type=EventType.job_started,
                data=EventData(extra={"project_name": job.get("project_name")}),
            ))

            # Set up project directory
            project_path = self._setup_project_dir(job)
            await update_job_status(job_id, JobStatus.in_progress, project_path=str(project_path))

            # Load transcript
            transcript_content = self._load_transcript(job)

            # Get existing phases or initialize
            phases = job.get("phases") or []
            if isinstance(phases, str):
                phases = json.loads(phases)

            # Process each phase
            context = {"transcript": transcript_content, "project_path": project_path}

            for phase_name in self.PHASES:
                # Check if phase already completed
                existing_phase = next((p for p in phases if p["name"] == phase_name), None)
                if existing_phase and existing_phase.get("status") == "completed":
                    print(f"[Worker] Skipping completed phase: {phase_name}")
                    # Load previous output for context
                    output_file = project_path / f"{phase_name}_output.md"
                    if output_file.exists():
                        context[f"{phase_name}_output"] = output_file.read_text()
                    continue

                # Update current phase
                await update_job_status(job_id, JobStatus.in_progress, current_phase=phase_name)

                # Process phase
                print(f"[Worker] Running phase: {phase_name}")
                phase_result = await self._run_phase(job_id, phase_name, context, project_path)

                # Update phases list
                phase_data = {
                    "name": phase_name,
                    "status": "completed" if phase_result["success"] else "failed",
                    "cost": phase_result.get("cost", 0),
                    "tokens": phase_result.get("tokens", 0),
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                }

                # Update or add phase
                phase_updated = False
                for i, p in enumerate(phases):
                    if p["name"] == phase_name:
                        phases[i] = phase_data
                        phase_updated = True
                        break
                if not phase_updated:
                    phases.append(phase_data)

                await update_job_phase(job_id, phases)

                if not phase_result["success"]:
                    raise Exception(f"Phase {phase_name} failed: {phase_result.get('error')}")

                # Add output to context for next phase
                context[f"{phase_name}_output"] = phase_result.get("output", "")

            # Create manifest
            await self._create_manifest(job, project_path, phases, tracker)

            # Mark job completed
            run_summary = await end_run_tracking()
            await update_job_status(
                job_id,
                JobStatus.completed,
                actual_cost=run_summary["total_cost"] if run_summary else 0,
            )

            print(f"[Worker] Job {job_id} completed successfully")

        except Exception as e:
            print(f"[Worker] Job {job_id} failed: {e}")

            # End tracking
            run_summary = await end_run_tracking()

            # Update job as failed
            await update_job_status(
                job_id,
                JobStatus.failed,
                error_message=str(e),
                actual_cost=run_summary["total_cost"] if run_summary else 0,
            )

            # Log error event
            await log_event(EventCreate(
                job_id=job_id,
                event_type=EventType.job_failed,
                data=EventData(extra={"error": str(e)}),
            ))

        finally:
            # Stop heartbeat
            if self._heartbeat_task:
                self._heartbeat_task.cancel()
                self._heartbeat_task = None
            self._current_job_id = None

    async def _heartbeat_loop(self, job_id: int):
        """Send periodic heartbeats while processing."""
        while True:
            try:
                await asyncio.sleep(self.config.heartbeat_interval)
                await update_job_heartbeat(job_id)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[Worker] Heartbeat error: {e}")

    def _setup_project_dir(self, job: Dict[str, Any]) -> Path:
        """Create and return the project output directory."""
        project_name = job.get("project_name", f"job_{job['id']}")
        # Sanitize project name for filesystem
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in project_name)

        project_path = OUTPUT_DIR / safe_name
        project_path.mkdir(parents=True, exist_ok=True)

        return project_path

    def _load_transcript(self, job: Dict[str, Any]) -> str:
        """Load the transcript file content."""
        transcript_file = job.get("transcript_file", "")

        # Try various paths
        paths_to_try = [
            Path(transcript_file),
            TRANSCRIPTS_DIR / transcript_file,
            TRANSCRIPTS_DIR / Path(transcript_file).name,
        ]

        for path in paths_to_try:
            if path.exists():
                return path.read_text()

        raise FileNotFoundError(f"Transcript not found: {transcript_file}")

    async def _run_phase(
        self,
        job_id: int,
        phase_name: str,
        context: Dict[str, Any],
        project_path: Path,
    ) -> Dict[str, Any]:
        """Run a single agent phase."""
        try:
            # Get backend for this phase
            backend = self.llm.get_backend_for_phase(phase_name)

            # Load system prompt
            system_prompt = self._load_agent_prompt(phase_name)

            # Build user message with context
            user_message = self._build_phase_prompt(phase_name, context)

            # Log phase started
            await log_event(EventCreate(
                job_id=job_id,
                event_type=EventType.phase_started,
                data=EventData(phase=phase_name, backend=backend),
            ))

            # Call LLM
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ]

            response: LLMResponse = await self.llm.chat(
                messages=messages,
                backend=backend,
                job_id=job_id,
            )

            # Save output
            output_file = project_path / f"{phase_name}_output.md"
            output_file.write_text(response.content)

            # Log phase completed
            await log_event(EventCreate(
                job_id=job_id,
                event_type=EventType.phase_completed,
                data=EventData(
                    phase=phase_name,
                    cost=response.cost,
                    tokens=response.total_tokens,
                    model=response.model,
                ),
            ))

            return {
                "success": True,
                "output": response.content,
                "cost": response.cost,
                "tokens": response.total_tokens,
                "model": response.model,
            }

        except Exception as e:
            await log_event(EventCreate(
                job_id=job_id,
                event_type=EventType.phase_failed,
                data=EventData(phase=phase_name, extra={"error": str(e)}),
            ))
            return {"success": False, "error": str(e)}

    def _load_agent_prompt(self, phase_name: str) -> str:
        """Load the system prompt for an agent phase."""
        prompt_file = AGENTS_DIR / f"{phase_name}.md"

        if prompt_file.exists():
            return prompt_file.read_text()

        # Fallback prompts if files don't exist
        fallback_prompts = {
            "analyst": """You are a transcript analyst for PBS Wisconsin. Your role is to analyze raw video transcripts and identify:

1. Key topics and themes discussed
2. Speaker identification and roles
3. Important quotes and timestamps
4. Structural elements (segments, transitions)
5. Items that may need human review (unclear audio, names to verify)

Output a detailed analysis document in markdown format that will guide the formatting and SEO agents.""",

            "formatter": """You are a transcript formatter for PBS Wisconsin. Your role is to transform raw transcripts into clean, readable markdown documents.

Guidelines:
- Use proper speaker attribution (SPEAKER NAME:)
- Create logical paragraph breaks
- Preserve important timestamps
- Fix obvious transcription errors
- Maintain the original meaning and voice

Output a clean, well-formatted markdown transcript.""",

            "seo": """You are an SEO specialist for PBS Wisconsin streaming content. Your role is to generate search-optimized metadata for video content.

Generate:
1. Title (compelling, keyword-rich, under 60 chars)
2. Short description (1-2 sentences, 150 chars)
3. Long description (2-3 paragraphs, engaging)
4. Tags (10-15 relevant keywords)
5. Categories

Output as JSON with keys: title, short_description, long_description, tags, categories""",

            "copy_editor": """You are a copy editor for PBS Wisconsin. Your role is to review and refine formatted transcripts for broadcast quality.

Focus on:
- Grammar and punctuation
- Clarity and readability
- PBS style guidelines
- Consistency in formatting
- Preserving speaker voice while improving prose

Output the polished transcript with any notes on changes made.""",
        }

        return fallback_prompts.get(phase_name, f"You are the {phase_name} agent. Process the input and provide appropriate output.")

    def _build_phase_prompt(self, phase_name: str, context: Dict[str, Any]) -> str:
        """Build the user prompt for a phase with relevant context."""
        transcript = context.get("transcript", "")

        if phase_name == "analyst":
            return f"""Please analyze the following transcript:

---
{transcript}
---

Provide a detailed analysis document."""

        elif phase_name == "formatter":
            analysis = context.get("analyst_output", "")
            return f"""Using the following analysis as guidance:

---
{analysis}
---

Please format this transcript:

---
{transcript}
---"""

        elif phase_name == "seo":
            analysis = context.get("analyst_output", "")
            formatted = context.get("formatter_output", "")
            return f"""Based on this analysis:

---
{analysis}
---

And this formatted transcript:

---
{formatted[:2000]}...
---

Generate SEO metadata as JSON."""

        elif phase_name == "copy_editor":
            formatted = context.get("formatter_output", "")
            return f"""Please review and polish this formatted transcript:

---
{formatted}
---

Apply PBS style guidelines and improve readability while preserving speaker voice."""

        return f"Process the following:\n\n{transcript}"

    async def _create_manifest(
        self,
        job: Dict[str, Any],
        project_path: Path,
        phases: List[Dict[str, Any]],
        tracker,
    ):
        """Create a manifest file for the completed project."""
        manifest = {
            "job_id": job["id"],
            "project_name": job.get("project_name"),
            "transcript_file": job.get("transcript_file"),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "phases": phases,
            "total_cost": tracker.total_cost if tracker else 0,
            "total_tokens": tracker.total_tokens if tracker else 0,
            "outputs": {
                "analysis": "analyst_output.md",
                "formatted_transcript": "formatter_output.md",
                "seo_metadata": "seo_output.md",
                "copy_edited": "copy_editor_output.md",
            },
        }

        manifest_file = project_path / "manifest.json"
        manifest_file.write_text(json.dumps(manifest, indent=2))


# CLI entry point
async def run_worker():
    """Run the worker as a standalone process."""
    worker = JobWorker()
    try:
        await worker.start()
    except KeyboardInterrupt:
        await worker.stop()


if __name__ == "__main__":
    asyncio.run(run_worker())
