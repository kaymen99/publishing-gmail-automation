import uvicorn, os
from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from src.graph import Workflow
from dotenv import load_dotenv

# Load .env file
load_dotenv()

app = FastAPI(
    title="Gmail Automation",
    version="1.0",
    description="LangGraph backend for the AI Gmail automation workflow",
)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != os.getenv("INTERNAL_API_KEY"):
        raise HTTPException(status_code=403, detail="Invalid API key")

@app.get("/")
async def redirect_root_to_docs():
    return RedirectResponse("/docs")

@app.post("/execute", dependencies=[Depends(verify_api_key)])
async def generate_route():
    workflow = Workflow()
    automation = workflow.app

    # config 
    config = {'recursion_limit': 1000}

    # state
    initial_state = {
        "emails": [],
        "current_email": {
            "id": "",
            "threadId": "",
            "sender": "",
            "sender_email": "",
            "subject": "",
            "body": ""
        },
        "email_category": "",
        "email_inquiries": [],
        "retrieved_context": "",
        "generated_email": "",
        "editor_feedback": "",
        "trials": 0
    }

    try:
        outputs = automation.invoke(initial_state, config)
        return {"result": outputs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def main():
    # Start the API
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()