import asyncio
import httpx

# 🔥 Your SignalHire API Key
API_KEY = "202.FOqUpFiN1xtdse3R41kkXkgWW3Bm"

# 🔥 Your ngrok callback URL
CALLBACK_URL = "https://7ed6-212-90-24-126.ngrok-free.app/callback"

# 🔥 SignalHire endpoint
SIGNALHIRE_API_URL = "https://www.signalhire.com/api/v1/candidate/search"

async def send_signalhire_request(item):
    headers = {
        "apikey": API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "items": [item],  # 👈 Must be a list
        "callbackUrl": CALLBACK_URL  # 👈 No underscore, exact case "callbackUrl"
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(SIGNALHIRE_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            print(f"\n✅ Request sent successfully to SignalHire.")
            print(f"Response Status: {response.status_code}")
            print(f"Response Content: {response.text}")
        except httpx.HTTPStatusError as exc:
            print(f"\n❌ HTTP error: {exc.response.status_code} - {exc.response.text}")
        except Exception as exc:
            print(f"\n❌ General error: {exc}")

# Example usage
if __name__ == "__main__":
    asyncio.run(send_signalhire_request(
        "https://www.linkedin.com/in/gabrielemonti/"  # 👈 OR email / phone / UID
    ))
