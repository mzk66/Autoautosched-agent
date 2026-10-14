from domain.input_bundle import InputFile
from domain.workflow_schema import ParsedSchedulingData
from domain.parsing.inspection import _sheet_role, inspect_input_files, sheet_records
from domain.parsing.orders import _parse_orders
from domain.parsing.machines import _detect_machine_mappings, _parse_machines, _parse_maintenance
from domain.parsing.rules import _parse_rules


def parse_input_files(
    input_files: list[InputFile],
) -> ParsedSchedulingData:
    parsed = ParsedSchedulingData()
    inspection = inspect_input_files(
        input_files
    )
    parsed.source_facts.extend(
        inspection.source_facts
    )
    parsed.unresolved_issues.extend(
        inspection.issues
    )

    for input_file in input_files:
        for sheet in input_file.sheets:
            records = sheet_records(sheet)
            role = _sheet_role(sheet.columns)

            if role == "orders":
                _parse_orders(
                    input_file,
                    sheet,
                    records,
                    parsed,
                )
            elif role == "machines":
                _parse_machines(
                    input_file,
                    sheet,
                    records,
                    parsed,
                )
            elif role == "maintenance":
                _parse_maintenance(
                    input_file,
                    sheet,
                    records,
                    parsed,
                )
            elif role == "rules":
                _parse_rules(
                    input_file,
                    sheet,
                    records,
                    parsed,
                )

    _detect_machine_mappings(parsed)
    parsed.source_facts.extend(
        [
            f"识别到 {len(parsed.jobs)} 个订单",
            f"识别到 {len(parsed.machines)} 台设备",
            f"识别到 {len(parsed.maintenance)} 个检修窗口",
            f"识别到 {len(parsed.constraints)} 条约束",
            f"识别到 {len(parsed.objectives)} 个目标",
        ]
    )

    return parsed
