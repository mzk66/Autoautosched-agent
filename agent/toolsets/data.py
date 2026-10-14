from domain.input_bundle import InputFile
from domain.parser import inspect_input_files, parse_input_files
from domain.workflow_schema import FileInspection, ParsedSchedulingData


def inspect_files(
    input_files: list[InputFile],
) -> FileInspection:
    return inspect_input_files(
        input_files
    )


def parse_data(
    input_files: list[InputFile],
) -> ParsedSchedulingData:
    return parse_input_files(
        input_files
    )
