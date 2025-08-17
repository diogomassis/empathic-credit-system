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
    """
    Health check endpoint for monitoring service status.

    Returns:
        dict: A dictionary containing the status of the service.
    """
    return {"status": "ok"}

@app.post("/v1/predict", response_model=PredictionResponse, tags=["Prediction"])
async def predict_risk(features: FeatureVector):
    """
    Predicts the credit risk score for a user based on provided feature vector.

    This endpoint receives a set of user features, applies a risk prediction algorithm, and returns a risk score
    between 0.0 (low risk) and 1.0 (high risk). The current implementation uses a random score for demonstration purposes.

    Args:
        features (FeatureVector): The input features for risk prediction.

    Returns:
        PredictionResponse: The predicted risk score response.
    """
    # logging.info(f"Received prediction request with features: {features.model_dump_json()}")
    
    # base_score = random.uniform(0.05, 0.75)
    # stress_penalty = features.stress_events_30d * 0.05
    # final_score = min(base_score + stress_penalty, 1.0)

    # logging.info(f"Prediction complete. Calculated risk_score: {final_score}")
    # return PredictionResponse(risk_score=final_score)
    logging.info(f"Received prediction request with features: {features.model_dump_json()}")
    final_score = random.uniform(0.0, 1.0)
    logging.info(f"Prediction complete. Calculated risk_score: {final_score}")
    return PredictionResponse(risk_score=final_score)
