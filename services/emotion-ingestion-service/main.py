import os
import json
import nats

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, status


NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the connection to NATS during the application's lifecycle.
    """
    print(f"Trying to connect to NATS at {NATS_URL}...")
    try:
        nc = await nats.connect(NATS_URL, name="emotion_ingestion_service")
        app.state.nats_connection = nc
        print("Successfully connected to NATS!")
        yield
    finally:
        if 'nats_connection' in app.state and app.state.nats_connection.is_connected:
            print("Closing connection to NATS...")
            await app.state.nats_connection.close()
            print("NATS connection closed.")


app = FastAPI(lifespan=lifespan)

@app.get("/health", status_code=status.HTTP_200_OK)
def health():
    """
    Health check endpoint for the Emotion Ingestion Service.
    """
    return {"message": "Emotion Ingestion Service is healthy."}


@app.post("/publish_emotion", status_code=status.HTTP_202_ACCEPTED)
async def publish_message(emotion_data: dict, request: Request):
    """
    Receives a JSON and publishes it to a NATS topic using the existing connection.
    """
    try:
        nc = request.app.state.nats_connection
        payload = json.dumps(emotion_data).encode()
        await nc.publish("emotions.ingested", payload)
        await nc.flush()
        return {"status": "message published", "data": emotion_data}
    except AttributeError:
        raise HTTPException(status_code=503, detail="NATS connection not available.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to publish to NATS: {str(e)}")
