def monthly_cost(sku: dict, price_row: dict, hours_per_month: float = 730) -> dict:
    compute = price_row["price_per_hour_usd"] * hours_per_month
    return {
        "compute_monthly": round(compute, 2),
        "total_monthly": round(compute, 2),
        "os": price_row["operating_system"],
        "purchase_option": price_row.get("purchase_option", "on_demand"),
        "price_effective_date": str(price_row.get("effective_date")),
    }
