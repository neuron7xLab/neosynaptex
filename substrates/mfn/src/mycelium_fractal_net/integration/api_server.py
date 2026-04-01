from __future__ import annotations

import time
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, model_validator

from mycelium_fractal_net import __version__
from mycelium_fractal_net.analytics.morphology import compute_morphology_descriptor
from mycelium_fractal_net.core.compare import compare as compare_sequences
from mycelium_fractal_net.core.detect import detect_anomaly
from mycelium_fractal_net.core.forecast import forecast_next
from mycelium_fractal_net.core.simulate import simulate_final, simulate_history
from mycelium_fractal_net.pipelines.reporting import build_analysis_report
from mycelium_fractal_net.types.field import (
    FieldSequence,
    GABAATonicSpec,
    NeuromodulationSpec,
    ObservationNoiseSpec,
    SerotonergicPlasticitySpec,
    SimulationSpec,
)

API_VERSION = "v1"
SERVICE_START = time.monotonic()
_METRICS: dict[str, float] = defaultdict(float)


def _observe(name: str, latency_s: float) -> None:
    _METRICS[f"{name}_requests"] += 1.0
    _METRICS[f"{name}_latency_total_s"] += float(latency_s)
    _METRICS["runtime_latency_last_ms"] = float(latency_s * 1000.0)


def _avg_ms(name: str) -> float:
    count = _METRICS.get(f"{name}_requests", 0.0)
    if count <= 0:
        return 0.0
    return float((_METRICS.get(f"{name}_latency_total_s", 0.0) / count) * 1000.0)


def health_payload() -> dict[str, Any]:
    return {
        "status": "healthy",
        "version": __version__,
        "engine_version": __version__,
        "api_version": API_VERSION,
        "uptime": max(0.0, time.monotonic() - SERVICE_START),
    }


def metrics_payload() -> dict[str, Any]:
    return {
        "simulation_requests": int(_METRICS.get("simulation_requests", 0.0)),
        "extract_requests": int(_METRICS.get("extract_requests", 0.0)),
        "detect_requests": int(_METRICS.get("detect_requests", 0.0)),
        "forecast_requests": int(_METRICS.get("forecast_requests", 0.0)),
        "compare_requests": int(_METRICS.get("compare_requests", 0.0)),
        "report_requests": int(_METRICS.get("report_requests", 0.0)),
        "runtime_latency": {
            "last_ms": float(_METRICS.get("runtime_latency_last_ms", 0.0)),
            "simulation_avg_ms": _avg_ms("simulation"),
            "extract_avg_ms": _avg_ms("extract"),
            "detect_avg_ms": _avg_ms("detect"),
            "forecast_avg_ms": _avg_ms("forecast"),
            "compare_avg_ms": _avg_ms("compare"),
            "report_avg_ms": _avg_ms("report"),
        },
    }


class GABAATonicPayload(BaseModel):
    profile: str = "baseline_nominal"
    agonist_concentration_um: float = Field(default=0.0, ge=0.0)
    resting_affinity_um: float = Field(default=0.0, ge=0.0)
    active_affinity_um: float = Field(default=0.0, ge=0.0)
    desensitization_rate_hz: float = Field(default=0.0, ge=0.0)
    recovery_rate_hz: float = Field(default=0.0, ge=0.0)
    shunt_strength: float = Field(default=0.0, ge=0.0, le=1.0)
    rest_offset_mv: float = 0.0


class SerotonergicPayload(BaseModel):
    profile: str = "baseline_nominal"
    gain_fluidity_coeff: float = 0.0
    reorganization_drive: float = 0.0
    coherence_bias: float = 0.0


class ObservationNoisePayload(BaseModel):
    profile: str = "baseline_nominal"
    std: float = Field(default=0.0, ge=0.0)
    temporal_smoothing: float = Field(default=0.0, ge=0.0, le=1.0)


class NeuromodulationPayload(BaseModel):
    profile: str = "baseline_nominal"
    enabled: bool = False
    dt_seconds: float = Field(default=1.0, gt=0.0)
    intrinsic_field_jitter: bool = False
    intrinsic_field_jitter_var: float = Field(default=0.0005, ge=0.0, le=0.01)
    gabaa_tonic: GABAATonicPayload | None = None
    serotonergic: SerotonergicPayload | None = None
    observation_noise: ObservationNoisePayload | None = None


class SimulationPayload(BaseModel):
    seed: int = 42
    grid_size: int = Field(default=32, ge=4)
    steps: int = Field(default=24, ge=1)
    alpha: float = Field(default=0.18, gt=0.0, le=0.25)
    spike_probability: float = Field(default=0.25, ge=0.0, le=1.0)
    turing_enabled: bool = True
    turing_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    quantum_jitter: bool = False
    jitter_var: float = Field(default=0.0005, ge=0.0, le=0.01)
    neuromodulation: NeuromodulationPayload | None = None
    with_history: bool = False


class FieldPayload(BaseModel):
    history: list[list[list[float]]] | None = None
    field: list[list[float]] | None = None
    spec: SimulationPayload | None = None


class ForecastPayload(FieldPayload):
    horizon: int = Field(default=8, ge=1)


class ComparePayload(BaseModel):
    left: FieldPayload
    right: FieldPayload


class ReportPayload(ForecastPayload):
    output_root: str = Field(
        default="artifacts/runs",
        max_length=500,
        description="Path for report output. No '..' traversal allowed.",
    )

    @model_validator(mode="after")
    def _validate_output_root(self) -> ReportPayload:
        """Prevent path traversal attacks."""
        if ".." in self.output_root:
            msg = "output_root must not contain '..' (path traversal)"
            raise ValueError(msg)
        return self


def _spec_from_payload(req: SimulationPayload) -> SimulationSpec:
    payload = req.model_dump(exclude={"with_history"})
    neuromod = payload.get("neuromodulation")
    payload["neuromodulation"] = (
        None
        if neuromod is None
        else NeuromodulationSpec(
            profile=neuromod.get("profile", "baseline_nominal"),
            enabled=bool(neuromod.get("enabled", False)),
            dt_seconds=float(neuromod.get("dt_seconds", 1.0)),
            intrinsic_field_jitter=bool(neuromod.get("intrinsic_field_jitter", False)),
            intrinsic_field_jitter_var=float(neuromod.get("intrinsic_field_jitter_var", 0.0005)),
            gabaa_tonic=(
                None
                if neuromod.get("gabaa_tonic") is None
                else GABAATonicSpec(**neuromod["gabaa_tonic"])
            ),
            serotonergic=(
                None
                if neuromod.get("serotonergic") is None
                else SerotonergicPlasticitySpec(**neuromod["serotonergic"])
            ),
            observation_noise=(
                None
                if neuromod.get("observation_noise") is None
                else ObservationNoiseSpec(**neuromod["observation_noise"])
            ),
        )
    )
    return SimulationSpec(**payload)


def _sequence_from_payload(payload: FieldPayload) -> FieldSequence:
    import numpy as np

    if payload.history is not None:
        hist = np.asarray(payload.history, dtype=np.float64)
        return FieldSequence(field=hist[-1], history=hist, spec=None, metadata={})
    if payload.field is not None:
        fld = np.asarray(payload.field, dtype=np.float64)
        return FieldSequence(field=fld, history=None, spec=None, metadata={})
    if payload.spec is not None:
        spec = _spec_from_payload(payload.spec)
        return simulate_history(spec) if payload.spec.with_history else simulate_final(spec)
    raise HTTPException(status_code=400, detail="Provide history, field, or spec")


def build_v1_router() -> APIRouter:
    router = APIRouter(tags=["mfn-v1"])

    @router.post("/simulate")
    async def simulate_endpoint(request: SimulationPayload) -> dict[str, Any]:
        start = time.perf_counter()
        spec = _spec_from_payload(request)
        seq = simulate_history(spec) if request.with_history else simulate_final(spec)
        _observe("simulation", time.perf_counter() - start)
        return seq.to_dict(include_arrays=True)

    @router.post("/extract")
    async def extract_endpoint(payload: FieldPayload) -> dict[str, Any]:
        start = time.perf_counter()
        result = compute_morphology_descriptor(_sequence_from_payload(payload)).to_dict()
        _observe("extract", time.perf_counter() - start)
        return result

    @router.post("/detect")
    async def detect_endpoint(payload: FieldPayload) -> dict[str, Any]:
        start = time.perf_counter()
        result = detect_anomaly(_sequence_from_payload(payload)).to_dict()
        _observe("detect", time.perf_counter() - start)
        return result

    @router.post("/forecast")
    async def forecast_endpoint(payload: ForecastPayload) -> dict[str, Any]:
        start = time.perf_counter()
        seq = _sequence_from_payload(payload)
        if not seq.has_history:
            seq = FieldSequence(
                field=seq.field,
                history=seq.field[None, :, :],
                spec=seq.spec,
                metadata=seq.metadata,
            )
        result = forecast_next(seq, horizon=payload.horizon).to_dict()
        _observe("forecast", time.perf_counter() - start)
        return result

    @router.post("/compare")
    async def compare_endpoint(payload: ComparePayload) -> dict[str, Any]:
        start = time.perf_counter()
        result = compare_sequences(
            _sequence_from_payload(payload.left), _sequence_from_payload(payload.right)
        ).to_dict()
        _observe("compare", time.perf_counter() - start)
        return result

    @router.post("/report")
    async def report_endpoint(payload: ReportPayload) -> dict[str, Any]:
        start = time.perf_counter()
        seq = _sequence_from_payload(payload)
        if not seq.has_history:
            seq = FieldSequence(
                field=seq.field,
                history=seq.field[None, :, :],
                spec=seq.spec,
                metadata=seq.metadata,
            )
        result = build_analysis_report(
            seq, output_root=payload.output_root, horizon=payload.horizon
        ).to_dict()
        _observe("report", time.perf_counter() - start)
        return result

    return router


v1_router = build_v1_router()


def register_canonical_routes(app: FastAPI) -> None:
    app.include_router(v1_router, prefix="/v1")

    @app.get("/health", include_in_schema=False)
    async def canonical_health() -> dict[str, Any]:
        return health_payload()

    @app.get("/metrics", include_in_schema=False)
    async def canonical_metrics() -> JSONResponse:
        return JSONResponse(metrics_payload())


def create_app() -> FastAPI:
    app = FastAPI(title="Morphology-aware Field Intelligence Engine", version=__version__)
    register_canonical_routes(app)
    return app


app = create_app()

__all__ = [
    "API_VERSION",
    "ComparePayload",
    "FieldPayload",
    "ForecastPayload",
    "ReportPayload",
    "SimulationPayload",
    "app",
    "build_v1_router",
    "create_app",
    "health_payload",
    "metrics_payload",
    "register_canonical_routes",
    "v1_router",
]
