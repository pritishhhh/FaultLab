from typing import Literal

from pydantic import BaseModel, Field, model_validator

FaultType = Literal["latency", "http_errors", "timeout", "dependency_unavailable", "cpu_pressure"]


class ServiceCreate(BaseModel):
    name: Literal["gateway"]


class FaultInput(BaseModel):
    type: FaultType
    latency_ms: int | None = Field(default=None, ge=0, le=1000)
    error_rate: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def check_parameters(self):
        if self.type in ("latency", "timeout") and self.latency_ms is None:
            raise ValueError("latency_ms is required")
        if self.type == "http_errors" and self.error_rate is None:
            raise ValueError("error_rate is required")
        if self.type == "timeout" and self.latency_ms is not None and self.latency_ms < 200:
            raise ValueError("timeout latency must be at least 200 ms")
        return self


class ExperimentCreate(BaseModel):
    service_id: str
    requests_per_second: int = Field(ge=1, le=50)
    concurrency: int = Field(ge=1, le=20)
    baseline_seconds: int = Field(ge=1, le=300)
    fault_seconds: int = Field(ge=1, le=300)
    recovery_seconds: int = Field(ge=1, le=300)
    timeout_seconds: float = Field(default=1.0, ge=0.1, le=10)
    fault: FaultInput


class ErrorBody(BaseModel):
    error: dict[str, str]
