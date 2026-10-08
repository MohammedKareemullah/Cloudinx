# Cloudinx — Cloud Migration Assessment (Frontend)

React (Vite) frontend for the cloud migration assessment backend. Built against the backend's actual
captured API responses, not an assumed contract — see "Backend contract" below.

## Run it

```bash
npm install
cp .env.example .env     # VITE_API_BASE_URL=http://localhost:8000 — point this at your backend
npm run dev
```

Open the printed local URL (default `http://localhost:5173`). The backend must be running and
reachable at `VITE_API_BASE_URL` with CORS enabled for this origin.

Build for production with `npm run build` (outputs to `dist/`); serve that directory with any static
file server, or point your own reverse proxy at it.

## Screens

1. **Upload** — drop/select the on-prem discovery export (`.xlsx`, Compute/Storage/Network sheets).
2. **Configure** — provider (AWS / Azure / Both), region(s) — pre-filled from the backend's
   `GET /providers` default, editable/free-text since the backend only exposes one default per
   provider, not a full region list — and which scenarios to run (cost / balanced / performance).
3. **Results** — per-server table: top recommended instance per scenario (type, vCPU, memory, monthly
   cost), a `fallback` badge when the backend had to fall back to a hardware-mapping/nearest-fit pick,
   and "No viable instance found" when a scenario genuinely has no recommendation. Expand any row for
   the full requirement breakdown (CPU/memory/IOPS/disk/network demand + confidence + data-quality
   notes), the chosen instance's full spec and score breakdown, and up to 3 ranked alternatives.
   **Export to Excel** downloads a multi-sheet workbook (summary + one sheet per scenario + a derived
   "Needs Review" sheet when the backend doesn't supply one).
4. **Ask the agent** — chat UI wired to `POST /agent/chat`. This endpoint wasn't present in the
   backend's documented API surface at the time this was built; the page calls it with the
   conventional `{message, history}` shape and parses the reply defensively from whichever key the
   backend returns (`text`, `response`, `answer`, `reply`, `message`, `output`, or `content`). If the
   route doesn't exist yet, the page shows a clear "not available yet" message instead of crashing —
   once the backend adds the route, this page works with no frontend changes.

## Backend contract (as actually observed)

```
GET  /health              -> { "status": "ok" }
GET  /providers           -> { "aws": { "default_region": "us-east-1" },
                                "azure": { "default_region": "eastus" } }
POST /assess/upload       -> multipart form: file, provider, aws_region, azure_region,
                              scenarios ("cost,balanced,performance"), group_name
```

`/assess/upload` response shape:

```jsonc
{
  "workload_count": 128,
  "targets": [{ "provider": "aws", "region": "us-east-1" }],
  "scenarios": ["cost", "balanced", "performance"],
  "needs_review": [],
  "results": [
    {
      "workload_id": "pwrds10.ADmLbJ...",
      "server_name": "pwrds10",
      "scenarios": {
        "cost": {
          "requirement": {
            "cpu_demand_cores": 6.88, "mem_gb": 23.4, "iops": 255, "disk_mbps": 93.1,
            "net_gbps": 0.0004, "confidence": "low", "notes": ["...", "..."]
          },
          "top_choice": {
            "provider": "aws", "region": "us-east-1", "instance_type": "r5a.xlarge",
            "family": "r5a", "vcpu": 4, "memory_gib": 32, "architecture": "x86_64",
            "processor": "AMD", "burstable": false,
            "network_baseline_gbps": 1.25, "network_peak_gbps": 10,
            "ebs_baseline_iops": 6000, "ebs_max_iops": 16000,
            "ebs_baseline_mbps": 135.63, "ebs_max_mbps": 360,
            "instance_storage_gb": null, "compute_monthly": 164.98, "total_monthly": 164.98,
            "os": "Windows", "purchase_option": "on_demand", "price_effective_date": "2026-09-01",
            "score_breakdown": { "cost": 1, "fit": 0.667, "perf": 1, "affinity": 0.5 },
            "total_score": 0.8333
          },
          "alternatives": [ /* same shape as top_choice, up to a few entries */ ],
          "hardware_mapping": false
        },
        "balanced": { /* same shape */ },
        "performance": { /* same shape */ }
      }
    }
  ]
}
```

Notes the frontend relies on:

- Each workload's scenarios are keyed under `"scenarios"` (not `"results"`), one entry per requested
  scenario — `requirement` / `top_choice` / `alternatives` / `hardware_mapping`.
- `top_choice` can be `null` (genuinely no viable instance for that scenario) — rendered as
  "No viable instance found", counted in "Needs review", and excluded from the cost totals.
- `hardware_mapping: true` means the backend fell back to a nearest-fit pick rather than a SKU that
  passed every hard filter — rendered with a `fallback` badge, still shown as a usable recommendation
  but also counted in "Needs review".
- `needs_review` at the top level may be empty even when individual scenarios need review (as in the
  real capture used to build this) — the frontend derives its own review list/count from each row's
  scenarios rather than trusting that array alone, and only uses the backend's list when non-empty for
  the exported "Needs Review" sheet.
- `/assess/upload` on a real fleet can take minutes (scoring every server against live AWS/Azure
  pricing) — the HTTP client has no request timeout, and the Configure page shows an elapsed-time
  indicator instead of appearing stuck.

If the real backend's shape ever changes, the two places to update are `src/api/client.js` (request/
response plumbing) and the `ScenarioCell` / `stats` logic in `src/pages/ResultsPage.jsx` plus
`src/utils/exportExcel.js` (rendering and export).
