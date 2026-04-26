# github-logs

Serverless GitHub activity intelligence on AWS. Collects your commit/issue/repo
activity daily, stores normalized records in DynamoDB, and uses Amazon Bedrock
to generate a structured weekly engineering report delivered by email.

## Architecture

```
EventBridge (daily 23:00 UTC) ─▶ github_collector_handler (Lambda)
                                         │
                                         ├─▶ GitHub REST API
                                         ├─▶ DynamoDB: DeveloperActivity
                                         └─▶ S3: raw archive (partitioned)

EventBridge (Sun 20:00 UTC)   ─▶ weekly_summary_handler (Lambda)
                                         │
                                         ├─▶ DynamoDB: DeveloperActivity (query)
                                         ├─▶ Amazon Bedrock (Claude)
                                         ├─▶ DynamoDB: GeneratedReports
                                         ├─▶ S3: reports (json + md)
                                         └─▶ SNS: email summary
```

See `docs/architecture.md` for the long form.

## Layout

```
src/                Python modules (imported by Lambda handlers)
  collectors/       GitHub API fetch + normalization
  storage/          DynamoDB and S3 access
  summaries/        Prompt building, Bedrock invocation, formatting
  notifications/    SNS email publisher
  common/           Config, logger, date helpers
lambdas/            Lambda entry points (handlers)
infrastructure/     SAM template + parameters
sample_data/        Fixture JSON for prompt iteration
```

## Local setup

```sh
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env   # then fill in values
make lint
```

## Deploy

Prereqs: AWS CLI configured, SAM CLI installed, a GitHub PAT stored in Secrets
Manager (the secret ARN goes into `infrastructure/parameters.json`).

```sh
sam build -t infrastructure/template.yaml
sam deploy -t infrastructure/template.yaml \
  --parameter-overrides $(cat infrastructure/parameters.json | jq -r 'to_entries | map("\(.key)=\(.value)") | join(" ")') \
  --capabilities CAPABILITY_IAM \
  --stack-name github-logs \
  --resolve-s3
```

After first deploy, confirm the SNS email subscription that arrives at the
configured email address.

## Configuration

Edit `infrastructure/parameters.json`:

| Key | Meaning |
|---|---|
| `GitHubUsername` | Your GitHub login |
| `GitHubSecretArn` | ARN of Secrets Manager secret holding the PAT |
| `NotificationEmail` | Address that receives the weekly email |
| `BedrockModelId` | Bedrock model id, e.g. a Claude Sonnet/Opus id in your region |
| `Region` | AWS region for deploy |

## Status

MVP scaffold. See `docs/architecture.md` for what is built vs planned.
