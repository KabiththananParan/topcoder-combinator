from fastapi import FastAPI

app = FastAPI(
    title="Topcoder Combinator",
    version="0.1.0",
)


@app.get("/health")
def health_check():
    return {"status": "ok"}