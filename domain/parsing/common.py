from datetime import datetime, time
import re
import pandas as pd
from domain.input_bundle import InputFile, SheetPreview
from domain.workflow_schema import DataIssue, InferredMapping, ParsedSchedulingData


def _header_key(value) -> str:
    return re.sub(
        r"\s+",
        "",
        str(value),
    ).casefold()


def _column_map(columns) -> dict[str, str]:
    normalized = {
        _header_key(column): str(column)
        for column in columns
    }
    result = {}

    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            key = _header_key(alias)

            if key in normalized:
                result[canonical] = normalized[key]
                break

    return result


def _is_missing(value) -> bool:
    if value is None:
        return True

    if isinstance(value, str):
        return not value.strip()

    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _record_value(value):
    if _is_missing(value):
        return None

    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()

    if hasattr(value, "item"):
        return value.item()

    return value


def _source_label(
    input_file: InputFile,
    sheet: SheetPreview,
    row_index: int,
) -> str:
    return (
        f"{input_file.name}/{sheet.name}/row {row_index + 2}"
    )


def _raw_value(
    row: dict,
    columns: dict[str, str],
    field: str,
):
    column = columns.get(field)
    return row.get(column) if column else None


def _parse_identifier(
    value,
    field: str,
    source: str,
    parsed: ParsedSchedulingData,
) -> str | None:
    if _is_missing(value):
        parsed.unresolved_issues.append(
            DataIssue(
                code="missing_identifier",
                message=f"{source} 缺少 {field}。",
                source=source,
                field=field,
            )
        )
        return None

    raw = str(value)
    stripped = raw.strip()

    if raw != stripped:
        parsed.inferred_mappings.append(
            InferredMapping(
                field=field,
                source_value=raw,
                proposed_value=stripped,
                reason="标识符包含首尾空白，需要用户确认后才能合并。",
                source=source,
            )
        )

    return raw


def _parse_number(
    value,
    field: str,
    source: str,
    parsed: ParsedSchedulingData,
) -> float | None:
    if _is_missing(value):
        parsed.unresolved_issues.append(
            DataIssue(
                code="missing_number",
                message=f"{source} 缺少 {field}。",
                source=source,
                field=field,
            )
        )
        return None

    if isinstance(value, (int, float)):
        return float(value)

    raw = str(value).strip()
    match = re.fullmatch(
        r"([+-]?\d+(?:\.\d+)?)\s*(件(?:/h)?|/h)?",
        raw,
        flags=re.IGNORECASE,
    )

    if not match:
        parsed.unresolved_issues.append(
            DataIssue(
                code="invalid_number",
                message=f"{source} 的 {field} 无法解析：{value}",
                source=source,
                field=field,
            )
        )
        return None

    number = float(match.group(1))

    if match.group(2):
        parsed.inferred_mappings.append(
            InferredMapping(
                field=field,
                source_value=raw,
                proposed_value=str(number),
                reason="识别到明确的件数或每小时产量单位。",
                applied=True,
                blocking=False,
                source=source,
            )
        )

    return number


def _parse_datetime(
    value,
    field: str,
    source: str,
    parsed: ParsedSchedulingData,
) -> datetime | None:
    if _is_missing(value):
        parsed.unresolved_issues.append(
            DataIssue(
                code="missing_datetime",
                message=f"{source} 缺少 {field}。",
                source=source,
                field=field,
            )
        )
        return None

    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()

    if isinstance(value, datetime):
        return value

    raw = str(value).strip()

    try:
        parsed_value = pd.to_datetime(
            raw,
            errors="raise",
        ).to_pydatetime()
    except (TypeError, ValueError):
        parsed.unresolved_issues.append(
            DataIssue(
                code="invalid_datetime",
                message=f"{source} 的 {field} 无法解析：{value}",
                source=source,
                field=field,
            )
        )
        return None

    canonical = parsed_value.strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    if raw != canonical:
        parsed.inferred_mappings.append(
            InferredMapping(
                field=field,
                source_value=raw,
                proposed_value=canonical,
                reason="日期格式已确定性转换为标准格式。",
                applied=True,
                blocking=False,
                source=source,
            )
        )

    return parsed_value


def _parse_enum(
    value,
    field: str,
    source: str,
    parsed: ParsedSchedulingData,
    mapping: dict[str, str],
) -> str | None:
    if _is_missing(value):
        parsed.unresolved_issues.append(
            DataIssue(
                code=f"missing_{field}",
                message=f"{source} 缺少 {field}。",
                source=source,
                field=field,
            )
        )
        return None

    raw = str(value).strip()
    mapped = mapping.get(raw.casefold())

    if mapped is None:
        parsed.unresolved_issues.append(
            DataIssue(
                code=f"unknown_{field}",
                message=f"{source} 的 {field} 编码无法确认：{value}",
                source=source,
                field=field,
            )
        )
        return None

    if raw != mapped:
        parsed.inferred_mappings.append(
            InferredMapping(
                field=field,
                source_value=raw,
                proposed_value=mapped,
                reason="使用项目内明确的枚举编码表。",
                applied=True,
                blocking=False,
                source=source,
            )
        )

    return mapped


def _parse_clock(value) -> tuple[time | None, bool]:
    if _is_missing(value):
        return None, False

    if isinstance(value, time):
        return value, False

    if isinstance(value, datetime):
        return value.time(), False

    raw = str(value).strip()

    if raw == "24:00":
        return time(0, 0), True

    try:
        return datetime.strptime(
            raw,
            "%H:%M",
        ).time(), False
    except ValueError:
        return None, False


def _split_products(value) -> list[str]:
    if _is_missing(value):
        return []

    return [
        item.strip()
        for item in re.split(
            r"[,/、]",
            str(value),
        )
        if item.strip()
    ]


def _rate_column(
    columns: list[str],
    product: str,
) -> str | None:
    candidates = {
        _header_key(f"rate_{product}"),
        _header_key(f"{product}速度"),
        _header_key(f"{product}速度(件/h)"),
    }

    for column in columns:
        if _header_key(column) in candidates:
            return column

    return None


COLUMN_ALIASES = {
    "order_id": {"order_id", "订单号", "订单编号"},
    "product": {"product", "产品"},
    "quantity": {"quantity", "数量"},
    "due_time": {"due_time", "交期"},
    "priority": {"priority", "优先级"},
    "customer_type": {"customer_type", "客户类型"},
    "machine_id": {"machine_id", "设备", "设备号"},
    "supported_products": {
        "supported_products",
        "可加工产品",
    },
    "daily_start": {"daily_start", "开工时间"},
    "daily_end": {"daily_end", "结束时间"},
    "shift": {"shift", "班次"},
    "start_time": {"start_time", "开始时间"},
    "end_time": {"end_time", "结束时间"},
    "note": {"note", "备注", "原因"},
    "rule_id": {"rule_id", "规则id"},
    "rule_type": {"rule_type", "规则类型"},
    "description": {"description", "规则描述"},
    "hard": {"hard", "是否硬约束"},
}
