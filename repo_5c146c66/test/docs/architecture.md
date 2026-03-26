# Project Aegis: Architecture Overview

Project Aegis is a high-performance, cross-platform data encryption utility. It is designed to solve the problem of secure local file storage for developers who need to bridge high-level interfaces (Web/Python) with low-level performance (C/C++).

### System Flow
1. User interacts via the Python CLI (`main.py`) or the Web Dashboard (`dashboard.ts`).
2. High-level logic validates settings from `config/settings.json`.
3. Requests are passed to the `core/` engine via native bridges.
4. The C/C++ layer performs memory-safe encryption and writes the output.