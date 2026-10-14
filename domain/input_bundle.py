from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class SheetPreview(BaseModel):
    name: str
    columns: list[str] = Field(
        default_factory=list
    )
    row_count: int | None = None
    preview_csv: str = ""
    records: list[dict[str, Any]] = Field(
        default_factory=list
    )


class InputFile(BaseModel):
    id: str = Field(
        default_factory=lambda: uuid4().hex
    )
    name: str
    file_type: str
    size_bytes: int
    sheets: list[SheetPreview] = Field(
        default_factory=list
    )
    text_excerpt: str | None = None
    read_error: str | None = None


class InputBundle(BaseModel):
    text: str = ""
    files: list[InputFile] = Field(
        default_factory=list
    )
    created_at: datetime = Field(
        default_factory=datetime.now
    )
