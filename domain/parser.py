"""文件解析公共入口。实现按数据类型维护在 parsing 中。"""

from domain.parsing.files import parse_input_files
from domain.parsing.inspection import inspect_input_files
from domain.parsing.legacy import inspect_excel, load_problem, parse_time

__all__ = ["parse_input_files", "inspect_input_files", "inspect_excel", "load_problem", "parse_time"]


if __name__ == "__main__":
    problem = load_problem("data/autosched_demo.xlsx")
    print("Jobs:", len(problem.jobs))
    print("Machines:", len(problem.machines))
    print("Maintenance:", len(problem.maintenance))
