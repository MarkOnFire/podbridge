# Maintenance Backlog

Items are worked incrementally. Any agent can pick up work.

## High Priority

(none currently - Sprint v3.1 tasks defined in SPRINT_PLAN.md)


## Normal Priority / Stray bugs and feature tweaks

- [ ] **Bug/Feature: Phase retry tracking is incomplete** (2026-01-21)
	- Multiple issues observed when retrying phases via the UI (job 169):
	- [ ] `attempts` counter stays at 1 even after successful retries
	- [ ] `model` field shows stale value from original run, not the retry model
		- This makes the job detail view misleading (shows different models per phase when retries all used same model)
	- [ ] No "user requested retry" event logged anywhere
	- [ ] No progress tracking during retry execution (job appears idle)
	- **Enhancement opportunity**: Add quick feedback prompts when user triggers retry
		- Capture signal about what was wrong with original output
		- Options like: "Inaccurate", "Missing info", "Wrong format", "Hallucination", etc.
		- Store this feedback for quality analysis and model tuning decisions

- [ ] **Bug: Langfuse client API compatibility** (2026-01-21)
	- Warning: `'Langfuse' object has no attribute 'trace'`
	- Langfuse SDK API has changed, client needs updating
	- Non-blocking but traces aren't being recorded

- [ ] **Iterate on feature: tweaks to Resources Index template** (2026-01-12)
	- look at production vault version of template and copy those changes, just added a parameter for summaries and a few additional metadata items to the view.

- [ ] **Iterate on feature: what makes jobs fast or slow** (2026-01-12)
	- Look at job 161. What caused all the model failures, but why was the job completed so quickly?


## Low Priority / Nice to Have

- [ ] **Feature addition: Feedback via GUI** (2026-01-12)
  - Mechanism to give feedback on artifacts produced on automation. Might need to explore the best method but ideally this would happen from the projects screen.

## Future Vision

- [ ] **Model tier optimization based on collected data** (2026-01-21)
	- Goal: Use production data to determine optimal model placement across tiers
	- Balance cost vs quality (low failure score)
	- **Inputs needed:**
		- [ ] Model used per phase (fix: currently stale on retry)
		- [ ] Retry frequency as quality signal (fix: not tracked yet)
		- [ ] User feedback on why retry triggered
		- [ ] Manual quality ratings (optional)
	- **Metrics to derive:**
		- Cost-per-successful-output by model
		- Failure rate by model × phase combination
		- Retry rate as proxy for "bad output"
	- **Output:** Clear recommendations for which models belong in which tier
	- Depends on: fixing retry tracking bugs, adding feedback mechanism 

## Completed (Recent)

