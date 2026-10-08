import os

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:SattiPaanai%4005@localhost:5490/cloud_migration_tool_db",
)

# The region(s) to pull AWS catalog/price data for. This MUST include your real target
# migration region(s) — sizing/pricing only works for regions you've actually ingested.
AWS_REGIONS = os.environ.get("AWS_REGIONS", "us-east-1").split(",")
AWS_LOCATIONS = os.environ.get("AWS_LOCATIONS", "US East (N. Virginia)").split(",")
# The region used by default when a tool call doesn't specify one. Set this to your real
# target region (e.g. "me-central-1") once you've ingested it — us-east-1 is just a placeholder.
DEFAULT_ASSESSMENT_REGION = os.environ.get("DEFAULT_ASSESSMENT_REGION", "us-east-1")

# Catalog filtering: a DENYLIST of family-name prefixes to exclude, not an allowlist.
# An allowlist goes stale every time AWS ships a new generation (this is exactly the bug
# that caused "no candidates" for most nodes — r8i-flex/r8a/m8a/t3a weren't on the old list).
# A denylist only needs updating when you want to exclude a whole new category on purpose.
CATALOG_FAMILY_DENYLIST_PREFIXES = os.environ.get(
    "CATALOG_FAMILY_DENYLIST_PREFIXES",
    "u-,u7i,mac,dl1,dl2,p2,p3,p4,p5,g3,g4,g5,g6,trn,inf,hpc,f1,vt1"
).split(",")

CPU_PERF_RATIO_PATH = os.environ.get("CPU_PERF_RATIO_PATH", "config/cpu_perf_ratio.yaml")

# Family-affinity thresholds: mem_gb-per-vCPU ratio above which a memory-optimized family
# is preferred, and below which a compute-optimized family is preferred. Between the two,
# general purpose is preferred. Calibrated loosely against common AWS family ratios
# (general purpose ~4 GiB/vCPU, memory-optimized ~8 GiB/vCPU, compute-optimized ~2 GiB/vCPU).
MEM_PER_VCPU_MEMORY_OPTIMIZED_THRESHOLD = float(os.environ.get("MEM_RATIO_MEMOPT_THRESHOLD", "6.0"))
MEM_PER_VCPU_COMPUTE_OPTIMIZED_THRESHOLD = float(os.environ.get("MEM_RATIO_COMPUTEOPT_THRESHOLD", "2.5"))

GENERAL_PURPOSE_FAMILY_PREFIXES = ("m",)
MEMORY_OPTIMIZED_FAMILY_PREFIXES = ("r", "x")
COMPUTE_OPTIMIZED_FAMILY_PREFIXES = ("c",)
BURSTABLE_FAMILY_PREFIXES = ("t",)

# --- Bedrock / Strands ---
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0")
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "us-east-1")
BEDROCK_TEMPERATURE = float(os.environ.get("BEDROCK_TEMPERATURE", "0.2"))
BEDROCK_MAX_TOKENS = int(os.environ.get("BEDROCK_MAX_TOKENS", "4000"))

# --- Azure ---
AZURE_SUBSCRIPTION_ID = os.environ.get("AZURE_SUBSCRIPTION_ID", "")
# Azure's region code (e.g. "eastus") is used identically by both the catalog and pricing
# APIs — unlike AWS, which needs config/aws_regions.py to bridge two different naming schemes.
DEFAULT_AZURE_REGION = os.environ.get("DEFAULT_AZURE_REGION", "eastus")
DEFAULT_PROVIDER = os.environ.get("DEFAULT_PROVIDER", "aws")  # "aws" | "azure"
