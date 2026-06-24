from dataclasses import dataclass, field
import uuid


@dataclass
class PatientTask:
    fio: str
    birth_date: str
    study_date: str = ""
    mode: str = "normal"
    status: str = "pending"
    source: str = "manual"
    note: str = ""

    # fluoro / xray
    task_type: str = "fluoro"

    # xray fields
    study_name: str = ""
    dose: str = ""
    description: str = ""
    conclusion: str = ""
    raw_text: str = ""

    # matched template fields
    template_key: str = ""
    template_name: str = ""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self):
        return {
            "id": self.id,
            "fio": self.fio,
            "birth_date": self.birth_date,
            "study_date": self.study_date,
            "mode": self.mode,
            "status": self.status,
            "source": self.source,
            "note": self.note,
            "task_type": self.task_type,
            "study_name": self.study_name,
            "dose": self.dose,
            "description": self.description,
            "conclusion": self.conclusion,
            "raw_text": self.raw_text,
            "template_key": self.template_key,
            "template_name": self.template_name,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            id=data.get("id") or str(uuid.uuid4()),
            fio=data.get("fio", ""),
            birth_date=data.get("birth_date", ""),
            study_date=data.get("study_date", ""),
            mode=data.get("mode", "normal"),
            status=data.get("status", "pending"),
            source=data.get("source", "manual"),
            note=data.get("note", ""),
            task_type=data.get("task_type", "fluoro"),
            study_name=data.get("study_name", ""),
            dose=data.get("dose", ""),
            description=data.get("description", ""),
            conclusion=data.get("conclusion", ""),
            raw_text=data.get("raw_text", ""),
            template_key=data.get("template_key", ""),
            template_name=data.get("template_name", ""),
        )