import requests
import time

API_KEY = 'FaihL1Eu7Ohla4AU39f_yQ'
search_term = 'https://grasshopperasia.com/'  # Company name or domain
per_page = 10
max_pages = 15
company_url = 'https://api.apollo.io/api/v1/mixed_companies/search'
people_url = 'https://api.apollo.io/v1/people/search'
headers = {'Content-Type': 'application/json'}

# Step 1: Search for the company in organizations
for page in range(1, max_pages + 1):
    print(f"\n📄 Fetching page {page} for '{search_term}'...")
    payload = {
        'api_key': API_KEY,
        'q_organization_name': search_term,
        'page': page,
        'per_page': per_page
    }

    response = requests.post(company_url, headers=headers, json=payload)

    if response.status_code != 200:
        print(f"❌ API error: {response.status_code}")
        print(response.text)
        break

    data = response.json()
    orgs = data.get('organizations', [])
    
    if not orgs:
        print("🚫 No more organizations found.")
        break

    for org in orgs:
        org_id = org.get("id")
        name = org.get("name")
        domain = org.get("domain")
        print(f"\n✅ Organization: {name} ({domain}) - ID: {org_id}")

        # Step 2: Fetch people with filters (seniorities and optional departments)
        people_payload = {
            'api_key': API_KEY,
            'organization_ids': [org_id],
            'page': 1,
            'per_page': 50,
            #'person_seniorities': ['owner', 'founder', 'c-suite'],
             #'departments': ['marketing']  # Optional: remove this line if not needed
             'person_titles': [
                               'ceo',
                               'founder',
                               'co-founder',
                               'cmo',
                               'head of marketing',
                               'marketing director',
                               'vp marketing',
                               'growth',
                               'head of growth',
                               'growth manager',
                               'marketing manager',
                               'brand manager',
                               'chief growth officer',
                               'head of digital',
                               'digital marketing',
                               'ecommerce',
                               'acquisition',
                               'user acquisition',
                               'performance marketing',
                               'business development',
                               'bd manager',
                               'vp business development',
                               'partnerships',
                               'head of strategy',
                               'chief digital officer',
                               'innovation manager',
                               'digital transformation',
                               'content director',
                               'media buying',
                               'head of brand',

                           ]
        }

        people_response = requests.post(people_url, headers=headers, json=people_payload)

        if people_response.status_code != 200:
            print(f"❌ Error fetching people: {people_response.status_code}")
            print(people_response.text)
            continue

        people = people_response.json().get('people', [])
        if not people:
            print("👥 No people found matching filters.")
        else:
            print(f"👥 Found {len(people)} people:")
            for p in people:
                print(f" - {p.get('first_name')} {p.get('last_name')} | {p.get('title')} | {p.get('linkedin_url')}")

    time.sleep(1)

print("\n✅ Done.")
