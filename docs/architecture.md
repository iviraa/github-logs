# Architecture

## Goals

- Turn raw, scattered GitHub activity into a coherent weekly engineering report.
- Be cheap (serverless, on-demand DynamoDB, no always-on resources).
- Stay grounded - the LLM only summarizes data we collected, never invents impact.

## Components

### Data collection (daily)

```
EventBridge (cron 23:00 UTC)
        |
        v
github_collector_handler (Lambda)
        |
        +--> GitHub REST API (paginated, rate-limit aware)
        +--> S3 raw archive (Hive-partitioned)
        +--> DynamoDB DeveloperActivity (idempotent batch writes)
```

Idempotency: every record is keyed by `activity_id` (e.g. `commit#owner/repo#sha`)
so re-runs overwrite rather than duplicate. The Lambda overlaps the lookback
window by 2 hours to cover any clock or schedule drift.

### Summarization (weekly)

```
EventBridge (cron Sun 20:00 UTC)
        |
        v
weekly_summary_handler (Lambda)
        |
        +--> DynamoDB: range-query last 7 days
        +--> compute deterministic metrics locally
        +--> Bedrock InvokeModel: structured-JSON prompt + activity payload
        +--> S3: report.json + report.md
        +--> DynamoDB GeneratedReports: index entry
        +--> SNS: email subscriber
```

Local metrics override anything the model returns under `weekly_metrics`, so
counts stay correct even if the model miscounts.

## Data model

### `DeveloperActivity` table

```
PK: USER#<username>
SK: ACTIVITY#<yyyy-mm-dd>#<repo>#<type>#<id>
```

Range queries by date are a simple `between` over SK. Adding a per-repo GSI
later (`GSI1PK = REPO#<repo>`, `GSI1SK = DATE#...`) is cheap if needed.

### `GeneratedReports` table

```
PK: USER#<username>
SK: REPORT#weekly#<start>#<end>
```

Holds metrics + S3 keys for the JSON and Markdown report files.

### S3 layout

```
raw archive/
  github/year=2026/month=05/day=04/repo=user_repo/commits.json
  github/year=2026/month=05/day=04/repo=user_repo/issues.json

reports/
  reports/user=example-user/year=2026/end=2026-05-10/report.json
  reports/user=example-user/year=2026/end=2026-05-10/report.md
```

## Prompting

System prompt (`src/summaries/prompt_builder.py`) enforces a strict JSON shape
and explicit anti-hallucination rules. The user payload is the compact
"activity_by_repo" view rather than raw GitHub JSON, which keeps the token
budget small and the prompt focused.

## What is built vs planned

Built (MVP scaffold):
- All Python modules above
- SAM template for two Lambdas, two tables, two buckets, one SNS topic
- Daily + weekly EventBridge schedules

Planned:
- Per-repo GSI on `DeveloperActivity`
- Glue + Athena queries over the raw archive
- TODO/FIXME scanner across cloned repos
- A simple web dashboard reading from `GeneratedReports`
