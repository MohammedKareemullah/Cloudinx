# Cloud Migration Assessment Engine (AWS + Azure, Strands agent, FastAPI)

Deterministic engine (sizing, filtering, scoring, pricing) across AWS and Azure, a Strands
agent on Amazon Bedrock that calls it as tools, and a FastAPI wrapper for upload-and-assess
plus agent chat.

## One-time setup (Windows PowerShell)
    python -m venv .venv
    .venv\Scripts\Activate.ps1
    pip install -r requirements.txt

    $env:DATABASE_URL = "postgresql://user:pass@localhost:5432/migration_assessment"

### AWS
    aws configure                      # or set AWS_PROFILE
IAM needs ec2:DescribeInstanceTypes and pricing:GetProducts.

### Azure
    az login                           # DefaultAzureCredential picks this up automatically
    $env:AZURE_SUBSCRIPTION_ID = "<your-subscription-id>"
The identity needs Reader on the subscription (resource_skus.list is a read-only catalog call);
the pricing API (prices.azure.com) is public and needs no auth at all.

### Bedrock (for the agent)
    $env:BEDROCK_MODEL_ID = "<model or inference-profile ID enabled in your Bedrock console>"
    $env:BEDROCK_REGION = "us-east-1"
Enable the model in Bedrock console -> Model access, and allow bedrock:InvokeModel /
bedrock:InvokeModelWithResponseStream on it.

## Regions are not hardcoded
Every ingestion and recommendation call takes an explicit region, and a region/provider combo
that hasn't been ingested yet is fetched automatically on first use (engine/catalog_ensure.py) —
there's no fixed default you're stuck with. AWS additionally needs a region-code -> pricing
"location name" mapping (its two APIs use different naming schemes); add new regions to
config/aws_regions.py as needed. Azure uses the same region code everywhere, so nothing
extra is needed there.

Picking a region is not a cosmetic choice: different regions can have different instance
families available (newer families often roll out to major regions first) and always have
different prices, so the catalog is re-queried per region rather than assumed constant.

## Calibration (CPU performance ratio)
config/cpu_perf_ratio.yaml holds a per-target-family multiplier that converts on-prem CPU
demand into cloud vCPU demand (see engine/sizing.py / engine/selection.py docstrings for why
this exists — vCPU count alone is not a comparable unit across CPU generations). It's
currently calibrated from AWS data only (via scripts/calibrate_cpu_ratio.py against a
Cloudamize-style reference export); Azure families fall back to the table's default ratio
until you calibrate against an Azure-specific reference the same way:
    python -m scripts.calibrate_cpu_ratio path/to/reference_export.xlsx

## Run — CLI
    python -m scripts.init_db
    python -m scripts.run_all_ingestion --workload-file adapters/Observed-Infrastructure.xlsx `
        --aws-regions me-central-1 --aws-locations "Middle East (UAE)"
    python -m scripts.generate_migration_plan --region me-central-1 --csv-out migration_plan.csv
    python -m agent.run "Assess pwrds10 for AWS in me-central-1, all three scenarios"
    python -m agent.run            # interactive

## Run — API
    uvicorn api.main:app --reload --port 8000

    POST /assess/upload   (multipart form)
        file: the Azure Migrate-style .xlsx (Compute/Storage/Network sheets)
        provider: "aws" | "azure" | "both"
        aws_region, azure_region: optional, override the configured defaults
        scenarios: "cost,balanced,performance"
    -> returns every server's recommendation per scenario, plus a needs_review list
       (hardware-mapping fallbacks and data gaps) pulled out for manual attention.

    POST /agent/chat  { "message": "..." }  -> { "text": "..." }

    GET /providers, GET /health
