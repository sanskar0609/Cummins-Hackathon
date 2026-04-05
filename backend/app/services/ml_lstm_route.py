import os
import numpy as np
try:
    import mlflow
    import mlflow.sklearn
except ImportError:
    mlflow = None
import joblib
from sklearn.ensemble import RandomForestRegressor
from datetime import datetime
from app.core.config import settings
from app.core.logging import log

MODEL_PATH = os.path.join("ml", "lstm", "route_risk_model.pkl")

# TODO: Replaced PyTorch LSTM with scikit-learn RandomForest equivalent natively
# since torch architectures were too large for Docker deployment.

def generate_mock_route_features(batch_size=32):
    X = np.random.rand(batch_size, 4).astype(np.float32)
    y = np.sum(X[:, 0:2], axis=1) * 50.0 + np.random.normal(0, 5, batch_size) 
    y = np.clip(y, 0, 100).astype(np.float32)
    return X, y

def train_and_log_model():
    log.info("starting_rf_training", tracking_uri=settings.MLFLOW_TRACKING_URI)
    mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
    mlflow.set_experiment("Route_Risk_Prediction")
    
    model = RandomForestRegressor(n_estimators=10)
    X_train, y_train = generate_mock_route_features(100)
    
    with mlflow.start_run(run_name=f"rf_run_{datetime.utcnow().strftime('%Y%m%d_%H%M')}"):
        model.fit(X_train, y_train)
        score = model.score(X_train, y_train)
        mlflow.log_metric("train_r2_score", score)
        mlflow.sklearn.log_model(model, "model", registered_model_name="RouteRiskRF")
        log.info("rf_training_complete", r2_score=score)

def train_and_save_mock_model():
    """ Trains the RF model on mock data and serializes to .pkl for deployment. """
    log.info("start_training_route_risk_model")
    model = RandomForestRegressor(n_estimators=10)
    X_train, y_train = generate_mock_route_features(200)
    model.fit(X_train, y_train)
    
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    log.info("route_risk_model_saved", path=MODEL_PATH)
    return model

def predict_route_risk(route_id: str) -> float:
    """ Prediction logic using pre-trained .pkl if available. """
    if os.path.exists(MODEL_PATH):
        try:
            model = joblib.load(MODEL_PATH)
        except Exception:
            # Re-train safely if load fails
            model = train_and_save_mock_model()
    else:
        # Create it on the fly for the first time
        model = train_and_save_mock_model()
    
    X_test, _ = generate_mock_route_features(1)
    prediction = model.predict(X_test)[0]
    return round(float(np.clip(prediction, 0.0, 100.0)), 2)

if __name__ == "__main__":
    train_and_log_model()
