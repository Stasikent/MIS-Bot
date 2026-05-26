from dataclasses import dataclass, field
from datetime import datetime
import uuid


@dataclass
class PatientTask:
    fio: str
    birth_date: str
    study_date: str = ""
    mode: str = "normal"
    status: str = "pending"
    note: str = ""
    source: str = "manual"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "fio": self.fio,
            "birth_date": self.birth_date,
            "study_date": self.study_date,
            "mode": self.mode,
            "status": self.status,
            "note": self.note,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PatientTask":
        return cls(
            id=data.get("id") or str(uuid.uuid4()),
            fio=data.get("fio", ""),
            birth_date=data.get("birth_date", ""),
            study_date=data.get("study_date", ""),
            mode=data.get("mode", "normal"),
            status=data.get("status", "pending"),
            note=data.get("note", ""),
            source=data.get("source", "manual"),
        )