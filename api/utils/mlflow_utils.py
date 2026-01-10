import mlflow
import os
import logging
import time
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Configure MLflow Tracking URI
# Default to Minikube service URL or local fallback
MLFLOW_TRACKING_URI = os.getenv('MLFLOW_TRACKING_URI', 'http://mlflow-service.dev:5000')

def setup_mlflow():
    """Initialize MLflow configuration."""
    try:
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        logger.info(f"MLflow tracking URI set to: {MLFLOW_TRACKING_URI}")
    except Exception as e:
        logger.warning(f"Failed to set MLflow tracking URI: {e}")

def log_query_experiment(
    prompt_version: str,
    model_tier: str,
    domain: str,
    cost: float,
    tokens: Dict[str, int],
    latency_ms: float,
    cached: bool,
    feedback_score: float = None
):

    if os.getenv("ENABLE_MLFLOW", "true").lower() != "true":
        return

    try:
        # Set the experiment name based on domain
        experiment_name = f"rag_pipeline_{domain}"
        mlflow.set_experiment(experiment_name)
        
        with mlflow.start_run(run_name=f"query_execution_{int(time.time())}"):
            # Log inputs
            mlflow.log_param("prompt_version", prompt_version)
            mlflow.log_param("model_tier", model_tier)
            mlflow.log_param("domain", domain)
            mlflow.log_param("cached", cached)
            
            # Log metrics
            mlflow.log_metric("cost", cost)
            mlflow.log_metric("input_tokens", tokens.get("input", 0))
            mlflow.log_metric("output_tokens", tokens.get("output", 0))
            mlflow.log_metric("latency_ms", latency_ms)
            
            if feedback_score is not None:
                mlflow.log_metric("feedback_score", feedback_score)
                
            # Log tags
            mlflow.set_tag("environment", os.getenv("APP_ENV", "dev"))
            mlflow.set_tag("pipeline_stage", "production" if not feedback_score else "evaluation")
            
    except Exception as e:
        # Don't fail the request if logging fails
        logger.error(f"Failed to log to MLflow: {e}")

from mlflow.pyfunc import PythonModel, PythonModelContext

class PromptModel(PythonModel):
    """Simple wrapper for prompt templates to allow registering as MLflow models"""
    def load_context(self, context: PythonModelContext):
        pass
        
    def predict(self, context: PythonModelContext, model_input):
        return "This is a prompt template model"

def register_prompt_version(
    version_id: str,
    domain: str,
    system_prompt: str,
    user_template: str
):
    """Register prompt version in MLflow model registry"""
    
    with mlflow.start_run(run_name=f"register_prompt_{version_id}"):
        # Log prompt as artifact
        mlflow.log_text(system_prompt, "system_prompt.txt")
        mlflow.log_text(user_template, "user_template.txt")
        
        # Log as model
        # We wrap the prompt in a simple PythonModel to satisfy MLflow's requirement
        model = PromptModel()
        
        mlflow.pyfunc.log_model(
            artifact_path="prompt",
            python_model=model,
            registered_model_name=f"prompt_{domain}_{version_id}"
        )
