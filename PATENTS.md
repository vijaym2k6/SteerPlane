# Patent Notice

SteerPlane's core technology is the subject of a **published Indian patent application**.

## Published Patent Application

| Field | Value |
|---|---|
| **Publication No.** | IN 202641071111 A1 |
| **Application No.** | 202641071111 |
| **Title** | System and Method for Runtime Monitoring and Controlled Execution of Autonomous AI Agents |
| **Status** | **Published / Patent Pending** — laid open 19 June 2026 (Journal No. 25/2026); examination pending, **not yet granted** |
| **Filed** | 08 June 2026 |
| **Applicant** | PES University, Bengaluru, Karnataka, India |
| **Inventors** | Vijay M; Sriraksha |
| **IPC** | G06N 20/00, G06N 5/04, G06N 5/02, G06F 21/55, G06N 3/04 |

> SteerPlane is **Patent Pending**. Please describe it as "patent pending" or "published patent application" — never "patented" or "granted" until a grant is issued.

## Patent-Pending Inventions

The published application covers the following systems and methods:

1. **System and Method for Runtime Loop Detection in Autonomous AI Agents**
   - Sliding-window pattern matching algorithm for detecting multi-pattern
     loops (single-action, alternating, and multi-step repeating sequences)
     in real-time across agent execution steps
   - Prompt-hash based gateway-level loop detection across API proxy calls
   - Automatic run termination upon loop confirmation

2. **AI Gateway Proxy with Integrated Policy Enforcement for LLM API Calls**
   - Transparent, protocol-compatible proxy layer that intercepts LLM API
     calls without requiring agent code modifications
   - Pre-request policy evaluation chain (deny → allow → rate limit → approval)
   - Real-time cumulative cost calculation and automatic budget enforcement
     with per-model token pricing across 25+ models

3. **Fault-Tolerant Runtime Control Plane for Autonomous AI Agents**
   - Graceful degradation architecture that maintains local safety enforcement
     when the central control plane is unreachable
   - Dual-mode enforcement (gateway proxy mode + SDK decorator mode)
   - Cross-framework integration architecture for automatic instrumentation
     of heterogeneous agent frameworks

## Open Source License

The source code of SteerPlane is made available under the terms of the
MIT License (see LICENSE file). This patent notice does not alter the
terms of the MIT License. Users of the open-source software are granted
the rights specified in the MIT License.

## Contact

For patent licensing inquiries, contact: steerplaneai@gmail.com
