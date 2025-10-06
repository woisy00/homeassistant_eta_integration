# Copilot Instructions for homeassistant_eta_integration

## Project Overview
- This is a Home Assistant custom integration for ETA heating units, exposing ETA REST API sensor data as Home Assistant entities.
- The main logic is in `custom_components/eta/` (notably `api.py`, `sensor.py`, `config_flow.py`).
- The integration is installed via HACS and configured through the Home Assistant UI (not YAML).

## Architecture & Patterns
- **API Layer:** `api.py` handles communication with the ETA REST API and sensor description parsing (uses `xmltodict`).
- **Config Flow:** `config_flow.py` implements a multi-step Home Assistant config flow for device and sensor selection.
- **Sensor Entities:** `sensor.py` defines Home Assistant sensor entities, using async setup and a shared API instance per device.
- **Constants:** Shared constants are in `const.py`.
- **Manifest:** `manifest.json` defines integration metadata and dependencies.
- **No YAML config:** All configuration is via the UI/config flow.

## Developer Workflows
- **Setup:** Use the provided `scripts/setup` or follow the README for HACS installation.
- **Testing:**
  - Use `pytest` for all tests in `tests/`.
  - Example: `pytest tests/` (see `tests/README.md` for more commands).
  - Test dependencies are in `requirements_test.txt`.
- **Linting/Formatting:**
  - `flake8` and `isort` are configured in `setup.cfg`.
  - Use `scripts/lint` for linting.
- **Devcontainer:** `.devcontainer.json` provides a ready-to-use VS Code devcontainer (Python 3.13, Home Assistant, all tools preinstalled).

## Project Conventions
- **Sensor selection:** Sensors are selected by the user during config flow, not hardcoded.
- **Async/Await:** All I/O and Home Assistant API calls are async.
- **Entity IDs:** Use `generate_entity_id` and Home Assistant helpers for entity management.
- **No direct file I/O:** All device data comes from the ETA REST API.
- **Tests:** Follow the style in `tests/` (modeled after Home Assistant core integration tests).

## Integration Points
- **Home Assistant:** Uses Home Assistant's async APIs, config flows, and entity model.
- **ETA REST API:** All device data is fetched via HTTP from the ETA unit (API must be enabled on the device).
- **HACS:** Installation and updates are managed via HACS.

## Key Files & Directories
- `custom_components/eta/` — main integration code
- `tests/` — test suite and test resources
- `scripts/` — dev scripts (setup, lint, develop)
- `.devcontainer.json` — VS Code devcontainer config
- `setup.cfg` — lint/format config

## Examples
- To add a new sensor type, extend `SensorType` and update `api.py` and `sensor.py` accordingly.
- To run tests with coverage: `pytest --cov=custom_components.eta tests/`

---
For more, see `README.md` and `tests/README.md`. When in doubt, follow Home Assistant core integration patterns.
