# How to Instantiate NICS

**Document Version:** 1.0.0
**Status:** Draft (Reference-Class)

## Purpose

This guide explains how to create a concrete NICS instance for a specific domain (agents, workflows, CI governance, etc.).

## Step 1: Define the Domain Inputs
- enumerate sensory channels (text, metrics, events)
- specify normalization and bounds
- map inputs to signal schemas

## Step 2: Configure Memory
- set capacity limits
- define decay + consolidation schedules
- choose retrieval semantics for the domain

## Step 3: Define Error Metrics
- perception error (input mismatch)
- memory error (context gap)
- policy error (governance rejection)
- propagation and global error aggregation

## Step 4: Configure Neuromodulators
- set bounded ranges
- set decay constants
- tie modulation to error signals only

## Step 5: Define Governance Computation
- specify inhibitory rules + constraints
- ensure governance dominance over action selection
- version and audit policy changes

## Step 6: Emit Decision Traces
- include inputs, state snapshot, error, modulation, governance, and action
- ensure deterministic serialization

## Example Instantiation

**NICS instance: CI Governance**
- Inputs: test failures, coverage deltas, latency spikes
- Errors: prediction error from expected quality gates
- Governance: block merges when inhibitor conditions match
- Actions: allow/deny merge + remediation suggestions

## Reference Implementation in MLSDM

- `src/mlsdm/engine/neuro_cognitive_engine.py`
- `src/mlsdm/observability/decision_trace.py`
