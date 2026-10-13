import requests

API = (
    "https://ckan0.cf.opendata.inter.prod-toronto.ca"
    "/api/3/action/package_show"
)

response = requests.get(
    API,
    params={"id": "bike-share-toronto-ridership-data"},
    timeout=60,
)
response.raise_for_status()

dataset = response.json()
if not dataset.get("success"):
    raise RuntimeError("Toronto Open Data API returned an error")

resources = dataset["result"]["resources"]

print(f"Found {len(resources)} resources:\n")

for resource in resources:
    name = resource.get("name", "")
    url = resource.get("url", "")
    fmt = resource.get("format", "")

    if "2024" in name or "2024" in url:
        print("Name:", name)
        print("Format:", fmt)
        print("URL:", url)
        print("-" * 60)
