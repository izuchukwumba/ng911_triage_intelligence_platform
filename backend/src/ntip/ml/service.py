"""Standalone inference service (design v1.2, section 3A.3).

Runs separately from the platform API and holds no state: it receives an
InferenceRequest and returns an InferenceResponse. Transcript text is treated
strictly as data to extract from, never as instructions.

    NTIP_MODEL=b1-tfidf-logreg uvicorn ntip.ml.service:create_inference_app --factory --port 8100
"""

import os
from collections.abc import Callable

from fastapi import FastAPI
from pydantic import BaseModel

from ntip.ml.contract import CONTRACT_VERSION, InferenceRequest, InferenceResponse
from ntip.ml.extractors import ModelExtractor, RulesAsModel


def _b1() -> ModelExtractor:
    from ntip.ml.b1 import B1Model  # needs the "ml" extra (scikit-learn)

    return B1Model()


def _b2() -> ModelExtractor:
    from ntip.ml.b2 import B2Model  # needs the "llm" extra and NTIP_B2_ALLOW_EXTERNAL=1

    return B2Model()


# Factories, so heavy model dependencies are only imported when selected.
MODELS: dict[str, Callable[[], ModelExtractor]] = {
    "b0-rules-as-model": RulesAsModel,
    "b1-tfidf-logreg": _b1,
    "b2-claude-structured": _b2,
}


class ModelInfo(BaseModel):
    model_id: str
    model_version: str
    contract_version: str


def load_model(name: str | None = None) -> ModelExtractor:
    name = name or os.environ.get("NTIP_MODEL", "b0-rules-as-model")
    if name not in MODELS:
        raise ValueError(f"unknown model {name!r}; available: {sorted(MODELS)}")
    return MODELS[name]()


def create_inference_app(model: ModelExtractor | None = None) -> FastAPI:
    model = model or load_model()
    app = FastAPI(
        title="NTIP inference service (research)",
        description="Proposes candidate observations only. SIMULATION ONLY.",
    )

    @app.post("/v1/infer")
    def infer(request: InferenceRequest) -> InferenceResponse:
        return model.infer(request)

    @app.get("/model-info")
    def model_info() -> ModelInfo:
        return ModelInfo(
            model_id=model.model_id,
            model_version=model.model_version,
            contract_version=CONTRACT_VERSION,
        )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
