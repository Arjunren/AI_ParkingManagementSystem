from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class TrafficStatus(str, Enum):
    low = "low"
    normal = "normal"
    high = "high"
    critical = "critical"


class Priority(str, Enum):
    low = "Low"
    medium = "Medium"
    high = "High"
    critical = "Critical"


class PeakPeriod(StrictModel):
    start: str = Field(max_length=10)
    end: str = Field(max_length=10)
    visitor_count: int = Field(ge=0)
    evidence: str = Field(min_length=3, max_length=300)


class Finding(StrictModel):
    subject: str = Field(min_length=1, max_length=160)
    observation: str = Field(min_length=3, max_length=500)
    evidence: str = Field(min_length=3, max_length=500)


class PriorityIssue(StrictModel):
    title: str = Field(min_length=3, max_length=180)
    priority: Priority
    reason: str = Field(min_length=3, max_length=500)


class OperationsAnalysis(StrictModel):
    traffic_status: TrafficStatus
    peak_periods: list[PeakPeriod] = Field(default_factory=list, max_length=12)
    congested_zones: list[Finding] = Field(default_factory=list, max_length=20)
    facility_concerns: list[Finding] = Field(default_factory=list, max_length=20)
    maintenance_patterns: list[Finding] = Field(default_factory=list, max_length=20)
    incident_patterns: list[Finding] = Field(default_factory=list, max_length=20)
    feedback_patterns: list[Finding] = Field(default_factory=list, max_length=20)
    reservation_patterns: list[Finding] = Field(default_factory=list, max_length=20)
    priority_issues: list[PriorityIssue] = Field(default_factory=list, max_length=20)
    data_gaps: list[str] = Field(default_factory=list, max_length=12)
    summary: str = Field(min_length=3, max_length=1200)


class Recommendation(StrictModel):
    title: str = Field(min_length=3, max_length=180)
    category: str = Field(min_length=3, max_length=80)
    priority: Priority
    priority_reason: str = Field(min_length=3, max_length=300)
    reason: str = Field(min_length=3, max_length=600)
    recommended_action: str = Field(min_length=3, max_length=800)
    related_zone: str = Field(default="", max_length=120)
    related_facility: str = Field(default="", max_length=120)


class RecommendationBatch(StrictModel):
    needs_additional_analysis: bool = False
    additional_analysis_request: str = Field(default="", max_length=500)
    recommendations: list[Recommendation] = Field(default_factory=list, max_length=20)
    summary: str = Field(min_length=3, max_length=1000)

    @model_validator(mode="after")
    def request_is_present_when_needed(self):
        if self.needs_additional_analysis and not self.additional_analysis_request:
            raise ValueError("additional_analysis_request is required when more analysis is needed")
        return self

