"""
Run with: uvicorn api.main:app --reload --port 8000

Endpoints:
  POST /assess/upload   — upload an Azure Migrate-style xlsx, get a full migration plan
  POST /agent/chat      — talk to the Strands/Bedrock agent
  GET  /providers       — which providers/regions are already cached
  GET  /health
"""
import tempfile
import shutil
import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from api.schemas import ChatRequest

from config.settings import DEFAULT_ASSESSMENT_REGION, DEFAULT_AZURE_REGION
from adapters.azure_migrate_xlsx import build_workloads
from scripts.ingest_workloads import run as ingest_workloads_from_path
from engine.catalog_ensure import ensure_catalog
from tools.tool_defs import recommend_instances
from db import repository as repo
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Cloud Migration Assessment API")


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/providers")
def providers():
    return {
        "aws": {"default_region": DEFAULT_ASSESSMENT_REGION},
        "azure": {"default_region": DEFAULT_AZURE_REGION},
    }


def _targets_from_provider(provider: str, aws_region: str | None, azure_region: str | None) -> list[dict]:
    aws_region = aws_region or DEFAULT_ASSESSMENT_REGION
    azure_region = azure_region or DEFAULT_AZURE_REGION
    if provider == "both":
        return [{"provider": "aws", "region": aws_region}, {"provider": "azure", "region": azure_region}]
    if provider == "azure":
        return [{"provider": "azure", "region": azure_region}]
    return [{"provider": "aws", "region": aws_region}]


@app.post("/assess/upload")
async def assess_upload(
    file: UploadFile = File(...),
    provider: str = Form("aws"),
    aws_region: str | None = Form(None),
    azure_region: str | None = Form(None),
    scenarios: str = Form("cost,balanced,performance"),
    group_name: str | None = Form(None),
):
    if provider not in ("aws", "azure", "both"):
        raise HTTPException(400, "provider must be 'aws', 'azure', or 'both'")

    scenario_list = [s.strip() for s in scenarios.split(",") if s.strip()]
    targets = _targets_from_provider(provider, aws_region, azure_region)

    # Validate the file parses BEFORE touching the DB, so a bad upload fails fast and clearly.
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
    try:
        try:
            parsed = build_workloads(tmp_path)
        except Exception as e:
            raise HTTPException(422, f"Could not parse the uploaded file as an Azure Migrate-style "
                                      f"export (Compute/Storage/Network sheets expected): {e}")
        if not parsed:
            raise HTTPException(422, "The uploaded file parsed but contained no server rows.")

        ingest_workloads_from_path(tmp_path)

        for t in targets:
            try:
                ensure_catalog(t["provider"], t["region"])
            except Exception as e:
                raise HTTPException(502, f"Could not prepare catalog/pricing for "
                                          f"{t['provider']}/{t['region']}: {e}")

        results = []
        for w in parsed:
            row = {"workload_id": w["id"], "server_name": w["server_name"]}
            rec = recommend_instances(
                w["id"],
                provider=(provider if provider != "both" else ""),
                aws_region=targets[0]["region"] if provider in ("aws", "both") else "",
                azure_region=(targets[-1]["region"] if provider in ("azure", "both") else ""),
                scenarios=scenario_list,
            )
            row["scenarios"] = rec.get("scenarios", rec)
            results.append(row)

        needs_review = [
            {"server_name": r["server_name"], "scenario": sc, "reason": d.get("error") or d.get("diagnosis")}
            for r in results for sc, d in r["scenarios"].items()
            if d.get("error") or d.get("hardware_mapping")
        ]

        return JSONResponse({
            "workload_count": len(results),
            "targets": targets,
            "scenarios": scenario_list,
            "needs_review": needs_review,
            "results": results,
        })
    finally:
        os.unlink(tmp_path)


@app.post("/agent/chat")
def agent_chat(req: ChatRequest):
    from agent.strands_agent import build_agent
    agent = build_agent()
    try:
        response = agent(req.message)
    except Exception as e:
        raise HTTPException(502, f"Agent call failed: {e}")
    return {"text": str(response)}

