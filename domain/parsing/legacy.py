from datetime import datetime
import pandas as pd
from domain.schema import Job, Machine, Maintenance, SchedulingProblem


def inspect_excel(file_path: str):
    excel = pd.ExcelFile(file_path)

    return {
        "sheets": excel.sheet_names,
        "orders": pd.read_excel(file_path, sheet_name="Orders")
        .to_dict(orient="records"),
        "machines": pd.read_excel(file_path, sheet_name="Machines")
        .to_dict(orient="records"),
        "maintenance": pd.read_excel(file_path, sheet_name="Maintenance")
        .to_dict(orient="records"),
    }


def parse_time(value: str):
    return datetime.strptime(value, "%H:%M").time()


def load_problem(file_path: str) -> SchedulingProblem:
    orders_df = pd.read_excel(file_path, sheet_name="Orders")
    machines_df = pd.read_excel(file_path, sheet_name="Machines")
    maintenance_df = pd.read_excel(file_path, sheet_name="Maintenance")
    jobs = []

    for _, row in orders_df.iterrows():
        jobs.append(
            Job(
                id=str(row["order_id"]),
                product=str(row["product"]),
                quantity=float(row["quantity"]),
                due_time=row["due_time"].to_pydatetime(),
                priority=(
                    str(row["priority"])
                    if not pd.isna(row["priority"])
                    else None
                ),
                customer_type=(
                    str(row["customer_type"])
                    if not pd.isna(row["customer_type"])
                    else None
                ),
            )
        )

    machines = []

    for _, row in machines_df.iterrows():
        supported_products = [
            product.strip()
            for product in str(
                row["supported_products"]
            ).split(",")
        ]
        rates = {}

        for product in ["A", "B", "C"]:
            column = f"rate_{product}"

            if column in row and not pd.isna(row[column]):
                rates[product] = float(row[column])

        machines.append(
            Machine(
                id=str(row["machine_id"]),
                supported_products=supported_products,
                rates=rates,
                daily_start=parse_time(
                    str(row["daily_start"])
                ),
                daily_end=parse_time(
                    str(row["daily_end"])
                ),
            )
        )

    maintenance = []

    for _, row in maintenance_df.iterrows():
        maintenance.append(
            Maintenance(
                machine_id=str(row["machine_id"]),
                start_time=row["start_time"].to_pydatetime(),
                end_time=row["end_time"].to_pydatetime(),
                note=(
                    str(row["note"])
                    if not pd.isna(row["note"])
                    else None
                ),
            )
        )

    return SchedulingProblem(
        jobs=jobs,
        machines=machines,
        maintenance=maintenance,
    )
