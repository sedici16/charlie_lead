import requests, json, csv
from pymongo import MongoClient

API_KEY = 'FaihL1Eu7Ohla4AU39f_yQ'

MONGO_URI = "mongodb+srv://gab_lead:jGQMefKw4RFr2mwS@cluster0.t2s7w4o.mongodb.net/?retryWrites=true&w=majority"


client = MongoClient(MONGO_URI)
db = client["apollo_leads"]
collection = db["contacts"]

company_domains = [
    'google.com',
]

#job_titles = [
#    'ceo', 'chief executive officer', 'owner', 'founder', 'co-founder',
#    'head of marketing', 'cmo', 'head of business development', 'head of sales',
#    'vp of business development', 'vp of sales and marketing', 'vp of marketing',
#    'vice president of business development', 'vice president of sales and marketing',
#    'vice president of marketing', 'director of marketing', 'director of business development',
#    'marketing director', 'vp of product', 'president and ceo', 'coo',
#    'senior vice president sales', 'senior vice president business development',
#    'senior vice president marketing', 'svp sales', 'svp business development',
#    'svp marketing', 'cto', 'chief technology officer', 'head of brand', 'svp of product',
#    'vice president', 'tech lead', 'head of product'
#]

job_titles = [
    'ceo']

headers = {'Content-Type': 'application/json'}
company_url = 'https://api.apollo.io/api/v1/mixed_companies/search'
people_url = 'https://api.apollo.io/v1/people/search'

def fetch_company(domain):
    payload = {'api_key': API_KEY, 'q_organization_name': domain, 'page': 1, 'per_page':1}
    response = requests.post(company_url, headers=headers, data=json.dumps(payload))
    if response.status_code != 200:
        print(f'❌ Error fetching company for {domain}: {response.text}')
        return None
    data = response.json()
    companies = data.get('organizations', [])
    if not companies:
        print(f'❌ No company found for {domain}')
        return None
    return companies[0]

def fetch_employees(company_id):
    payload = {
        'api_key': API_KEY,
        'organization_ids': [company_id],
        'page': 1,
        'per_page': 20,
        'job_titles': job_titles
    }
    response = requests.post(people_url, headers=headers, data=json.dumps(payload))
    if response.status_code != 200:
        print(f'❌ Error fetching employees: {response.text}')
        return []
    data = response.json()
    return data.get('people', [])

def collect_contacts(domains):
    contacts = []
    for domain in domains:
        company = fetch_company(domain)
        if not company:
            continue
        company_id = company.get('id')
        company_name = company.get('name')
        print(f'\n✅ Found company: {company_name} (ID: {company_id}) for domain {domain}')
        people = fetch_employees(company_id)
        print(f'Found {len(people)} matching employees at {company_name}:\n')
        for person in people:
            first = person.get('first_name', '').strip()
            last = person.get('last_name', '').strip()
            name = f'{first} {last}'
            title = person.get('title', 'N/A')
            linkedin = person.get('linkedin_url', 'N/A')
            email_status = person.get('email_status', 'unknown')
            email = get_personal_email(first, last, domain)
            print(f'- {name}')
            print(f'  Title: {title}')
            print(f'  LinkedIn: {linkedin}')
            print(f'  Email Verified: {email_status}\n')
            print(f"  Email: {email or 'Not available'}\n")
            
            contact = {
                "first_name": first,
                "last_name": last,
                "domain": domain,
                "email": email or "",
                "title": title,
                "linkedin": linkedin,
                "email_status": email_status
            }

            contacts.append(contact)
            

            # Save to MongoDB with upsert (insert or update)
            collection.update_one(
                {"email": email},
                {"$set": contact},
                upsert=True
            )




    return contacts

def save_contacts_to_csv(contacts, filename='leads_for_guessing.csv'):
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'first_name', 'last_name', 'domain', 'email',
            'title', 'linkedin', 'email_status'
        ])
        writer.writeheader()
        writer.writerows(contacts)
    print(f'\n📁 Saved {len(contacts)} leads to {filename}')


def get_personal_email(first_name, last_name, domain, linkedin_url=None):
    url = 'https://api.apollo.io/api/v1/people/match'
    headers = {'accept': 'application/json', 'Content-Type': 'application/json'}
    payload = {
        'api_key': API_KEY,
        'first_name': first_name,
        'last_name': last_name,
        'domain': domain,
        'reveal_personal_emails': True,
        'reveal_phone_number': False
    }
    if linkedin_url:
        payload['linkedin_url'] = linkedin_url
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    if response.status_code == 200:
        data = response.json()
        person = data.get('person', {})
        personal_emails = person.get('personal_emails', [])
        work_email = person.get('email')
        return personal_emails[0] if personal_emails else work_email
    else:
        print(f'❌ Failed to retrieve email: {response.status_code} - {response.text}')
        return None

def main():
    contacts = collect_contacts(company_domains)
    save_contacts_to_csv(contacts)

if __name__ == '__main__':
    main()
