import requests

API_KEY = 'FaihL1Eu7Ohla4AU39f_yQ'
COMPANY_DOMAIN = 'gingerhospitality.co.uk'
TITLES = ['CEO', 'ceo']
API_URL = 'https://api.apollo.io/api/v1/mixed_people/search'

HEADERS = {
    'Content-Type': 'application/json',
    
}

def search_people_by_title(domain, title):
    payload = {
        'api_key': API_KEY,
        'organization_domains': [domain],  # strict filter
        'title': title,
        'page': 1,
        'per_page': 10  # You can paginate if you expect many results
    }

    response = requests.post(API_URL, headers=HEADERS, json=payload)

    if response.status_code == 200:
        data = response.json()
        people = data.get('people', [])
        return people
    else:
        print(f"❌ Error {response.status_code}: {response.text}")
        return []

def main():
    for title in TITLES:
        print(f"\n🔎 Searching for: {title} at {COMPANY_DOMAIN}")
        people = search_people_by_title(COMPANY_DOMAIN, title)

        if not people:
            print("🚫 No results found.")
            continue

        for person in people:
            org = person.get('organization', {})
            print("✅ Found:")
            print("  Name:", person.get("name"))
            print("  Title:", person.get("title"))
            print("  LinkedIn:", person.get("linkedin_url"))
            print("  Email Verified:", person.get("email_status"))
            print("  Twitter:", person.get("twitter_url"))
            print("  Company Name:", org.get("name"))
            print("  Company Website:", org.get("website_url") or f"https://{org.get('domain')}")

            print("-" * 40)

if __name__ == "__main__":
    main()
