from dataclasses import dataclass
from json import dump, load
from typing import Any

from pydantic import JsonValue


@dataclass
class Database:
    filename: str

    def get(self) -> Any:
        with open(self.filename, "r", encoding="UTF-8") as file:
            return load(file)

    def set(self, data: JsonValue) -> None:
        with open(self.filename, "w", encoding="UTF-8") as file:
            dump(data, file, ensure_ascii=False, indent=2, sort_keys=True)
