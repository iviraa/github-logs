.PHONY: install lint fmt build deploy invoke-collector invoke-summary clean

install:
	pip install -r requirements.txt -r requirements-dev.txt

lint:
	ruff check src lambdas
	mypy src lambdas

fmt:
	ruff format src lambdas
	ruff check --fix src lambdas

build:
	sam build -t infrastructure/template.yaml

deploy: build
	sam deploy -t infrastructure/template.yaml \
		--stack-name github-logs \
		--capabilities CAPABILITY_IAM \
		--resolve-s3 \
		--parameter-overrides $$(jq -r 'to_entries | map("\(.key)=\(.value)") | join(" ")' infrastructure/parameters.json)

invoke-collector:
	sam local invoke GitHubCollectorFunction \
		-t infrastructure/template.yaml \
		-e events/daily_collect.json

invoke-summary:
	sam local invoke WeeklySummaryFunction \
		-t infrastructure/template.yaml \
		-e events/weekly_summary.json

clean:
	rm -rf .aws-sam .mypy_cache .ruff_cache __pycache__
	find . -type d -name __pycache__ -exec rm -rf {} +
