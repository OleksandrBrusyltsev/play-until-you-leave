import uvicorn
from fastapi import FastAPI

# healthcheck only
app = FastAPI()


@app.get("/")
@app.get("/health")
def health():
    return {"status": "ok"}


def run_api():
    uvicorn.run(app, host="0.0.0.0", port=8080,log_level="warning")
