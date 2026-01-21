# Maintenance Backlog

Items are worked incrementally. Any agent can pick up work.

## High Priority

(none currently - Sprint v3.1 tasks defined in SPRINT_PLAN.md)


## Normal Priority / Stray bugs and feature tweaks

- [ ] **Bug: Phase retry attempts counter not incrementing** (2026-01-21)
	- When retrying phases via the UI, the `attempts` field stays at 1 even after successful retries
	- Observed on job 169: analyst and formatter retries ran successfully but `attempts: 1` unchanged
	- The retry itself works correctly (outputs generated, previous preserved)
	- Just the counter tracking that's broken

- [ ] **Bug: Langfuse client API compatibility** (2026-01-21)
	- Warning: `'Langfuse' object has no attribute 'trace'`
	- Langfuse SDK API has changed, client needs updating
	- Non-blocking but traces aren't being recorded

- [ ] **Iterate on feature: tweaks to Resources Index template** (2026-01-12)
	- look at production vault version of template and copy those changes, just added a parameter for summaries and a few additional metadata items to the view.

- [ ] **Iterate on feature: what makes jobs fast or slow** (2026-01-12)
	- Look at job 161. What caused all the model failures, but why was the job completed so quickly?


## Low Priority / Nice to Have

- [ ] **Feature addition: Feedback via GUI* (2026-01-12)
  - Mechanism to give feedback on artifacts produced on automation. Might need to explore the best method but ideally this would happen from the projects screen. 

## Completed (Recent)

