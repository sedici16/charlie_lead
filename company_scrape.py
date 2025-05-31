from duckduckgo_search import DDGS
from scrapegraphai.graphs import SmartScraperGraph

OPENAI_API_KEY = "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"  # replace with your key

def search_duckduckgo(query, max_results=10):
    with DDGS() as ddgs:
        results = ddgs.text(query, max_results=max_results)
        return [r['href'] for r in results]


def scrape_with_gpt(url):
    config = {
        "llm": {
            "api_key": OPENAI_API_KEY,
            "model": "gpt-4"
        },
        "graph_config": {
            "verbose": True
        }
    }
    graph = SmartScraperGraph(
        prompt="Extract the startup name, website, location, and a short description.",
        source=url,
        config=config
    )
    return graph.run()

if __name__ == "__main__":
    query = input("🔍 Enter search query (e.g. fintech startups in London): ")
    urls = search_duckduckgo(query)

    print(f"\n📄 Found {len(urls)} URLs. Scraping...\n")
    for url in urls:
        print(f"🌐 URL: {url}")
        try:
            data = scrape_with_gpt(url)
            print("📊 Extracted Data:", data)
        except Exception as e:
            print("⚠️ Error scraping:", e)
        print("-" * 60)
