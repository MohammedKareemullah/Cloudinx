"""
AWS's Pricing API (get_products) is keyed by a human-readable 'location' string, while
describe_instance_types and everything else uses the region CODE. These don't convert
into each other programmatically, so we keep a small explicit map. Add a region here the
first time you use it; ensure_catalog will tell you exactly this if a region is missing.
"""
AWS_REGION_LOCATION_NAMES = {
    "us-east-1": "US East (N. Virginia)",
    "us-east-2": "US East (Ohio)",
    "us-west-2": "US West (Oregon)",
    "eu-west-1": "EU (Ireland)",
    "eu-central-1": "EU (Frankfurt)",
    "ap-south-1": "Asia Pacific (Mumbai)",
    "ap-southeast-1": "Asia Pacific (Singapore)",
    "me-central-1": "Middle East (UAE)",
    "me-south-1": "Middle East (Bahrain)",
}
