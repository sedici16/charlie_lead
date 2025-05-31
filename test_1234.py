import requests

API_KEY = 'FaihL1Eu7Ohla4AU39f_yQ'
company_id = '673e262b386a2401b0b5ddc3'
url = "https://api.apollo.io/api/v1/mixed_companies/search"

headers = {
    "accept": "application/json",
    "Cache-Control": "no-cache",
    "Content-Type": "application/json"
}

payload = {
    "api_key": API_KEY,
    "organization_ids": [company_id],
    "page": 1,
    "per_page": 1
}

response = requests.post(url, headers=headers, json=payload)

if response.status_code == 200:
    companies = response.json().get("organizations", [])
    print (companies)
    if companies:
        company = companies[0]
        print("✅ Found company:")
        print("  Name:", company.get("name"))
        print("  Domain:", company.get("domain"))
        print("  ID:", company.get("id"))
        print("  Website:", company.get("website_url"))
    else:
        print("🚫 No company found with that ID.")
else:
    print(f"❌ API error: {response.status_code}")
    print(response.text)
