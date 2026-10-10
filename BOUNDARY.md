# KhetSathi — Build Boundary & Provenance

Environmental Hacks 2026 | Track 2: Heat and Water | Build Window: 8–11 Oct 2026

## 1. Provenance and Hackathon Boundary Statement

This document explicitly defines what was newly created during the hackathon versus prior conceptual ideas, in strict accordance with Section 3 of the Technical Requirements Document (TRD).

| Prior concept / reference | Newly built for Environmental Hacks 2026 |
|---|---|
| Solar irrigation concept, ET0, FAO-56 ideas, RL concept, voice/PWA concepts | AWS SAM backend infrastructure (`infrastructure/template.yaml`) |
| Earlier FastAPI/MQTT/PostgreSQL/TimescaleDB architecture | DynamoDB single-table data model and repository (`khetsathi` table) |
| Earlier sell/hold, mandi and post-harvest ideas | Daily scheduled decision workflow (EventBridge -> Lambda -> DynamoDB) |
| Previous conceptual safety ideas | Pure Python deterministic FAO-56 decision engine + 12 independent safety checks |
| Previous voice concept | Amazon Polly (`hi-IN`) -> S3 audio -> PWA voice playback path |
| Previous UI ideas | Modern mobile-first React + Vite PWA with offline caching and high contrast UI |
| Previous simulation concept | Reproducible historical weather replay simulation (Bihar/Odisha maize season) |
| Previous architecture diagrams | Production-grade AWS serverless implementation, CloudWatch alarms and test suites |

Prior documents are cited as research inspiration only. All executable code in this repository was written during the hackathon window.
