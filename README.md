# MIS Bot

Desktop automation assistant for radiology workflows in a medical information system (MIS/МИС). The project combines OCR, visual template recognition and controlled mouse/keyboard automation.

> Active development branch. Workstation-specific coordinates, passwords and local profiles must not be committed.

## Major update since the first public snapshot

The repository was initially published on 24 June 2026. The current codebase now includes:

- separate fluorography and X-ray routes;
- X-ray launch from a new visit or an already opened patient card;
- clipboard parsing into separate **Описание** and **Заключение** fields;
- protocol/template mapping for X-ray examinations;
- template-owner filtering and patient-specific template selection;
- inpatient visit handling;
- protected profiles and saved-list transfer;
- multi-monitor/RDP-aware physical Win32 clicks;
- first-time workplace setup, correction mode and an extended **Click Map**;
- automatic Click Map discovery from templates/protocols and required runtime anchors;
- runtime click recalibration and PNG template replacement;
- retry logic for slow MIS transitions;
- offline/USB and small delta-update tooling.

## First start / workstation configuration

Real `config/settings.json` and `config/coordinates.json` are intentionally not stored in Git. On a clean checkout the runtime creates them from `settings.example.json` and `coordinates.example.json` when needed. Replace the placeholder MIS/RIS values in `settings.json`, then run **Первоначальная настройка рабочего места** before using automation.

The initial setup now includes the common visit anchors, `Активное посещение`, optional inpatient dialogs, fluorography/X-ray history items, diagnosis closing controls and the X-ray `Описание` / `Заключение` fields. Fine correction and patient-specific protocol row templates can be handled through the Click Map.

## Visit opening

For a new visit the bot confirms the date first and then detects the actual MIS branch: inpatient question, without-referral dialog, or a ready visit/reason field. Slow transitions are rechecked instead of failing immediately.

## X-ray route

The X-ray route uses the common `work_plus` → `service_price_zero` service-list flow, opens **Рентгенографическое исследование** from medical history, opens **Шаблоны → Выбрать**, applies the configured patient-specific template and fills only **Описание** and **Заключение**. There is no study-number or study-date field at this protocol stage.

## Click Map

`gui/click_map_technical_window.py` is the advanced diagnostics/configuration screen. It combines `config/templates.json`, protocol `template_key` values and required runtime anchors. A newly introduced required anchor can therefore be configured before its PNG has been created on a workstation.

Both runtime clicks and Click Map test clicks use physical Win32 coordinates across the Windows virtual desktop, so a MIS window can be on a second monitor, including a differently oriented display.

## Updates

- `smart_update_standalone.py` applies an update from a prepared folder/USB drive while preserving workstation configuration and locally calibrated templates.
- `make_update_package.py` creates a small changed-files update package instead of redistributing the whole application.

## Repository safety

Do not commit real `config/settings.json`, internal MIS/RIS addresses, signing passwords, workstation coordinates, user list profiles, saved patient lists/sessions, logs/screenshots/OCR captures or built EXE/dist folders.

## Structure

```text
config/       configuration schemas/defaults
gui/          desktop UI and workplace calibration
models/       task/domain models
ocr/          OCR and clipboard text parsing
project/      MIS/RIS automation flows
services/     reusable runtime services
```

## Status

Active development. The August 2026 major synchronization brings the public repository toward the current multi-monitor/X-ray/workplace-calibration architecture.
