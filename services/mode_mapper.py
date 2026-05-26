UI_MODE_TO_INTERNAL = {
    "Норма": "normal",
    "Кардиомегалия": "cardiomegaly",
    "2 Проекции": "two_projections",
    "Свой протокол": "manual_edit",
}

INTERNAL_TO_UI_MODE = {v: k for k, v in UI_MODE_TO_INTERNAL.items()}