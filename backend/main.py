from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from rag_engine import TokamakArchitect
import uvicorn

app = FastAPI(title="Tokamak Architect API")

# Allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize AI
bot = TokamakArchitect()

class ChatRequest(BaseModel):
    message: str
    history: list = [] 

@app.get("/")
def health_check():
    return {"status": "Tokamak Architect is Online 🤖"}

@app.post("/chat")
def chat_endpoint(request: ChatRequest):
    try:
        response = bot.ask(request.message, request.history)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
