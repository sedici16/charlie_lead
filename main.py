from fastapi import FastAPI, Request, Form, Query, status
from fastapi import APIRouter
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import asyncio
import httpx
from motor.motor_asyncio import AsyncIOMotorClient
from typing import List
from collections import defaultdict
import csv
import io
from typing import Dict, List
from fastapi.responses import PlainTextResponse
import json
from bson import ObjectId
from fastapi import HTTPException
from bson.errors import InvalidId
import os
from bson.regex import Regex
import re

from dotenv import load_dotenv
load_dotenv()

from starlette.middleware.sessions import SessionMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send


EXEMPT_PATHS = {"/login", "/callback", "/static", "/favicon.ico"}

class AuthMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        path = request.url.path

        if any(path.startswith(p) for p in EXEMPT_PATHS):
            await self.app(scope, receive, send)
            return

        if not request.session.get("authenticated"):
            response = RedirectResponse(url="/login", status_code=303)
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


API_KEY = os.getenv("APOLLO_API_KEY")
CALLBACK_URL = os.getenv("CALLBACK_URL", "/callback")
PASSWORD = os.getenv("ACCESS_PASSWORD")

if not API_KEY:
    raise RuntimeError("Missing APOLLO_API_KEY environment variable.")

SIGNALHIRE_KEY = os.getenv("SIGNALHIRE_API_KEY")

if not SIGNALHIRE_KEY:
    raise RuntimeError("Missing SIGNALHIRE_API_KEY environment variable.")



# MongoDB connection URI
MONGO_URI = "mongodb+srv://gab_lead:jGQMefKw4RFr2mwS@cluster0.t2s7w4o.mongodb.net/?retryWrites=true&w=majority"

# Initialize the FastAPI app
app = FastAPI()


# middleware 
app.add_middleware(AuthMiddleware)

#session secrcted
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET"))






# Mount static directory (optional, for CSS/JS if needed)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Point to the Jinja2 templates directory
templates = Jinja2Templates(directory="templates")

# Setup MongoDB client and select database/collection
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client["apollo_leads"]
collection = db["contacts"]
company_collection = db["companies"]

# List of job titles to filter contacts
job_titles = [
    'ceo', 'chief executive officer', 'founder', 'co-founder',
    'head of marketing', 'cmo', 'head of business development', 'head of sales',
    'vp of business development', 'vp of sales and marketing', 'vp of marketing',
    'vice president of business development', 'vice president of sales and marketing',
    'vice president of marketing', 'director of marketing', 'director of business development',
    'marketing director', 'vp of product', 'president and ceo', 'coo',
    'senior vice president sales', 'senior vice president business development',
    'senior vice president marketing', 'svp sales', 'svp business development',
    'svp marketing', 'cto', 'chief technology officer', 'head of brand', 'svp of product',
    'vice president', 'tech lead', 'head of product',
    # New titles added below
    'chief digital officer', 'chief innovation officer', 'director of product',
    'vp of engineering', 'product lead', 'head of technology',
    'chief commercial officer', 'chief revenue officer', 'head of growth',
    'growth director', 'chief strategy officer', 'cso', 'vp strategy',
    'head of strategy', 'director of strategy', 'senior head of product',
    'executive assistant to president & ceo', 'executive assistant to ceo',
    'global vp of business development', 'ceo & founder', 'cto & co-founder',
    'ceo & co-founder', 'managing director', 'chairman', 'president',
    'executive director', 'general manager', 'chairperson', 'chairwoman',
    'chief operating officer', 'vp of operations', 'director of operations',
    'chief product officer', 'cpo', 'chief information officer'
]

# Apollo API endpoints
company_url = 'https://api.apollo.io/api/v1/mixed_companies/search'
#people_url = 'https://api.apollo.io/v1/people/search'
people_url = 'https://api.apollo.io/api/v1/mixed_people/search'
match_url = 'https://api.apollo.io/api/v1/people/match'



#log in route 
@app.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, password: str = Form(...)):
    if password == PASSWORD:
        request.session["authenticated"] = True
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid password"})





# Route: GET homepage with form, display the home page and its forms
@app.get("/", response_class=HTMLResponse)
async def read_form(request: Request):
    available_domains = await db["domains_for_sale"].find().to_list(length=None)
    return templates.TemplateResponse("index.html", {"request": request, "job_titles": job_titles, "available_domains": available_domains})

# Route: POST to process domains from form
@app.post("/process", response_class=HTMLResponse)
async def process_form(
    request: Request, domains: str = Form(...),
    job_titles: str = Form(...), 
    domain_sale: str = Form(...)):
    

    domain_list = [d.strip() for d in domains.splitlines() if d.strip()]
    custom_titles = [t.strip().lower() for t in job_titles.splitlines() if t.strip()]
    available_domains = await db["domains_for_sale"].find().to_list(length=None)


    
    results, logs = await fetch_all(domain_list, custom_titles, domain_sale)
    return templates.TemplateResponse("index.html", {
        "available_domains": available_domains,  # ← must be here
        "request": request,
        "result": f"\u2705 Processed {len(results)} contacts from {len(domain_list)} domains.",
        "logs": logs,
        "job_titles": custom_titles,
        "domains": domains  # 👈 this keeps the original input in the form
        
    })




@app.get("/autocomplete_companies")
async def autocomplete_companies(q: str = Query(..., min_length=2)):
    escaped_query = re.escape(q)  # 🔒 Escape special regex characters
    regex = Regex(f".*{escaped_query}.*", "i")  # Case-insensitive
    cursor = company_collection.find({"name": regex}, {"name": 1, "company_id": 1}).limit(100)
    results = await cursor.to_list(length=10)
    return [{"value": c["name"], "label": f"{c['name']} (company)"} for c in results if "name" in c]



# Asynchronously process all domains
async def fetch_all(domains: List[str], job_titles: List[str], domain_sale: str):
    contacts = []
    log_entries = []

    timeout = httpx.Timeout(20.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        tasks = [process_domain(domain, client, job_titles, domain_sale) for domain in domains]
        all_contacts_nested = await asyncio.gather(*tasks)

        #loop to add data into mongodb
        for domain_contacts in all_contacts_nested:
            for contact in domain_contacts:

                # ✅ Add keyword and price in the database
                contacts.append(contact)

                unique_filter = {
                    "linkedin": contact["linkedin"] or "",
                    "first_name": contact["first_name"],
                    "last_name": contact["last_name"],
                    "company_name": contact["company_name"]
                }

                # ✏️ Build update dict carefully
                update_fields = {}
                for key, value in contact.items():
                    if value not in (None, ""):
                      update_fields[key] = value

                result = await collection.update_one(
                    unique_filter,
                    {"$set": update_fields},
                    upsert=True
                )

                
                action = "✅ Inserted" if result.upserted_id else "♻️ Updated"
                title_display = contact.get("title", "[no title]")
                first = contact.get("first_name", "")
                last = contact.get("last_name", "")
                full_name = f"{first} {last}".strip() or "[no name]"
                

                log_entries.append(f"{action} contact: {contact['email']} |Name: {full_name}| Title: {title_display} at {contact.get('company_name', 'Unknown')}")
                


                if result.upserted_id:
                    print(f"✅ Inserted new contact: {contact['email']} at {contact.get('company_name', 'Unknown')}")
                else:
                    print(f"♻️ Updated existing contact: {contact['email']} at {contact.get('company_name', 'Unknown')}")

                
    return contacts, log_entries

# Process a single domain (fetch company and employees)
async def process_domain(domain: str, client: httpx.AsyncClient, job_titles: List[str], domain_sale: str):

    #companies = await fetch_company_all(domain, client)
    companies = await fetch_by_domain_or_id_update(domain, client)
    print ("what we get:", companies )

    if not companies:
        return []

    contacts = []

    for company in companies:
        company_id = company.get("id")
        company_name = company.get("name", "")
        company_domain = company.get("website_url", "")

            # 👇 Clean and minimal company object to store
        clean_company = {
            "company_id": company.get("id"),
            "name": company.get("name"),
            "linkedin_url": company.get("linkedin_url"),
            "logo_url": company.get("logo_url"),
            "headcount_growth_6m": company.get("organization_headcount_six_month_growth"),
            "headcount_growth_12m": company.get("organization_headcount_twelve_month_growth"),
            "headcount_growth_24m": company.get("organization_headcount_twenty_four_month_growth"),
            "intent_strength": company.get("intent_strength"),
            "organization_revenue": company.get("organization_revenue"),
            "organization_revenue_printed": company.get("organization_revenue_printed"),
            "domain_for_sale": domain_sale,

        }


        # ✅ Store it (create or update)
        await company_collection.update_one(
             {"company_id": company_id}, 
            {"$set": clean_company},
            upsert=True
        )

        people = await fetch_people(company_id, client, job_titles)
        fetch_emails = len(people) <= 5  # 👈 only fetch emails if 5 or fewer employees
        
        for person in people:

            email = ""
            email_status = ""
            email_source = ""
            all_emails = []  # 👈 Ensure it's always defined

            
            if fetch_emails:
                email, email_status, email_source, all_emails = await fetch_email(
                    client,
                    person.get("first_name"),
                    person.get("last_name"),
                    domain,
                    person.get("linkedin_url")
                ) or  ("", "", "", [])  # 👈 Fix: provide a 4-element fallback tuple


            contact = {
                "first_name": person.get("first_name", ""),
                "last_name": person.get("last_name", ""),
                "company_id": company_id,
                "domain": domain,
                "company_name": company_name,
                "company_domain": company_domain,
                "email": email,  # 👈 USE the fetched email here!,
                "title": person.get("title", ""),
                "linkedin": person.get("linkedin_url", ""),
                "email_status": email_status,# already processed im bulk action
                "email_source": email_source,  # 👈 ADD THIS
                "all_emails": all_emails
            }
            contacts.append(contact)

    return contacts


# Fetch company info from Apollo API
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

async def fetch_company_all(domain, client):
    page = 1
    per_page = 50  # You can fetch more per request to reduce API calls
    all_companies = []

    while len(all_companies) < 50:
        payload = {
            "api_key": API_KEY,
            "q_organization_name": domain,
            "page": page,
            "per_page": per_page
        }
        res = await client.post(company_url, json=payload)
        if res.status_code != 200:
            print(f"❌ Failed to fetch companies for {domain} on page {page}: {res.status_code}")
            break

        data = res.json()
        companies = data.get("organizations", [])

        # 🔍 Log found companies
        for c in companies:
            print(f"✅ Found company: {c.get('name')} | Domain: {c.get('domain')} | ID: {c.get('id')}")


        if not companies:
            break

        all_companies.extend(companies)

        if len(companies) < per_page:
            break  # no more pages

        page += 1

    return all_companies


# Fetch employees from Apollo API
async def fetch_people(company_id, client, job_titles: List[str]):
    payload = {
        "api_key": API_KEY,
        "organization_ids": [company_id],
        "page": 1,
        "per_page": 100,
        #"job_titles": job_titles
        "person_titles": job_titles
    }

    res = await client.post(people_url, json=payload)
    #print("👀 Full people JSON:\n", json.dumps(res.json(), indent=2))

    if res.status_code != 200:
        print(f"❌ Failed to fetch people for company ID {company_id}: {res.status_code}")
        return []

    people = res.json().get("people", [])

    print(f"\n👥 People fetched for company ID {company_id}:")
    if not people:
        print("🚫 No matching people found.")
    else:
        for person in people:
            print(f" - {person.get('first_name', '')} {person.get('last_name', '')} | Title: {person.get('title', '')} | LinkedIn: {person.get('linkedin_url', '')}")

    return people


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
    person = res.json().get("person", {})
    #data = res.json().get("person", {})
    #print(f"\n🧾 Full JSON from Apollo email enrichment for {first} {last}:\n{json.dumps(data, indent=2)}")
    print(f"\n🧾 Full JSON from Apollo email enrichment for {first} {last}:\n{json.dumps(person, indent=2)}")

    #email_status = person.get("email_status", "unknown")
    #emails = person.get("personal_emails", [])
    #email = emails[0] if emails else person.get("email")

    emails = person.get("personal_emails", [])
    all_emails = emails if emails else ([person.get("email")] if person.get("email") else [])
    email_status = person.get("email_status", "unknown")
    email = all_emails[0] if all_emails else ""

    return email, email_status, "Apollo", all_emails


async def fetch_by_domain_or_id(input_str: str, client: httpx.AsyncClient):
    # Apollo IDs are 24-character hex strings (most of the time)
    is_id = len(input_str) == 24 and all(c in '0123456789abcdef' for c in input_str.lower())

    if is_id:
        # Fetch single company by ID
        payload = {
            "api_key": API_KEY,
            "organization_ids": [input_str],
            "page": 1,
            "per_page": 1
        }
        res = await client.post(company_url, json=payload)
        if res.status_code != 200:
            print(f"❌ Failed to fetch company by ID {input_str}: {res.status_code}")
            return []

        data = res.json()
        companies = data.get("organizations", [])
        if not companies:
            print(f"🚫 No company found with ID: {input_str}")
            return []
        
        for c in companies:
            print(f"✅ Found company by ID: {c.get('name')} | Domain: {c.get('domain')} | ID: {c.get('id')}")
        return companies

    else:
        # Use the full fetch_company_all logic for domain or name
        return await fetch_company_all(input_str, client)

async def fetch_by_domain_or_id_update(input_str: str, client: httpx.AsyncClient):
    is_id = len(input_str) == 24 and all(c in '0123456789abcdef' for c in input_str.lower())

    if is_id:
        payload = {
            "api_key": API_KEY,
            "organization_ids": [input_str],
            "page": 1,
            "per_page": 1
        }
        res = await client.post(company_url, json=payload)
        if res.status_code != 200:
            print(f"❌ Error from mixed_companies for ID {input_str}: {res.status_code}")
            return []

        companies = res.json().get("organizations", [])
        if companies:
            for c in companies:
                print(f"✅ Found in mixed_companies by ID: {c.get('name')} | Domain: {c.get('domain')}")
        return companies

    # Step 1: Try to get exact match in accounts
    accounts = await fetch_from_accounts_by_keyword(input_str, client)
    exact_account = next(
        (acc for acc in accounts if (acc.get("domain") or "").strip().lower() == input_str.strip().lower()),
        None
    )
    if exact_account:
        print(f"🎯 Exact domain match found in accounts: {exact_account['domain']}")

    # Step 2: Always fetch organization matches
    organizations = await fetch_company_all(input_str, client)
    if organizations:
        print(f"🧭 Organizations found (length: {len(organizations)})")

    # Combine into one unified list, preferring exact_account first
    
    combined = []

    if exact_account:
        exact_account["source"] = "account"
        combined.append(exact_account)

    for org in organizations:
        org["source"] = "organization"
        combined.append(org)

    if not combined:
        print(f"🚫 No matches found in either organizations or accounts for: {input_str}")

    return combined


#this was the missing one
async def fetch_from_accounts_by_keyword(keyword: str, client: httpx.AsyncClient):
    max_pages = 5
    per_page = 5
    all_matches = []

    print(f"🔁 Searching accounts for: '{keyword}' (up to {max_pages} pages)")

    for page in range(1, max_pages + 1):
        print(f"📄 Page {page} (accounts)")

        payload = {
            "api_key": API_KEY,
            "q_organization_name": keyword,
            "page": page,
            "per_page": per_page
        }

        res = await client.post(company_url, json=payload)
        if res.status_code != 200:
            print(f"❌ API error on page {page}: {res.status_code}")
            break

        data = res.json()
        accounts = data.get("accounts", [])
        if not accounts:
            print("🚫 No more accounts found.")
            break

        for acc in accounts:
            domain = acc.get("domain")
            print(f"✅ Found (accounts): {acc.get('name')} | Domain: {domain} | ID: {acc.get('id')}")
            all_matches.append(acc)

            # Stop if we find an exact domain match
            if domain and domain.lower() == keyword.lower():
                print(f"🎯 Exact domain match found in accounts: {domain}")
                return [acc]

        # polite pause if needed
        await asyncio.sleep(0.5)

    return all_matches





# Route: GET homepage with search form
#@app.get("/search", response_class=HTMLResponse)
#async def search_form(request: Request):
#    return templates.TemplateResponse("search.html", {"request": request})

# Route: POST to search contacts by domain
@app.post("/search", response_class=HTMLResponse)
@app.get("/search", response_class=HTMLResponse)
#async def search_results(request: Request, domain_query: str = Form(...), ):
async def search(request: Request, domain_query: str = Form(None, alias="domain_query")):

    if request.method == "GET":
        domain_query = request.query_params.get("domain_query")

    if not domain_query:
        return templates.TemplateResponse("search.html", {"request": request})


    query = {
                "$or": [
                    {"domain": {"$regex": domain_query, "$options": "i"}},
                    {"company_domain": {"$regex": domain_query, "$options": "i"}},
                    {"company_name": {"$regex": domain_query, "$options": "i"}}
                ]
            }

        
    results = await collection.find(query).to_list(length=None)

    grouped: Dict[str, List[dict]] = defaultdict(list)
    
    for contact in results:
        key = contact.get("company_domain") or contact["domain"]

        # ⬇️ Sort emails so that those containing company domain come first
        domain = (contact.get("company_domain") or contact.get("domain") or "")\
        .replace("http://", "")\
        .replace("https://", "")\
        .replace("www.", "")\
        .lower()

        emails = contact.get("all_emails", [])
        
        sorted_emails = sorted(emails, key=lambda e: domain not in e.lower())
        
        contact["all_emails"] = sorted_emails


        grouped[key].append(contact)

    return templates.TemplateResponse("search.html", {
        "request": request,
        "grouped_results": dict(grouped),
        "csv_download": domain_query,
        "domain_query": domain_query
    })

#new route to use the company collection to fetch the employees
@app.post("/search_by_company_id", response_class=HTMLResponse)
@app.get("/search_by_company_id", response_class=HTMLResponse)
async def search_by_company_id(request: Request, domain_query: str = Form(None)):
    if request.method == "GET":
        domain_query = request.query_params.get("domain_query")

    if not domain_query:
        return templates.TemplateResponse("search_company.html", {
            "request": request,
            "results": [],
            "domain_query": ""
        })

    # Normalize domain
    domain_normalized = domain_query.lower().replace("http://", "").replace("https://", "").replace("www.", "")

    # Step 1: Find the company by name, domain, or URL
    company = await company_collection.find_one({
        "$or": [
            {"name": {"$regex": domain_query, "$options": "i"}},
            {"domain": {"$regex": domain_normalized, "$options": "i"}},
            {"website_url": {"$regex": domain_normalized, "$options": "i"}}
        ]
    })

    if not company:
        return templates.TemplateResponse("search_company.html", {
            "request": request,
            "results": [],
            "domain_query": domain_query
        })
    
    # 🔁 JOIN: Fetch domain pricing if company has a domain_for_sale
    domain_key = company.get("domain_for_sale")
    if domain_key:
        domain_doc = await db["domains_for_sale"].find_one({"domain": domain_key})
        if domain_doc:
            company["price"] = domain_doc.get("price")

    # Step 2: Fetch all employees linked to this company
    company_id = company.get("company_id") or company.get("id")
    employees = await collection.find({"company_id": company_id}).to_list(length=None)

    # Step 3: Sort emails within each employee
    for emp in employees:
        
        domain_clean = domain_normalized
        emp["all_emails"] = sorted(emp.get("all_emails", []), key=lambda e: domain_clean not in e.lower())

    # Step 4: Return both company and employee data to the frontend
    return templates.TemplateResponse("search_company.html", {
        "request": request,
        "results": [{"company": company, "employees": employees}],
        "domain_query": domain_query
    })


@app.get("/autocomplete_domains_for_sale")
async def autocomplete_domains_for_sale(q: str = Query(..., min_length=2)):
    escaped_query = re.escape(q)  # Escape special regex characters
    regex = Regex(f".*{escaped_query}.*", "i")  # Case-insensitive match
    cursor = db["domains_for_sale"].find({"domain": regex}, {"domain": 1, "price": 1}).limit(20)
    results = await cursor.to_list(length=20)
    return [{"value": d["domain"], "label": f"{d['domain']} - €{d.get('price', 'N/A')}"} for d in results if "domain" in d]



@app.post("/autocomplete_companies ", response_class=HTMLResponse)
@app.get("/search_by_domain_sale", response_class=HTMLResponse)
async def search_by_domain_sale(request: Request, domain_query: str = Form(None)):
    if request.method == "GET":
        domain_query = request.query_params.get("domain_query")

    if not domain_query:
        return templates.TemplateResponse("search_company.html", {
            "request": request,
            "results": [],
            "domain_query": ""
        })

    domain_normalized = domain_query.lower().replace("http://", "").replace("https://", "").replace("www.", "")

    # 🔁 Match all companies with this domain_for_sale
    companies = await company_collection.find({
        "$or": [
            {"domain_for_sale": {"$regex": domain_normalized, "$options": "i"}},
            {"domain": {"$regex": domain_normalized, "$options": "i"}},
            {"website_url": {"$regex": domain_normalized, "$options": "i"}},
            {"name": {"$regex": domain_normalized, "$options": "i"}} 
        ]
    }).to_list(length=None)

    if not companies:
        return templates.TemplateResponse("search_company.html", {
            "request": request,
            "results": [],
            "domain_query": domain_query
        })

    results = []

    for company in companies:
        domain_key = company.get("domain_for_sale")
        if domain_key:
            domain_doc = await db["domains_for_sale"].find_one({"domain": domain_key})
            if domain_doc:
                company["price"] = domain_doc.get("price")

        company_id = company.get("company_id") or company.get("id")
        employees = await collection.find({"company_id": company_id}).to_list(length=None)

        for emp in employees:
            emp["all_emails"] = sorted(
                emp.get("all_emails", []),
                key=lambda e: domain_normalized not in e.lower()
            )

        results.append({
            "company": company,
            "employees": employees
        })

    return templates.TemplateResponse("search_company.html", {
        "request": request,
        "results": results,
        "domain_query": domain_query
    })







@app.post("/signalhire_request")
async def signalhire_request(
    linkedin: str = Form(None),
    first_name: str = Form(...),
    last_name: str = Form(...),
    company_domain: str = Form(...)
):
    # 🔥 Prepare the request to SignalHire
    headers = {
        "apikey": SIGNALHIRE_KEY,  # 🚨 replace with your actual key
        "Content-Type": "application/json"
    }
    payload = {
        "items": [linkedin if linkedin else f"{first_name} {last_name} {company_domain}"],
        "callbackUrl": CALLBACK_URL
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://www.signalhire.com/api/v1/candidate/search",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            print (payload)
            print("✅ SignalHire request sent!")
        except Exception as e:
            print(f"❌ Error sending to SignalHire: {e}")

    # After sending the request, go back to the homepage
    return RedirectResponse(url="/search", status_code=303)


#it responsible to fetch and store in mongodb emails from apollo and signalhire by selection of the boxes on the interface
@app.post("/bulk_action")
async def bulk_action(request: Request):
    form_data = await request.form()
    selected_contacts = form_data.getlist('selected_contacts')
    action = form_data.get('action')
    domain_query = form_data.get('domain_query')  # ⬅️ Capture it from the form!
    source = form_data.get('source') or "search"  # 🆕 Default to original route

    if not selected_contacts:
        return PlainTextResponse("❌ No contacts selected.", status_code=400)

    print(f"✅ Selected contacts: {selected_contacts}")
    print(f"✅ Selected action: {action}")

    async with httpx.AsyncClient() as client:
        if action == "apollo":
            for linkedin_url in selected_contacts:
                # Find the contact details in MongoDB
                contact = await collection.find_one({"linkedin": linkedin_url})
                if not contact:
                    print(f"⚠️ Contact not found for {linkedin_url}")
                    continue

                first_name = contact.get("first_name", "")
                last_name = contact.get("last_name", "")
                domain = contact.get("domain", "")

                # Use Apollo to fetch email
                email, email_status, email_source, all_emails = await fetch_email(client, first_name, last_name, domain, linkedin_url)
                if email:
                    await collection.update_one(
                        {"linkedin": linkedin_url},
                        {"$set": {
                            "email": email,
                            "email_status": email_status,
                            "email_source": email_source,
                            "all_emails": all_emails  # ✅ Add this line
                        }}
                    )
                    print(f"✅ Apollo email updated for {linkedin_url}: {email}")
                else:
                    print(f"❌ Apollo could not find email for {linkedin_url}")

        elif action == "signalhire":
            # 🔥 Send ONE single request for all LinkedIns
            payload = {
                "items": selected_contacts,
                "callbackUrl": CALLBACK_URL
            }
            headers = {
                "apikey": SIGNALHIRE_KEY,
                "Content-Type": "application/json"
            }
            try:
                res = await client.post(
                    "https://www.signalhire.com/api/v1/candidate/search",
                    headers=headers,
                    json=payload
                )
                res.raise_for_status()
                print(f"✅ Bulk SignalHire request sent for {len(selected_contacts)} contacts.")
            except Exception as e:
                print(f"❌ Error sending bulk to SignalHire: {e}")

    #return RedirectResponse(url="/search", status_code=303)

    # ⬇️ Redirect back to /search with domain_query preserved
    #if domain_query:
    #    return RedirectResponse(url=f"/search?domain_query={domain_query}", status_code=303)
    #else:
    #    return RedirectResponse(url="/search", status_code=303)

    # 🔁 Redirect to correct search view use the old route or the new one earch_by_company_id
    if source == "company_id":
        return RedirectResponse(url=f"/search_by_domain_sale?domain_query={domain_query}", status_code=303)
    else:
        return RedirectResponse(url=f"/search?domain_query={domain_query}", status_code=303)
    



@app.post("/export_selected_csv")
async def export_selected_csv(request: Request):
    form = await request.form()
    company_id = form.get("company_id")


    # ✅ Parse all selected _id values from checkbox names
    selected_ids = [
        form.get(field)
        for field in form.keys()
        if field.startswith("export_selected_") and form.get(field)
    ]

    print("✔ Selected ID strings:", selected_ids)

    # ✅ Convert strings to ObjectId
    selected_object_ids = []
    for sid in selected_ids:
        try:
            selected_object_ids.append(ObjectId(sid))
        except InvalidId:
            print(f"⚠️ Skipping invalid ObjectId: {sid}")

    if not selected_object_ids:
        return StreamingResponse(iter(["No valid contacts selected."]), media_type="text/plain")

    # ✅ Query MongoDB directly by _id
    filtered_employees = await collection.find({
        "_id": {"$in": selected_object_ids}
    }).to_list(length=None)

    for emp in filtered_employees:
        print("🔍 EMPLOYEE DOCUMENT:", emp)

    print(f"✅ Exporting {len(filtered_employees)} contacts")

    # ✅ Build CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name", "Title", "Email", "LinkedIn", "Source", "Status"])

    for emp in filtered_employees:
        writer.writerow([
            f"{emp.get('first_name', '')} {emp.get('last_name', '')}",
            emp.get("title", ""),
            emp.get("email", ""),
            emp.get("linkedin", ""),
            emp.get("email_source", ""),
            emp.get("email_status", "")
        ])
    
        await collection.update_one(
            {"_id": emp["_id"]},
            {"$set": {"export_selected": True}}  # ✅ Add this
    )
    

    output.seek(0)
    return StreamingResponse(
        iter([u'\ufeff' + output.getvalue()]),  # 🔥 UTF-8 BOM prefix
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=selected_contacts_{company_id}.csv"}
    )


    

#wait for the answer from signalhire and store the response.
@app.post("/callback")
async def signalhire_callback(request: Request):
    data = await request.json()
    print(f"✅ Received callback from SignalHire:\n{data}")

    for result in data:
        status = result.get("status")
        item = result.get("item")
        candidate = result.get("candidate", {})

        if status == "success" and candidate:
            emails = candidate.get("contacts", [])
            
            all_emails = [c.get("value") for c in emails if c.get("type") == "email"]
            
            first_valid_email = None

            if all_emails:
                first_valid_email = all_emails[0]


            # Update MongoDB if email found
            if first_valid_email:

                #linkedin_url = candidate.get("social", [{}])[0].get("link")  # Best guess
                linkedin_url = (candidate.get("social") or [{}])[0].get("link", "")
                first_name = candidate.get("fullName", "").split()[0] if candidate.get("fullName") else None
                last_name = " ".join(candidate.get("fullName", "").split()[1:]) if candidate.get("fullName") else None

                if not first_name or not last_name:
                    print("⚠️ Could not parse full name.")
                    continue
                


                if linkedin_url:
                    normalized_linkedin = linkedin_url.replace("https://", "http://")
                    result = await collection.update_one(
                            {"$or": [
                                {"linkedin": linkedin_url},
                                {"linkedin": normalized_linkedin},
                                 {"first_name": first_name, "last_name": last_name}
                                
                            ]},
                            {"$set": {"email": first_valid_email,
                            "email_source": "SignalHire",
                            "all_emails": all_emails,
                            }},
                            upsert=False
                            )
                    if result.modified_count:
                        print(f"✅ Updated contact {linkedin_url} with new email: {first_valid_email}")
                    else:
                        print(f"⚠️ Could not find contact to update for {linkedin_url}")
    return PlainTextResponse("OK")

#old route from the search page
@app.get("/download_csv", response_class=StreamingResponse)
async def download_csv(domain: str):
    normalized = domain.lower().replace("http://", "").replace("https://", "").replace("www.", "")
    query = {
        "$or": [
            {"domain": {"$regex": normalized, "$options": "i"}},
            {"company_domain": {"$regex": normalized, "$options": "i"}}
        ]
    }

    results = await collection.find(query).to_list(length=None)

    if not results:
        print(f"❌ No results found for domain: {domain}")

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=[
        "first_name", "last_name", "title", "email", "linkedin", "domain"
    ])
    writer.writeheader()
    for row in results:
        writer.writerow({
            "first_name": row.get("first_name", ""),
            "last_name": row.get("last_name", ""),
            "title": row.get("title", ""),
            "email": row.get("email", ""),
            "linkedin": row.get("linkedin", ""),
            "domain": row.get("domain", row.get("company_domain", ""))
        })

    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=contacts_{normalized}.csv"}
    )

#new route for the id matching csv save
@app.get("/download_csv_by_company_id", response_class=StreamingResponse)
async def download_csv_by_company_id(company_id: str):
    # Step 1: Get the company (optional, for metadata or name in filename)
    company = await company_collection.find_one({
        "$or": [
            {"company_id": company_id},
            {"id": company_id}
        ]
    })

    if not company:
        return StreamingResponse(iter(["No company found."]), media_type="text/plain")
    
    # 🔁 JOIN: attach price from domains_for_sale
    domain_key = company.get("domain_for_sale")
    if domain_key:
        domain_doc = await db["domains_for_sale"].find_one({"domain": domain_key})
        if domain_doc:
            company["price"] = domain_doc.get("price")


    company_name = company.get("name", "unknown_company").replace(" ", "_").lower()
    
    domain_for_sale = company.get("domain_for_sale", "")

    # Step 2: Get employees by company_id
    employees = await collection.find({"company_id": company_id}).to_list(length=None)

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=[
        "first_name", "last_name", "title", "email", "linkedin", "domain", "price", "domain_for_sale"
    ])
    writer.writeheader()

    for row in employees:
        writer.writerow({
            "first_name": row.get("first_name", ""),
            "last_name": row.get("last_name", ""),
            "title": row.get("title", ""),
            "email": row.get("email", ""),
            "linkedin": row.get("linkedin", ""),
            "domain": row.get("domain", row.get("company_domain", "")),
            "price": company.get("price", ""),  # include price here
            "domain_for_sale": domain_for_sale
            
            

        })

    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=contacts_{company_name}.csv"}
    )


#update the company metadata with price
@app.post("/update_company_metadata")
async def update_company_metadata(
    company_id: str = Form(...),
    price: str = Form(""),
    domain_query: str = Form(...),
    domain_for_sale: str = Form(""),
    redirect_to: str = Form("search_by_company_id")  # default fallback
    
):
    update_fields = {}

    if price.strip():
        update_fields["price"] = price.strip()

    if domain_for_sale.strip():
        update_fields["domain_for_sale"] = domain_for_sale.strip()

    if update_fields:
        await company_collection.update_one(
            {"company_id": company_id},
            {"$set": update_fields}
        )
        print(f"✅ Updated company {company_id} with: {update_fields}")
    else:
        print("⚠️ No fields to update")

        # Conditional redirect
    if redirect_to == "manage_companies":
        return RedirectResponse(url=f"/manage_companies?query={domain_query}", status_code=303)
    else:
        return RedirectResponse(url=f"/search_by_company_id?domain_query={domain_query}", status_code=303)

# Route: GET company search form and results
@app.get("/manage_companies", response_class=HTMLResponse)
async def company_search(request: Request, query: str = ""):
    if not query:
        return templates.TemplateResponse("manage_companies.html", {"request": request, "results": [], "query": ""})

    normalized = query.lower().replace("http://", "").replace("https://", "").replace("www.", "")

    company_query = {
        "$or": [
            {"name": {"$regex": query, "$options": "i"}},
            {"domain": {"$regex": normalized, "$options": "i"}},
            {"website_url": {"$regex": normalized, "$options": "i"}}
        ]
    }

    results = await company_collection.find(company_query).to_list(length=None)

    # JOIN: attach price from domains_for_sale
    for company in results:
        domain_key = company.get("domain_for_sale")
        if domain_key:
            domain_doc = await db["domains_for_sale"].find_one({"domain": domain_key})
            if domain_doc:
                company["price"] = domain_doc.get("price")

    return templates.TemplateResponse("manage_companies.html", {
        "request": request,
        "results": results,
        "query": query
    })

#display the domain table
@app.get("/manage_domains", response_class=HTMLResponse)
async def manage_domains(request: Request):
    domains = await db["domains_for_sale"].find().to_list(length=None)
    return templates.TemplateResponse("manage_domains.html", {
        "request": request,
        "domains": domains
    })

#add domains in the domain table
@app.post("/add_domain", response_class=RedirectResponse)
async def add_domain(
    domain: str = Form(...),
    price: str = Form(...),
):
    await db["domains_for_sale"].update_one(
        {"domain": domain},
        {"$set": {"price": price}},
        upsert=True
    )
    return RedirectResponse(url="/manage_domains", status_code=303)


#delete domains in the domain table
@app.post("/delete_domain", response_class=RedirectResponse)
async def delete_domain(domain: str = Form(...)):
    await db["domains_for_sale"].delete_one({"domain": domain})
    return RedirectResponse(url="/manage_domains", status_code=303)


@app.get("/download_csv_by_keyword", response_class=StreamingResponse)
async def download_csv_by_keyword(keyword: str):
    query = {"keyword": keyword}
    results = await collection.find(query).to_list(length=None)

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=[
        "Domain Name", "Price", "Company", "First Name", "Last Name", "Email", "Company Title"
    ])
    writer.writeheader()

    for row in results:
        writer.writerow({
            "Domain Name": row.get("keyword", ""),
            "Price": row.get("price", ""),
            "Company": row.get("company_name", ""),
            "First Name": row.get("first_name", ""),
            "Last Name": row.get("last_name", ""),
            "Email": row.get("email", ""),
            "Company Title": row.get("title", "")
        })

    buffer.seek(0)
    return StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv", headers={
        "Content-Disposition": f"attachment; filename=leads_{keyword}.csv"
    })

@app.get("/export_csv_by_keyword", response_class=HTMLResponse)
async def keyword_export_page(request: Request):
    return templates.TemplateResponse("keyword_export.html", {"request": request})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)