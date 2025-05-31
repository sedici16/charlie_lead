from fastapi import FastAPI, Request
import uvicorn

app = FastAPI()

@app.post("/callback")
async def receive_callback(request: Request):
    data = await request.json()
    print("\n✅ Received callback from SignalHire:")
    print(data)
    
    # Optional: save to file (for history/debugging)
    with open("signalhire_callback_log.txt", "a", encoding="utf-8") as f:
        f.write(str(data) + "\n\n")
    
    return {"message": "Callback received successfully!"}

if __name__ == "__main__":
    uvicorn.run("callback_server:app", host="0.0.0.0", port=7862, reload=True)
