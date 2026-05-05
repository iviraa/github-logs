# github-logs

Collects your commit/issue/repo activity daily, stores normalized records
in DynamoDB, and uses Amazon Bedrock to generate a structured weekly
engineering report delivered by email. A separate monthly retrospective
runs Athena queries over a partitioned S3 data lake for longer-horizon
analytics.

## Stack

| Layer | Service |
|---|---|
| Triggers | EventBridge |
| Compute | Lambda (Python 3.12, arm64) |
| Operational store | DynamoDB |
| Data lake | S3 (Hive-partitioned) |
| Schema discovery | Glue Crawler + Glue Data Catalog |
| Analytics | Athena |
| LLM | Bedrock (Claude Haiku) |
| Auth | Secrets Manager |
| Notification | SNS + email subscription |
| IaC | AWS SAM |

## Repo layout

```
src/
  collectors/      GitHub fetch + normalization
  storage/         DynamoDB, S3, Athena access
  summaries/       Prompt builders, Bedrock client, formatters, orchestrators
  notifications/   SNS publisher
  common/          Config, logger, date helpers
lambdas/           Lambda entry points
infrastructure/    SAM template + parameters
scripts/           One-shot utilities
sample_data/       Fixture JSON for prompt iteration
```

## Local setup

```sh
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp infrastructure/parameters.example.json infrastructure/parameters.json
# fill in your values; parameters.json is gitignored
```

## Deploy

Prereqs: AWS CLI configured, SAM CLI installed, GitHub PAT stored in
Secrets Manager, Bedrock inference profile granted in your region.

```sh
make deploy
```

After the first deploy, confirm the SNS subscription email AWS sends to the
address in `parameters.json`.

## Configuration

`infrastructure/parameters.json`:

| Key | Meaning |
|---|---|
| `GitHubUsername` | Your GitHub login |
| `GitHubSecretArn` | ARN of the Secrets Manager secret holding the PAT |
| `NotificationEmail` | Inbox that receives reports |
| `BedrockModelId` | Cross-region inference profile id |
| `Region` | AWS region for the stack |

