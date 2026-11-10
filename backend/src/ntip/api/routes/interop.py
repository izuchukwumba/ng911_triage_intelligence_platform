"""/v1/interop endpoints (design v1.2, sections 3B.3 and 3B.5).

Project-defined endpoints, not NENA-standard ones: an HTTP 202 here means the
payload was accepted for *local* advisory processing, not an NG911
acknowledgement. Interop is disabled (fail closed) unless tenant credentials
are configured in NTIP_INTEROP_TOKENS, and every receipt is visible only to
the tenant that submitted it.
"""

import hmac
from typing import Annotated

from fastapi import APIRouter, Header, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from ntip.api.errors import correlation_id
from ntip.interop.gateway import (
    EidoGateway,
    PayloadTooLarge,
    RevisionConflict,
    UnsupportedProfile,
)
from ntip.interop.receipts import InteropReceipt, ReceiptStatus
from ntip.store import UnknownIncident

router = APIRouter(prefix="/v1/interop", tags=["interop"])

_REJECTED = {ReceiptStatus.QUARANTINED, ReceiptStatus.UNSUPPORTED_VERSION}


class ReceiptOut(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    receiptId: str
    status: ReceiptStatus
    sourceDigest: str
    adapterVersion: str
    profileId: str
    assessmentStatus: str
    incidentId: str | None
    problems: list[str]

    @classmethod
    def of(cls, receipt: InteropReceipt) -> "ReceiptOut":
        if receipt.assessment_id:
            assessment = "assessed"
        elif receipt.status in _REJECTED:
            assessment = "not_processed"
        else:
            assessment = "no_new_narrative"
        return cls(
            receiptId=receipt.receipt_id,
            status=receipt.status,
            sourceDigest=receipt.payload_digest,
            adapterVersion=receipt.adapter_version,
            profileId=receipt.profile_id,
            assessmentStatus=assessment,
            incidentId=receipt.incident_id,
            problems=receipt.problems,
        )


def _error(request: Request, code: int, kind: str, message: str) -> JSONResponse:
    cid = correlation_id(request)
    return JSONResponse(
        status_code=code,
        content={"error": {"code": kind, "message": message, "correlation_id": cid}},
    )


def _tenant(request: Request, authorization: str | None) -> str | JSONResponse:
    tokens: dict[str, str] = request.app.state.interop_tokens
    if not tokens:
        return _error(request, 403, "interop_disabled", "Interop is not enabled on this server.")
    presented = (authorization or "").removeprefix("Bearer ").strip()
    for token, tenant in tokens.items():
        if presented and hmac.compare_digest(presented, token):
            return tenant
    return _error(request, 401, "unauthorized", "Missing or invalid interop credentials.")


def _gateway(request: Request) -> EidoGateway:
    gateway: EidoGateway = request.app.state.eido_gateway
    return gateway


@router.post("/eido/ingest", status_code=status.HTTP_202_ACCEPTED, response_model=None)
async def ingest_eido(
    request: Request,
    response: Response,
    authorization: Annotated[str | None, Header()] = None,
    x_interop_profile: Annotated[str | None, Header()] = None,
    content_type: Annotated[str | None, Header()] = None,
) -> ReceiptOut | JSONResponse:
    tenant = _tenant(request, authorization)
    if isinstance(tenant, JSONResponse):
        return tenant
    if not (content_type or "").startswith("application/json"):
        return _error(request, 415, "unsupported_media_type", "Send application/json.")
    raw = await request.body()
    try:
        result = _gateway(request).ingest(
            raw,
            tenant_id=tenant,
            profile_id=x_interop_profile or "",
            correlation_id=correlation_id(request),
        )
    except UnsupportedProfile:
        expected = _gateway(request).profile.profile_id
        return _error(request, 422, "unsupported_profile", f"X-Interop-Profile must be {expected}.")
    except PayloadTooLarge:
        return _error(request, 413, "payload_too_large", "Payload exceeds the size limit.")
    except RevisionConflict:
        return _error(
            request, 409, "revision_conflict",
            "This EIDO revision was already received with different content.",
        )  # fmt: skip
    if not result.replayed:
        request.app.state.metrics.inc(
            "ntip_interop_receipts_total", status=str(result.receipt.status)
        )
    out = ReceiptOut.of(result.receipt)
    if result.receipt.status in _REJECTED:
        return JSONResponse(status_code=422, content=out.model_dump(mode="json"))
    if result.replayed:
        response.headers["Idempotent-Replayed"] = "true"
    return out


def _own_receipt(request: Request, receipt_id: str, tenant: str) -> InteropReceipt:
    receipt = _gateway(request).pipeline.store.interop_receipt(receipt_id)
    # Another tenant's receipt is indistinguishable from a missing one.
    if receipt is None or receipt.tenant_id != tenant:
        raise UnknownIncident(receipt_id)
    return receipt


@router.get("/receipts/{receipt_id}", response_model=None)
def get_receipt(
    receipt_id: str, request: Request, authorization: Annotated[str | None, Header()] = None
) -> InteropReceipt | JSONResponse:
    tenant = _tenant(request, authorization)
    if isinstance(tenant, JSONResponse):
        return tenant
    return _own_receipt(request, receipt_id, tenant)


@router.get("/receipts/{receipt_id}/payload", response_model=None)
def get_receipt_payload(
    receipt_id: str, request: Request, authorization: Annotated[str | None, Header()] = None
) -> Response:
    """The original payload, unchanged (design v1.2, INT-011)."""
    tenant = _tenant(request, authorization)
    if isinstance(tenant, JSONResponse):
        return tenant
    receipt = _own_receipt(request, receipt_id, tenant)
    return Response(content=receipt.payload, media_type="application/json")
