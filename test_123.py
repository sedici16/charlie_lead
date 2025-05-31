import requests
import time

API_KEY = 'FaihL1Eu7Ohla4AU39f_yQ'
search_term = 'intercom.com'  # <--- Any string to search by name

per_page = 10   # Typically 10 is max for /mixed_companies/search
max_pages = 50  # Adjust as needed
url = 'https://api.apollo.io/api/v1/mixed_companies/search'
headers = {'Content-Type': 'application/json'}

for page in range(1, max_pages + 1):
    print(f"\n📄 Fetching page {page} for '{search_term}'...")
    payload = {
        'api_key': API_KEY,
        'q_organization_name': search_term,
       # "domains": ["gingerhospitality.co.uk"],
         #'countries': ['United Kingdom'],
        'page': page,
        'per_page': per_page
    }

    response = requests.post(url, headers=headers, json=payload)

    # Check for a valid status code
    if response.status_code != 200:
        print(f"❌ API error: {response.status_code}")
        print(response.text)
        break

    data = response.json()

    # Apollo may return companies in "organizations" or "accounts"
    companies = data.get('organizations', []) + data.get('accounts', [])
    
    if not companies:
        print("🚫 No more companies found.")
        break
    
    # Print out each company's details
    for org in companies:
        print("✅ Found company:")
        print("  Name:", org.get("name"))
        print("  Domain:", org.get("domain"))
        print("  ID:", org.get("id"))
        print("  Website:", org.get("website_url"))
        print("-" * 50)

    # Polite delay to avoid rate-limit issues
    time.sleep(1)

print("\n✅ Done.")
