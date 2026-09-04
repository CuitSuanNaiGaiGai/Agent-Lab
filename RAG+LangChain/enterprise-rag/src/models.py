from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Document:
    id: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.content = self.content.strip()

        if not self.content:
            raise ValueError("Document content cannot be empty.")