import logging
import random

from fastapi import FastAPI, status
from models.machine_learning import FeatureVector, PredictionResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

app = FastAPI(
    title="Credit Analysis Service",
    version="1.0.0"
)

@app.get("/healthz", status_code=status.HTTP_200_OK, tags=["Monitoring"])
async def health_check():
    return {"status": "ok"}

@app.post("/v1/predict", response_model=PredictionResponse, tags=["Prediction"])
async def predict_risk(features: FeatureVector):
    logging.info(f"Received prediction request with features: {features.model_dump_json()}")
    
    base_score = random.uniform(0.05, 0.75)
    stress_penalty = features.stress_events_30d * 0.05
    final_score = min(base_score + stress_penalty, 1.0)

    logging.info(f"Prediction complete. Calculated risk_score: {final_score}")
    return PredictionResponse(risk_score=final_score)
