# Demo

A walkthrough you can show in an interview or on the README.

## 1. The problem

Raw GitHub history is noisy:

```
fix auth
update calendar
add supabase migration
bug fix
readme changes
final cleanup
```

It does not communicate what was actually built.

## 2. What this system produces

Every Sunday at 20:00 UTC, an email arrives that looks roughly like:

```
Weekly Engineering Summary: 2026-05-04 - 2026-05-10

## Overview
This week, you focused on CRM scheduling, authentication migration,
and deployment cleanup across three repositories.

## Metrics
- Commits: 12
- Issues opened: 2
- Issues closed: 1
- Repositories touched: 3

## Repository Breakdown

### crm-dashboard
Most work centered on scheduling and authentication migration.

**Notable work:**
- Added Supabase schema support for installer scheduling
- Migrated Firebase Auth users into Supabase profile records
- Fixed timezone handling in Google Calendar sync

**Risks/gaps:**
- Calendar sync retry behavior still appears unfinished

## Resume Bullet Drafts
- Built CRM scheduling workflows using Supabase, Firebase Auth, and
  Google Calendar integration to support installer assignment and
  appointment management.

## Next Week
1. Add calendar sync failure tests
2. Close stale CRM scheduling issues
3. Update README setup instructions
```

## 3. How it gets there

1. **Daily collector** runs at 23:00 UTC and pulls every commit / issue
   touched in the last day across all your owned repos. Records land in
   DynamoDB; the raw GitHub responses go to a partitioned S3 archive.
2. **Weekly summarizer** runs Sunday at 20:00 UTC. It range-queries the
   activity table, builds a compact "activity_by_repo" payload, and asks
   Bedrock to produce a structured JSON report.
3. The JSON is rendered to Markdown and published via SNS to your inbox.
   The JSON and Markdown both land in the reports S3 bucket.

## 4. Why it does not hallucinate

- The system prompt enforces a strict JSON schema and explicit "do not
  exaggerate / do not claim production impact" rules.
- The summarizer overwrites the model's `weekly_metrics` with locally
  computed counts, so numbers stay correct even when the model miscounts.
- The prompt only ever sees activity that was actually collected; there
  is no upstream context that could leak invented impact claims.

## 5. Screenshots

Drop CloudWatch / SNS / generated-report screenshots into
`docs/screenshots/` and reference them here.
