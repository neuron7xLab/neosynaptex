"""V1 REST API endpoints — typed pipeline surface."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from mycelium_fractal_net.analytics.morphology import compute_morphology_descriptor
from mycelium_fractal_net.core.compare import compare
from mycelium_fractal_net.core.detect import detect_anomaly
from mycelium_fractal_net.core.forecast import forecast_next
from mycelium_fractal_net.core.simulate import simulate_final, simulate_history
from mycelium_fractal_net.pipelines.reporting import build_analysis_report
from mycelium_fractal_net.types.field import FieldSequence, SimulationSpec

v1_router = APIRouter(tags=["v1"])


class V1SimulationRequest(BaseModel):
    seed: int = 42
    grid_size: int = Field(default=32, ge=4)
    steps: int = Field(default=24, ge=1)
    alpha: float = Field(default=0.18, gt=0.0, le=0.25)
    spike_probability: float = Field(default=0.25, ge=0.0, le=1.0)
    turing_enabled: bool = True
    turing_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    quantum_jitter: bool = False
    jitter_var: float = Field(default=0.0005, ge=0.0, le=0.01)
    with_history: bool = False


class V1FieldPayload(BaseModel):
    history: list[list[list[float]]] | None = None
    field: list[list[float]] | None = None
    spec: V1SimulationRequest | None = None


def _spec_from_v1(req: V1SimulationRequest) -> SimulationSpec:
    return SimulationSpec(**req.model_dump(exclude={"with_history"}))


def _sequence_from_payload(payload: V1FieldPayload) -> FieldSequence:
    if payload.history is not None:
        import numpy as np

        hist = np.asarray(payload.history, dtype=np.float64)
        return FieldSequence(field=hist[-1], history=hist, spec=None, metadata={})
    if payload.field is not None:
        import numpy as np

        fld = np.asarray(payload.field, dtype=np.float64)
        return FieldSequence(field=fld, history=None, spec=None, metadata={})
    if payload.spec is not None:
        spec = _spec_from_v1(payload.spec)
        return simulate_history(spec) if payload.spec.with_history else simulate_final(spec)
    raise HTTPException(status_code=400, detail="Provide history, field, or spec")


@v1_router.post("/v1/simulate")
async def v1_simulate(request: V1SimulationRequest) -> dict:

    spec = _spec_from_v1(request)
    loop = asyncio.get_running_loop()
    fn = simulate_history if request.with_history else simulate_final
    seq = await loop.run_in_executor(None, fn, spec)
    return seq.to_dict(include_arrays=True)


@v1_router.post("/v1/extract")
async def v1_extract(payload: V1FieldPayload) -> dict:

    seq = _sequence_from_payload(payload)
    loop = asyncio.get_running_loop()
    desc = await loop.run_in_executor(None, compute_morphology_descriptor, seq)
    return {"descriptor": desc.to_dict()}


@v1_router.post("/v1/detect")
async def v1_detect(payload: V1FieldPayload) -> dict:
    seq = _sequence_from_payload(payload)
    return {"detection": detect_anomaly(seq).to_dict()}


class V1ForecastRequest(V1FieldPayload):
    horizon: int = Field(default=8, ge=1)


@v1_router.post("/v1/forecast")
async def v1_forecast(payload: V1ForecastRequest) -> dict:
    seq = _sequence_from_payload(payload)
    if not seq.has_history:
        seq = (
            simulate_history(seq.spec)
            if seq.spec is not None
            else FieldSequence(
                field=seq.field,
                history=seq.field[None, :, :],
                spec=seq.spec,
                metadata=seq.metadata,
            )
        )
    return {"forecast": forecast_next(seq, horizon=payload.horizon).to_dict()}


class V1CompareRequest(BaseModel):
    left: V1FieldPayload
    right: V1FieldPayload


@v1_router.post("/v1/compare")
async def v1_compare(payload: V1CompareRequest) -> dict:
    left = _sequence_from_payload(payload.left)
    right = _sequence_from_payload(payload.right)
    return {"comparison": compare(left, right).to_dict()}


class V1ReportRequest(V1ForecastRequest):
    output_root: str = "artifacts/runs"


@v1_router.post("/v1/report")
async def v1_report(payload: V1ReportRequest) -> dict:
    seq = _sequence_from_payload(payload)
    if not seq.has_history:
        seq = (
            simulate_history(seq.spec)
            if seq.spec is not None
            else FieldSequence(
                field=seq.field,
                history=seq.field[None, :, :],
                spec=seq.spec,
                metadata=seq.metadata,
            )
        )
    report = build_analysis_report(seq, output_root=payload.output_root, horizon=payload.horizon)
    return report.to_dict()


def main(host: str | None = None, port: int | None = None) -> None:
    """Run the FastAPI server with uvicorn."""
    import os

    import uvicorn

    resolved_host = host or os.getenv("MFN_HOST", "0.0.0.0")  # nosec B104
    resolved_port = int(port or int(os.getenv("MFN_PORT", "8000")))
    from mycelium_fractal_net.api import app

    uvicorn.run(app, host=resolved_host, port=resolved_port)
