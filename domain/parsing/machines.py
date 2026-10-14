import re
from domain.input_bundle import InputFile, SheetPreview
from domain.workflow_schema import DataIssue, InferredMapping, ParsedMachine, ParsedMaintenance, ParsedSchedulingData
from domain.parsing.common import _column_map, _is_missing, _parse_clock, _parse_datetime, _parse_identifier, _parse_number, _rate_column, _raw_value, _source_label, _split_products


def _parse_machines(
    input_file: InputFile,
    sheet: SheetPreview,
    records: list[dict],
    parsed: ParsedSchedulingData,
):
    columns = _column_map(sheet.columns)

    for index, row in enumerate(records):
        source = _source_label(
            input_file,
            sheet,
            index,
        )
        products = _split_products(
            _raw_value(
                row,
                columns,
                "supported_products",
            )
        )
        rates = {}

        for product in products:
            column = _rate_column(
                sheet.columns,
                product,
            )
            rate = _parse_number(
                row.get(column) if column else None,
                f"rate[{product}]",
                source,
                parsed,
            )

            if rate is not None:
                rates[product] = rate

        shift_value = _raw_value(
            row,
            columns,
            "shift",
        )
        start_value = _raw_value(
            row,
            columns,
            "daily_start",
        )
        end_value = _raw_value(
            row,
            columns,
            "daily_end",
        )

        if not _is_missing(shift_value):
            parts = re.split(
                r"\s*[-—~至]\s*",
                str(shift_value).strip(),
                maxsplit=1,
            )

            if len(parts) == 2:
                start_value, end_value = parts

        daily_start, _ = _parse_clock(
            start_value
        )
        daily_end, daily_end_next_day = (
            _parse_clock(end_value)
        )

        if daily_start is None or daily_end is None:
            parsed.unresolved_issues.append(
                DataIssue(
                    code="invalid_working_calendar",
                    message=f"{source} 的工作时间无法解析。",
                    source=source,
                    field="working_calendar",
                )
            )

        parsed.machines.append(
            ParsedMachine(
                source=source,
                id=_parse_identifier(
                    _raw_value(row, columns, "machine_id"),
                    "machine id",
                    source,
                    parsed,
                ),
                supported_products=products,
                rates=rates,
                daily_start=daily_start,
                daily_end=daily_end,
                daily_end_next_day=daily_end_next_day,
            )
        )


def _parse_maintenance(
    input_file: InputFile,
    sheet: SheetPreview,
    records: list[dict],
    parsed: ParsedSchedulingData,
):
    columns = _column_map(sheet.columns)

    for index, row in enumerate(records):
        source = _source_label(
            input_file,
            sheet,
            index,
        )
        note = _raw_value(
            row,
            columns,
            "note",
        )

        parsed.maintenance.append(
            ParsedMaintenance(
                source=source,
                machine_id=_parse_identifier(
                    _raw_value(row, columns, "machine_id"),
                    "maintenance machine id",
                    source,
                    parsed,
                ),
                start_time=_parse_datetime(
                    _raw_value(row, columns, "start_time"),
                    "maintenance start_time",
                    source,
                    parsed,
                ),
                end_time=_parse_datetime(
                    _raw_value(row, columns, "end_time"),
                    "maintenance end_time",
                    source,
                    parsed,
                ),
                note=(
                    str(note)
                    if not _is_missing(note)
                    else None
                ),
            )
        )


def _canonical_entity_id(value: str) -> str:
    return re.sub(
        r"[^0-9a-z]",
        "",
        value.casefold(),
    )


def _detect_machine_mappings(
    parsed: ParsedSchedulingData,
):
    machine_ids = [
        machine.id
        for machine in parsed.machines
        if machine.id is not None
    ]
    exact_ids = set(machine_ids)
    canonical = {}

    for machine_id in machine_ids:
        canonical.setdefault(
            _canonical_entity_id(machine_id),
            [],
        ).append(machine_id)

    for maintenance in parsed.maintenance:
        reference = maintenance.machine_id

        if reference is None or reference in exact_ids:
            continue

        candidates = canonical.get(
            _canonical_entity_id(reference),
            [],
        )

        if len(candidates) == 1:
            proposed = candidates[0]
            parsed.inferred_mappings.append(
                InferredMapping(
                    field="maintenance.machine_id",
                    source_value=reference,
                    proposed_value=proposed,
                    reason="去除分隔符后标识一致，但尚未自动合并。",
                    source=maintenance.source,
                )
            )
            message = (
                f"{maintenance.source}: {reference} 可能对应 {proposed}，"
                "目前未自动合并。"
            )
        else:
            message = (
                f"{maintenance.source}: 未找到设备 {reference}。"
            )

        parsed.unresolved_issues.append(
            DataIssue(
                code="unknown_machine_reference",
                message=message,
                source=maintenance.source,
                field="maintenance.machine_id",
            )
        )
