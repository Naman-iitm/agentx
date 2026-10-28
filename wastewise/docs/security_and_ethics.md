# WasteWise Security, Privacy, and Responsible AI

## Data minimization
Store only operational data required for waste collection. Avoid collecting personal data from streets or camera feeds. If images are used, define retention, access, and deletion policies before deployment.

## Secrets
- Keep `.env` out of version control.
- Use `.env.example` with placeholders only.
- Never expose API keys in frontend variables except keys explicitly designed to be public and restricted by origin/quota.
- Do not return secrets from `/settings`.

## API security
- Validate all fields server-side.
- Apply authentication and role-based permissions before public or municipal deployment.
- Rate-limit ingestion and optimization endpoints.
- Enforce request size limits.
- Protect state-changing endpoints against unauthorized access.
- Record audit events for settings changes, alert state transitions, and manual overrides.

## AI and model limitations
- Mark forecasts as predictions and model classifications as probabilistic.
- Include method/model version and relevant warnings.
- Provide a human-review path for uncertain or hazardous categories.
- Do not use an LLM as a source for sensor facts, geographic facts, or numerical route optimization.
- Keep operator override and correction workflows available.
- Monitor forecast error and classification error over time.

## Environmental claims
Do not claim exact carbon reduction or fuel savings unless a baseline is defined and measurements support it. An estimated fuel comparison must state the vehicle consumption assumption and distance method.

## Demo transparency
The exhibition build must identify simulator data clearly. If a route uses straight-line distance rather than real road routing, show “approximate distance”. If a forecast is a rolling baseline, label it accordingly.
