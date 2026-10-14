from io import BytesIO
from datetime import date, datetime

import pandas as pd

from domain.input_bundle import InputBundle, InputFile, SheetPreview


def to_json_value(value):
    if pd.isna(value):
        return None

    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()

    if isinstance(value, (datetime, date)):
        return value

    if hasattr(value, "item"):
        return value.item()

    return value


def dataframe_to_records(
    dataframe: pd.DataFrame,
) -> list[dict]:
    return [
        {
            str(column): to_json_value(value)
            for column, value in row.items()
        }
        for row in dataframe.to_dict(
            orient="records"
        )
    ]


def build_input_bundle(
    text: str,
    uploaded_files,
) -> InputBundle:
    return InputBundle(
        text=text,
        files=[
            build_input_file(
                uploaded_file
            )
            for uploaded_file in uploaded_files
        ],
    )


def build_input_file(
    uploaded_file,
    max_rows_per_sheet: int = 30,
) -> InputFile:
    name = uploaded_file.name
    file_type = infer_file_type(
        name
    )
    content = uploaded_file.getvalue()

    try:
        if file_type in {
            "xlsx",
            "xls",
        }:
            return build_excel_input_file(
                name=name,
                file_type=file_type,
                content=content,
                max_rows_per_sheet=max_rows_per_sheet,
            )

        if file_type == "csv":
            return build_csv_input_file(
                name=name,
                content=content,
                max_rows=max_rows_per_sheet,
            )

        return InputFile(
            name=name,
            file_type=file_type,
            size_bytes=len(content),
            text_excerpt=decode_text(
                content
            )[:12000],
        )

    except Exception as exc:
        return InputFile(
            name=name,
            file_type=file_type,
            size_bytes=len(content),
            read_error=str(exc),
        )


def build_excel_input_file(
    name: str,
    file_type: str,
    content: bytes,
    max_rows_per_sheet: int,
) -> InputFile:
    workbook = pd.ExcelFile(
        BytesIO(content)
    )

    sheets = []

    for sheet_name in workbook.sheet_names:
        df = pd.read_excel(
            workbook,
            sheet_name=sheet_name,
        )

        sheets.append(
            SheetPreview(
                name=sheet_name,
                columns=[
                    str(column)
                    for column in df.columns
                ],
                row_count=len(df),
                preview_csv=df.head(
                    max_rows_per_sheet
                ).to_csv(
                    index=False
                ),
                records=dataframe_to_records(df),
            )
        )

    return InputFile(
        name=name,
        file_type=file_type,
        size_bytes=len(content),
        sheets=sheets,
    )


def build_csv_input_file(
    name: str,
    content: bytes,
    max_rows: int,
) -> InputFile:
    df = pd.read_csv(
        BytesIO(content)
    )

    return InputFile(
        name=name,
        file_type="csv",
        size_bytes=len(content),
        sheets=[
            SheetPreview(
                name="csv",
                columns=[
                    str(column)
                    for column in df.columns
                ],
                row_count=len(df),
                preview_csv=df.head(
                    max_rows
                ).to_csv(
                    index=False
                ),
                records=dataframe_to_records(df),
            )
        ],
    )


def input_bundle_to_prompt(
    bundle: InputBundle,
) -> str:
    sections = []

    if bundle.text.strip():
        sections.append(
            "用户本轮输入：\n"
            f"{bundle.text}"
        )

    for index, input_file in enumerate(
        bundle.files,
        start=1,
    ):
        sections.append(
            input_file_to_prompt(
                input_file,
                index=index,
            )
        )

    return "\n\n".join(
        sections
    )


def input_file_to_prompt(
    input_file: InputFile,
    index: int | None = None,
) -> str:
    label = (
        f"File {index}"
        if index is not None
        else "File"
    )

    lines = [
        f"[{label}: {input_file.name}]",
        f"type: {input_file.file_type}",
        f"size_bytes: {input_file.size_bytes}",
    ]

    if input_file.read_error:
        lines.append(
            f"read_error: {input_file.read_error}"
        )
        return "\n".join(
            lines
        )

    for sheet in input_file.sheets:
        lines.extend(
            [
                f"\n[Sheet: {sheet.name}]",
                f"row_count: {sheet.row_count}",
                f"columns: {', '.join(sheet.columns)}",
                "preview_csv:",
                sheet.preview_csv,
            ]
        )

    if input_file.text_excerpt:
        lines.extend(
            [
                "text_excerpt:",
                input_file.text_excerpt,
            ]
        )

    return "\n".join(
        lines
    )


def infer_file_type(
    file_name: str,
) -> str:
    if "." not in file_name:
        return "unknown"

    return file_name.rsplit(
        ".",
        1,
    )[-1].lower()


def decode_text(
    content: bytes,
) -> str:
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return content.decode(
            "gb18030",
            errors="replace",
        )
