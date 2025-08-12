from fastapi import FastAPI, status

app = FastAPI()

@app.get("/health", status_code=status.HTTP_200_OK)
def health():
    """
    This endpoint returns a welcome message and a 200 OK status.
    """
    return {"message": "Emotion Ingestion Service is healthy."}
