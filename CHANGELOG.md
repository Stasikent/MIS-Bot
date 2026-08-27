# Changelog

## 2026-08 major synchronization

### X-ray workflow
- Dedicated X-ray route and open-card launch.
- Removed obsolete X-ray service-row dependency from the route.
- Templates → Select → owner filter → patient-specific template sequence.
- X-ray protocol fills Description and Conclusion only.
- Clipboard parser handles single-line and multiline MIS text.

### Visit opening
- Unified new-visit branching for fluorography and X-ray.
- Inpatient question is checked only after confirming the visit date.
- Inpatient Yes / optional diagnosis No branch.
- Delayed retry checks for slow MIS transitions.

### Workplace calibration
- First-time workplace setup and correction mode.
- Extended Click Map with template preview, test click, point recalibration and PNG replacement.
- Automatic protocol/runtime-anchor discovery.
- Active Visit goal anchor.

### Multi-monitor / RDP
- Windows virtual-desktop coordinate handling.
- Physical Win32 cursor movement and critical clicks.
- Runtime offsets reread from workstation configuration before actions.

### Lists and profiles
- Password-protected profile for exported task lists.
- Encrypted saved-list transfer between workstations.

### Updating
- Standalone USB-to-PC updater.
- Manifest comparison for faster flash updates.
- Delta update package builder and installer.
