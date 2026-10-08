CREATE TABLE IF NOT EXISTS workload (
    id                  TEXT PRIMARY KEY,
    group_name          TEXT,
    asset               TEXT,
    server_name         TEXT NOT NULL,
    ip_address          TEXT,
    os                  TEXT NOT NULL,
    os_version          TEXT,
    sql_edition         TEXT,
    sql_version         TEXT,
    on_time_pct         NUMERIC(5,2),
    observed_vcpu       INTEGER NOT NULL,
    cpu_util_pct        NUMERIC(6,2) NOT NULL,
    cpu_confidence      TEXT NOT NULL DEFAULT 'point_in_time',
    mem_provisioned_gb  NUMERIC(10,2) NOT NULL,
    mem_peak_gb         NUMERIC(10,2),
    storage_gb          NUMERIC(12,2),
    iops_peak           INTEGER,
    disk_throughput_mbps NUMERIC(10,2),
    net_mbps_peak       NUMERIC(12,4),
    net_confidence      TEXT NOT NULL DEFAULT 'derived',
    raw_row             JSONB,
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS instance_sku (
    provider             TEXT NOT NULL,
    region               TEXT NOT NULL,
    instance_type        TEXT NOT NULL,
    family               TEXT,
    current_generation   BOOLEAN,
    vcpu                 INTEGER NOT NULL,
    memory_gib           NUMERIC(10,2) NOT NULL,
    architecture         TEXT,
    processor            TEXT,
    burstable            BOOLEAN,
    network_baseline_gbps NUMERIC(10,2),
    network_peak_gbps     NUMERIC(10,2),
    ebs_baseline_iops     INTEGER,
    ebs_max_iops          INTEGER,
    ebs_baseline_mbps     NUMERIC(10,2),
    ebs_max_mbps          NUMERIC(10,2),
    instance_storage_gb   NUMERIC(12,2),
    hypervisor            TEXT,
    raw_payload           JSONB NOT NULL,
    fetched_at            TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (provider, region, instance_type)
);

CREATE TABLE IF NOT EXISTS instance_price (
    provider              TEXT NOT NULL,
    region                TEXT NOT NULL,
    instance_type         TEXT NOT NULL,
    operating_system      TEXT NOT NULL,
    pre_installed_sw      TEXT NOT NULL DEFAULT 'NA',
    license_model         TEXT,
    tenancy               TEXT DEFAULT 'Shared',
    capacity_status       TEXT DEFAULT 'Used',
    purchase_option       TEXT NOT NULL DEFAULT 'on_demand',
    price_per_hour_usd    NUMERIC(12,6) NOT NULL,
    sku_code              TEXT,
    effective_date        DATE,
    raw_payload           JSONB NOT NULL,
    fetched_at            TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (provider, region, instance_type, operating_system, pre_installed_sw, purchase_option)
);

CREATE INDEX IF NOT EXISTS idx_sku_filter ON instance_sku (provider, region, vcpu, memory_gib);
CREATE INDEX IF NOT EXISTS idx_price_lookup ON instance_price (provider, region, instance_type, operating_system);

CREATE TABLE IF NOT EXISTS recommendation_run (
    id              SERIAL PRIMARY KEY,
    workload_id     TEXT NOT NULL REFERENCES workload(id),
    scenario        TEXT NOT NULL,
    region          TEXT NOT NULL,
    instance_type   TEXT,
    monthly_cost    NUMERIC(12,2),
    requirement     JSONB,
    score_breakdown JSONB,
    binding_constraints JSONB,
    created_at      TIMESTAMPTZ DEFAULT now()
);
