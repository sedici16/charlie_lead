from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import asyncio
import httpx
from motor.motor_asyncio import AsyncIOMotorClient
from typing import List

# Apollo API Key
API_KEY = 'FaihL1Eu7Ohla4AU39f_yQ'
# MongoDB connection URI
MONGO_URI = "mongodb+srv://gab_lead:jGQMefKw4RFr2mwS@cluster0.t2s7w4o.mongodb.net/?retryWrites=true&w=majority"


# Initialize the FastAPI app
app = FastAPI()

# Mount static directory (optional, for CSS/JS if needed)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Point to the Jinja2 templates directory
templates = Jinja2Templates(directory="templates")

# Setup MongoDB client and select database/collection
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client["apollo_leads"]
collection = db["contacts"]

# List of job titles to filter contacts
job_titles = [
    'ceo', 'chief executive officer', 'owner', 'founder', 'co-founder',
    'head of marketing', 'cmo', 'head of business development', 'head of sales',
    'vp of business development', 'vp of sales and marketing', 'vp of marketing',
    'vice president of business development', 'vice president of sales and marketing',
    'vice president of marketing', 'director of marketing', 'director of business development',
    'marketing director', 'vp of product', 'president and ceo', 'coo',
    'senior vice president sales', 'senior vice president business development',
    'senior vice president marketing', 'svp sales', 'svp business development',
    'svp marketing', 'cto', 'chief technology officer', 'head of brand', 'svp of product',
    'vice president', 'tech lead', 'head of product'
]

# Apollo API endpoints
company_url = 'https://api.apollo.io/api/v1/mixed_companies/search'
people_url = 'https://api.apollo.io/v1/people/search'
match_url = 'https://api.apollo.io/api/v1/people/match'

# Route: GET homepage with form
@app.get("/", response_class=HTMLResponse)
async def read_form(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Route: POST to process domains from form
@app.post("/process", response_class=HTMLResponse)
async def process_form(request: Request, domains: str = Form(...)):
    domain_list = [d.strip() for d in domains.splitlines() if d.strip()]
    results = await fetch_all(domain_list)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "result": f"\u2705 Processed {len(results)} contacts from {len(domain_list)} domains."
    })

# Asynchronously process all domains
async def fetch_all(domains: List[str]):
    contacts = []
    async with httpx.AsyncClient() as client:
        tasks = [process_domain(domain, client) for domain in domains]
        all_contacts_nested = await asyncio.gather(*tasks)
        for domain_contacts in all_contacts_nested:
            for contact in domain_contacts:
                contacts.append(contact)
                await collection.update_one({"email": contact["email"]}, {"$set": contact}, upsert=True)
    return contacts

# Process a single domain (fetch company and employees)
async def process_domain(domain: str, client: httpx.AsyncClient):
    company = await fetch_company(domain, client)
    if not company:
        return []
    company_id = company.get("id")
    people = await fetch_people(company_id, client)
    contacts = []
    for person in people:
        email = await fetch_email(client, person.get("first_name"), person.get("last_name"), domain, person.get("linkedin_url"))
        contact = {
            "first_name": person.get("first_name", ""),
            "last_name": person.get("last_name", ""),
            "domain": domain,
            "email": email or "",
            "title": person.get("title", ""),
            "linkedin": person.get("linkedin_url", ""),
            "email_status": person.get("email_status", "")
        }
        contacts.append(contact)
    return contacts

async def fetch_company(domain, client):
    payload = {
        "api_key": API_KEY,
        "q_organization_name": domain,
        "page": 1,
        "per_page": 1
    }
    res = await client.post(company_url, json=payload)
    if res.status_code != 200:
        print(f"❌ Failed to fetch company for {domain}: {res.status_code}")
        return None
    data = res.json()
    organizations = data.get("organizations", [])
    if not organizations:
        print(f"❌ No company found for domain: {domain}")
        return None
    return organizations[0]



# Fetch employees from Apollo API
async def fetch_people(company_id, client):
    payload = {
        "api_key": API_KEY,
        "organization_ids": [company_id],
        "page": 1,
        "per_page": 5,
        "job_titles": job_titles
    }
    res = await client.post(people_url, json=payload)
    if res.status_code != 200:
        return []
    return res.json().get("people", [])

# Fetch personal or fallback email from Apollo API
async def fetch_email(client, first, last, domain, linkedin=None):
    payload = {
        "api_key": API_KEY,
        "first_name": first,
        "last_name": last,
        "domain": domain,
        "reveal_personal_emails": True,
        "reveal_phone_number": False
    }
    if linkedin:
        payload["linkedin_url"] = linkedin
    res = await client.post(match_url, json=payload)
    if res.status_code != 200:
        return None
    data = res.json().get("person", {})
    emails = data.get("personal_emails", [])
    return emails[0] if emails else data.get("email")
