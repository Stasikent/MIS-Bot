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
- protected profiles and encrypted saved-list transfer;
- multi-monitor/RDP-aware physical Win32 clicks;
- first-time workplace setup, correction mode and an extended **Click Map**;
- automatic Click Map discovery from templates/protocols and required runtime anchors;
- runtime click recalibration and PNG template replacement;
- retry logic for slow MIS transitions;
- offline/USB and small delta-update tooling.

## Visit opening

For a new visit the bot confirms the date first and then detects the actual MIS branch: inpatient question, without-referral dialog, or a ready visit/reason field. Slow transitions are rechecked instead of failing immediately.

## X-ray route

The X-ray route uses the common service-list flow, opens the X-ray protocol from medical history, opens Templates → Select, applies the configured patient-specific template and fills only **Описание** and **Заключение**. There is no study-number or study-date field at this protocol stage.

## Click Map

`gui/click_map_technical_window.py` is the advanced diagnostics/configuration screen. It combines `config/templates.json`, protocol `template_key` values and required runtime anchors. A newly introduced required anchor can therefore be configured before its PNG has been created on a workstation.

## Multi-monitor support

Runtime clicks use the Windows virtual desktop and physical Win32 cursor/click APIs to avoid primary-monitor coordinate assumptions when MIS is on another monitor or inside RDP.

## Updates

`tools/update/` contains standalone USB → PC update logic, manifest-based comparison and delta-package creation/application utilities. Workstation configuration and locally calibrated templates are intended to survive program updates.

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
tools/update/ offline and delta update utilities
```

## Status

Active development. The August 2026 major synchronization brings the public repository toward the current multi-monitor/X-ray/workplace-calibration architecture.
