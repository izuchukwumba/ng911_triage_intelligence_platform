"""Standalone inference service (design v1.2, section 3A.3).

Runs separately from the platform API and holds no state: it receives an
InferenceRequest and returns an InferenceResponse. Transcript text is treated
strictly as data to extract from, never as instructions.

    NTIP_MODEL=b0-rules-as-model uvicorn ntip.ml.service:create_inference_app --factory --port 8100
"""

import os

from fastapi import FastAPI
from pydantic import BaseModel

from ntip.ml.contract import CONTRACT_VERSION, InferenceRequest, InferenceResponse
from ntip.ml.extractors import ModelExtractor, RulesAsModel

MODELS: dict[str, type] = {"b0-rules-as-model": RulesAsModel}


class ModelInfo(BaseModel):
    model_id: str
    model_version: str
    contract_version: str


def load_model(name: str | None = None) -> ModelExtractor:
    name = name or os.environ.get("NTIP_MODEL", "b0-rules-as-model")
    if name not in MODELS:
        raise ValueError(f"unknown model {name!r}; available: {sorted(MODELS)}")
    model: ModelExtractor = MODELS[name]()
    return model


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
