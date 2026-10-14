from domain.input_bundle import InputFile, SheetPreview
from domain.workflow_schema import DataIssue, ParsedRule, ParsedSchedulingData
from domain.parsing.common import _column_map, _is_missing, _raw_value, _source_label


def _parse_bool(value) -> bool | None:
    if _is_missing(value):
        return None

    normalized = str(value).strip().casefold()

    if normalized in {"true", "yes", "y", "1", "是"}:
        return True

    if normalized in {"false", "no", "n", "0", "否"}:
        return False

    return None


def _is_supported_rule(description: str) -> bool:
    normalized = description.casefold()

    return (
        "检修" in normalized
        and "不可" in normalized
    ) or (
        "vip" in normalized
        and "延期" in normalized
        and "3" in normalized
    )


def _parse_rules(
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
        description_value = _raw_value(
            row,
            columns,
            "description",
        )

        if _is_missing(description_value):
            parsed.unresolved_issues.append(
                DataIssue(
                    code="missing_rule_description",
                    message=f"{source} 缺少规则描述。",
                    source=source,
                    field="description",
                )
            )
            continue

        description = str(description_value).strip()
        rule_type_value = _raw_value(
            row,
            columns,
            "rule_type",
        )
        rule_type = (
            str(rule_type_value).strip()
            if not _is_missing(rule_type_value)
            else None
        )
        supported = _is_supported_rule(
            description
        )
        rule_id_value = _raw_value(
            row,
            columns,
            "rule_id",
        )
        rule = ParsedRule(
            source=source,
            id=(
                str(rule_id_value).strip()
                if not _is_missing(rule_id_value)
                else None
            ),
            rule_type=rule_type,
            description=description,
            hard=_parse_bool(
                _raw_value(row, columns, "hard")
            ),
            supported=supported,
        )

        if rule_type and "目标" in rule_type:
            parsed.objectives.append(rule)
        else:
            parsed.constraints.append(rule)

        if not supported:
            parsed.unresolved_issues.append(
                DataIssue(
                    code="unsupported_rule",
                    message=(
                        f"规则 {rule.id or description} 尚未映射到当前 Solver，"
                        "需要确认是否忽略或扩展模型。"
                    ),
                    source=source,
                    field="rule",
                )
            )
