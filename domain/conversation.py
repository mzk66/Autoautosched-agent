from collections import defaultdict, deque
from copy import deepcopy
from datetime import datetime
import json
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

from domain.input_bundle import InputBundle, InputFile
from domain.workflow_schema import ScenarioRecord


def _file_fingerprint(item: dict) -> str:
    content = {
        key: value
        for key, value in item.items()
        if key != "id"
    }

    return json.dumps(
        content,
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )


class ChatMessage(BaseModel):
    role: str
    content: str
    files: list[str] = Field(
        default_factory=list
    )
    created_at: datetime = Field(
        default_factory=datetime.now
    )


class Conversation(BaseModel):
    id: str = Field(
        default_factory=lambda: uuid4().hex
    )
    title: str = "新对话"
    title_is_custom: bool = False
    messages: list[ChatMessage] = Field(
        default_factory=list
    )
    file_contexts: list[InputFile] = Field(
        default_factory=list
    )
    input_bundles: list[InputBundle] = Field(
        default_factory=list
    )
    workflow_state: dict = Field(
        default_factory=dict
    )
    scenario_history: list[ScenarioRecord] = Field(
        default_factory=list
    )
    created_at: datetime = Field(
        default_factory=datetime.now
    )
    updated_at: datetime = Field(
        default_factory=datetime.now
    )

    @model_validator(mode="before")
    @classmethod
    def migrate_file_ids(cls, value):
        if not isinstance(value, dict):
            return value

        data = deepcopy(value)
        file_contexts = data.get(
            "file_contexts",
            [],
        ) or []
        available_ids = defaultdict(deque)

        for index, item in enumerate(file_contexts):
            if isinstance(item, InputFile):
                item = item.model_dump(
                    mode="json"
                )
                file_contexts[index] = item

            if not isinstance(item, dict):
                continue

            resource_id = item.setdefault(
                "id",
                uuid4().hex,
            )
            available_ids[
                _file_fingerprint(item)
            ].append(resource_id)

        data["file_contexts"] = file_contexts

        input_bundles = data.get(
            "input_bundles",
            [],
        ) or []

        for bundle_index, bundle in enumerate(input_bundles):
            if isinstance(bundle, InputBundle):
                bundle = bundle.model_dump(
                    mode="json"
                )
                input_bundles[bundle_index] = bundle

            if not isinstance(bundle, dict):
                continue

            files = bundle.get(
                "files",
                [],
            ) or []

            for file_index, item in enumerate(files):
                if isinstance(item, InputFile):
                    item = item.model_dump(
                        mode="json"
                    )
                    files[file_index] = item

                if not isinstance(item, dict):
                    continue

                fingerprint = _file_fingerprint(
                    item
                )
                candidates = available_ids[
                    fingerprint
                ]

                if "id" in item:
                    try:
                        candidates.remove(
                            item["id"]
                        )
                    except ValueError:
                        pass
                    continue

                item["id"] = (
                    candidates.popleft()
                    if candidates
                    else uuid4().hex
                )

            bundle["files"] = files

        data["input_bundles"] = input_bundles

        return data

    def touch(self):
        self.updated_at = datetime.now()

    def rename(self, title: str):
        normalized = " ".join(
            title.split()
        )

        if not normalized:
            raise ValueError(
                "对话名称不能为空。"
            )

        self.title = normalized
        self.title_is_custom = True
        self.touch()

    def add_input_bundle(
        self,
        bundle: InputBundle,
    ):
        self.input_bundles.append(bundle)
        self.file_contexts.extend(
            bundle.files
        )
        self.workflow_state = {}
        self.touch()

    def record_scenario(self, scenario: ScenarioRecord):
        self.scenario_history.append(scenario)
        self.touch()

    def remove_file(
        self,
        file_id: str,
    ) -> InputFile | None:
        removed = None

        for index, input_file in enumerate(
            self.file_contexts
        ):
            if input_file.id == file_id:
                removed = self.file_contexts.pop(
                    index
                )
                break

        if removed is None:
            return None

        for bundle in self.input_bundles:
            bundle.files = [
                input_file
                for input_file in bundle.files
                if input_file.id != file_id
            ]

        self.input_bundles = [
            bundle
            for bundle in self.input_bundles
            if bundle.text.strip() or bundle.files
        ]
        self.workflow_state = {}
        self.touch()

        return removed


def make_conversation_title(
    text: str,
    file_names: list[str],
    fallback_index: int,
) -> str:
    normalized = " ".join(
        text.split()
    )

    if normalized:
        return normalized[:24]

    if file_names:
        if len(file_names) == 1:
            return f"文件：{file_names[0][:18]}"

        return f"{len(file_names)} 个文件"

    return f"新对话 {fallback_index}"
