from domain.input_bundle import InputFile, SheetPreview
from domain.workflow_schema import DataIssue, ParsedJob, ParsedSchedulingData
from domain.parsing.common import _column_map, _is_missing, _parse_datetime, _parse_enum, _parse_identifier, _parse_number, _raw_value, _source_label


def _parse_orders(
    input_file: InputFile,
    sheet: SheetPreview,
    records: list[dict],
    parsed: ParsedSchedulingData,
):
    columns = _column_map(sheet.columns)
    priority_mapping = {
        "high": "high",
        "高": "high",
        "normal": "normal",
        "普通": "normal",
    }
    customer_mapping = {
        "vip": "VIP",
        "normal": "normal",
        "普通": "normal",
    }

    for index, row in enumerate(records):
        source = _source_label(
            input_file,
            sheet,
            index,
        )
        product_value = _raw_value(
            row,
            columns,
            "product",
        )

        if _is_missing(product_value):
            parsed.unresolved_issues.append(
                DataIssue(
                    code="missing_product",
                    message=f"{source} 缺少 product。",
                    source=source,
                    field="product",
                )
            )

        parsed.jobs.append(
            ParsedJob(
                source=source,
                id=_parse_identifier(
                    _raw_value(row, columns, "order_id"),
                    "job id",
                    source,
                    parsed,
                ),
                product=(
                    str(product_value).strip()
                    if not _is_missing(product_value)
                    else None
                ),
                quantity=_parse_number(
                    _raw_value(row, columns, "quantity"),
                    "quantity",
                    source,
                    parsed,
                ),
                due_time=_parse_datetime(
                    _raw_value(row, columns, "due_time"),
                    "due_time",
                    source,
                    parsed,
                ),
                priority=_parse_enum(
                    _raw_value(row, columns, "priority"),
                    "priority",
                    source,
                    parsed,
                    priority_mapping,
                ),
                customer_type=_parse_enum(
                    _raw_value(row, columns, "customer_type"),
                    "customer_type",
                    source,
                    parsed,
                    customer_mapping,
                ),
            )
        )
