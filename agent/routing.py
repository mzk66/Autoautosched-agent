import re


SOLVE_TERMS = (
    "排程",
    "排产",
    "求解",
    "开始优化",
    "生成生产计划",
    "确认并排程",
    "确认开始排程",
    "开始执行",
    "机器分配",
    "schedule",
)



INSPECT_TERMS = (
    "读一下",
    "读取",
    "检查数据",
    "分析数据",
    "看看数据",
    "识别数据",
    "缺什么",
)



FORBIDDEN_LLM_PATTERNS = (
    r"\bstart_time\b",
    r"\bend_time\b",
    r"\bduration_min\b",
    r"\btardiness_min\b",
    r"\bobjective_value\b",
    r"开始时间\s*[:：]",
    r"结束时间\s*[:：]",
    r"分配到.{0,8}(机器|设备)",
    r"Solver status\s*[:：]",
    r"\b(?:OPTIMAL|FEASIBLE|INFEASIBLE)\b",
)



def classify_scheduling_action(
    user_text: str,
    has_new_files: bool = False,
) -> str | None:
    """将用户输入路由到求解、检查或普通聊天。

    参数：
        user_text：用户本轮消息，按子串匹配而非整句解析。
        has_new_files：本轮是否上传了新文件；无求解关键词时，新文件触发检查。
    返回：
        "solve" 表示请求求解，"inspect" 表示检查数据，None 表示交给普通聊天。
        求解匹配优先，因此同时命中两类关键词或同时上传文件时仍返回 "solve"。
    """
    # casefold 比 lower 更适合不区分大小写的文本比较；中文关键词不受影响。
    normalized = user_text.casefold()

    if any(
        term.casefold() in normalized
        for term in SOLVE_TERMS
    ):
        return "solve"

    if (
        has_new_files
        or any(
            term.casefold() in normalized
            for term in INSPECT_TERMS
        )
    ):
        return "inspect"

    return None



def enforce_llm_boundary(text: str) -> str:
    """过滤普通聊天通道中疑似未经工具链验证的排程结果。

    命中任意规则时，用固定提示替换整条回复；未命中时原样返回。
    本函数仅检查传入文本，不读取工作流状态，也不验证数值或排程真实性。
    工具链生成的正式结果由 run_scheduling_workflow 控制发布。
    """
    # IGNORECASE 让英文状态名和字段名的匹配不受大小写影响。
    if any(
        re.search(pattern, text, re.IGNORECASE)
        for pattern in FORBIDDEN_LLM_PATTERNS
    ):
        return (
            "这条回复涉及排程结果，但本轮没有经过 "
            "SchedulingProblem 校验、Solver 和 Verifier，"
            "因此系统已阻止展示。请明确发送“帮我排程”以运行工具链。"
        )

    return text
