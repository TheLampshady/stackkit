import logging
import os
from typing import Literal

from google.cloud.aiplatform.prediction.predictor import Predictor

logger = logging.getLogger(__name__)


class ImagePredictor(Predictor):
    def __init__(self, **kwargs):
        super().__init__()
        logger.error("Predictor Init: Loading Predictor")
        self.token = os.environ.get("MY_TOKEN")

    def load(self, artifacts_uri: str | None = None):
        """Loads the preprocessor and model artifacts."""
        logger.error("Loading: Loading model")

    def predict(
        self, instances: dict[Literal["instances"], list]
    ) -> dict[Literal["predictions"], list]:
        # The serving container calls this method
        outputs = []
        instances_list = instances.get("instances") or []
        logger.error(f"Instances: {instances_list}")
        logger.error(f"ENV: {os.environ}")
        outputs.append({"env": dict(os.environ)})
        return {"predictions": outputs}
