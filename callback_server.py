from fastapi import FastAPI, Request

app = FastAPI()

@app.post("/callback")
async def receive_callback(request: Request):
    data = await request.json()
    print("\n✅ Received callback from SignalHire:")
    print(data)
    
    with open("signalhire_callback_log.txt", "a", encoding="utf-8") as f:
        f.write(str(data) + "\n\n")
    
    return {"message": "Callback received!"}
