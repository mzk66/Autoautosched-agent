from io import StringIO
import pandas as pd
from domain.input_bundle import InputFile, SheetPreview
from domain.workflow_schema import DataIssue, FileInspection
from domain.parsing.common import _column_map, _record_value


def sheet_records(
    sheet: SheetPreview,
) -> list[dict]:
    if sheet.records:
        return sheet.records

    if not sheet.preview_csv.strip():
        return []

    dataframe = pd.read_csv(
        StringIO(sheet.preview_csv)
    )

    return [
        {
            str(column): _record_value(value)
            for column, value in row.items()
        }
        for row in dataframe.to_dict(
            orient="records"
        )
    ]


def inspect_input_files(
    input_files: list[InputFile],
) -> FileInspection:
    report = FileInspection(
        file_count=len(input_files),
        sheet_count=sum(
            len(input_file.sheets)
            for input_file in input_files
        ),
    )

    for input_file in input_files:
        report.source_facts.append(
            f"文件 {input_file.name}，{len(input_file.sheets)} 个工作表"
        )

        if input_file.read_error:
            report.issues.append(
                DataIssue(
                    code="file_read_error",
                    message=(
                        f"无法读取 {input_file.name}: "
                        f"{input_file.read_error}"
                    ),
                    source=input_file.name,
                )
            )

        for sheet in input_file.sheets:
            records = sheet_records(sheet)

            if (
                sheet.row_count is not None
                and len(records) < sheet.row_count
            ):
                report.issues.append(
                    DataIssue(
                        code="incomplete_file_content",
                        message=(
                            f"{input_file.name}/{sheet.name} 只有 "
                            f"{len(records)} 行可用，源文件共有 "
                            f"{sheet.row_count} 行，请重新上传。"
                        ),
                        source=f"{input_file.name}/{sheet.name}",
                    )
                )

    return report


def _sheet_role(columns) -> str | None:
    mapping = _column_map(columns)

    if {
        "order_id",
        "product",
        "quantity",
    }.issubset(mapping):
        return "orders"

    if {
        "machine_id",
        "supported_products",
    }.issubset(mapping):
        return "machines"

    if {
        "machine_id",
        "start_time",
        "end_time",
    }.issubset(mapping):
        return "maintenance"

    if "description" in mapping:
        return "rules"

    return None
