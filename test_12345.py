import requests

API_KEY = 'FaihL1Eu7Ohla4AU39f_yQ'
company_id = 'intercom'  # Can be either organization or account ID

HEADERS = {
    "accept": "application/json",
    "Cache-Control": "no-cache",
    "Content-Type": "application/json"
}

def search_in_mixed_companies(company_id):
    print("🔍 Searching in `mixed_companies` endpoint...")
    url = "https://api.apollo.io/api/v1/mixed_companies/search"
    payload = {
        "api_key": API_KEY,
        "organization_ids": [company_id],
        "page": 1,
        "per_page": 1
    }
    response = requests.post(url, headers=HEADERS, json=payload)
    if response.status_code == 200:
        companies = response.json().get("organizations", [])
        if companies:
            company = companies[0]
            print("✅ Found in `mixed_companies`:")
            print("  Name:", company.get("name"))
            print("  Domain:", company.get("domain"))
            print("  ID:", company.get("id"))
            print("  Website:", company.get("website_url"))
            return True
    else:
        print(f"❌ Error from `mixed_companies`: {response.status_code}")
        print(response.text)
    return False

def search_in_accounts(company_id):
    print("🔍 Searching in `accounts` endpoint...")
    url = "https://api.apollo.io/api/v1/accounts/search"
    payload = {
        "api_key": API_KEY,
        "ids": [company_id],
        "page": 1,
        "per_page": 1
    }
    response = requests.post(url, headers=HEADERS, json=payload)
    if response.status_code == 200:
        accounts = response.json().get("accounts", [])
        if accounts:
            account = accounts[0]
            print("✅ Found in `accounts`:")
            print("  Name:", account.get("name"))
            print("  Domain:", account.get("domain"))
            print("  ID:", account.get("id"))
            print("  Website:", account.get("website_url"))
            return True
    else:
        print(f"❌ Error from `accounts`: {response.status_code}")
        print(response.text)
    return False

# Try both endpoints
if not search_in_mixed_companies(company_id):
    if not search_in_accounts(company_id):
        print("🚫 No company found in either endpoint.")
