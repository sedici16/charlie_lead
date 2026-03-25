# Charlie Lead

A lead generation tool that finds and enriches business contacts. Search for companies, scrape key details, and retrieve contact information through a web interface.

## What It Does

1. Search for companies by keyword or industry
2. Scrape company details (size, location, domain)
3. Find relevant people at those companies via Apollo and SignalHire APIs
4. Store leads in MongoDB for tracking and export
5. Export results as CSV

## Tech Stack

- **Backend**: FastAPI (async)
- **Database**: MongoDB Atlas (via Motor async driver)
- **APIs**: Apollo.io (company/people search), SignalHire (contact enrichment)
- **Frontend**: Jinja2 templates with static assets
- **Auth**: Simple password protection

## Setup

```bash
git clone https://github.com/sedici16/charlie_lead.git
cd charlie_lead
pip install -r requirements.txt
uvicorn main:app --reload
```

## Environment Variables

```
APOLLO_API_KEY=your-apollo-key
SIGNALHIRE_API_KEY=your-signalhire-key
ACCESS_PASSWORD=your-password
CALLBACK_URL=/callback
```

## Project Structure

```
charlie_lead/
├── main.py              # FastAPI app, routes, API integrations
├── company_scrape.py    # Company data scraping
├── search_people.py     # People search logic
├── callback_server.py   # Webhook handler for async enrichment
├── requirements.txt
├── static/              # Frontend assets
└── templates/           # HTML templates
```
