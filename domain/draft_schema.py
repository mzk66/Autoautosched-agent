from pydantic import BaseModel, Field


class MissingQuestion(BaseModel):
    field: str
    question: str
    input_type: str = "text"
    options: list[str] | None = None


class DraftJob(BaseModel):
    id: str | None = None
    product: str | None = None
    quantity: float | None = None
    due_time: str | None = None
    priority: str | None = None
    customer_type: str | None = None
    notes: str | None = None


class DraftMachine(BaseModel):
    id: str | None = None
    supported_products: list[str] = Field(
        default_factory=list
    )
    rates: dict[str, float] = Field(
        default_factory=dict
    )
    daily_start: str | None = None
    daily_end: str | None = None
    notes: str | None = None


class DraftMaintenance(BaseModel):
    machine_id: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    note: str | None = None


class ExtractedDraft(BaseModel):
    jobs: list[DraftJob] = Field(
        default_factory=list
    )
    machines: list[DraftMachine] = Field(
        default_factory=list
    )
    maintenance: list[DraftMaintenance] = Field(
        default_factory=list
    )
    objectives: list[str] = Field(
        default_factory=list
    )
    constraints: list[str] = Field(
        default_factory=list
    )
    assumptions: list[str] = Field(
        default_factory=list
    )
    missing_questions: list[MissingQuestion] = Field(
        default_factory=list
    )
