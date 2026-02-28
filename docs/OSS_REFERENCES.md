# OSS References Used (Design Patterns)

This project follows proven patterns from well-known open-source agent systems,
adapted for cold outreach.

## 1) LangGraph-style stateful flow pattern

Reference:
- https://github.com/langchain-ai/langgraph

Adopted pattern:
- Explicit step-based flow for draft generation (prepare lead -> research -> template route -> draft -> rewrite -> fallback).
- Human-in-the-loop remains first-class via approval UI before sending.

## 2) CrewAI-style role separation

Reference:
- https://github.com/crewAIInc/crewAI

Adopted pattern:
- Distinct role agents:
  - lead intelligence
  - research
  - copywriter
  - rewrite
- Orchestrator coordinates role handoffs.

## 3) AutoGen-style tool + orchestration layering

Reference:
- https://github.com/microsoft/autogen

Adopted pattern:
- Agent/tool composition where research and rewrite are optional tools in a deterministic pipeline.
- Fallback behavior when tool/model step is unavailable.

## 4) LiteLLM-style provider/model fallback thinking

Reference:
- https://github.com/BerriAI/litellm

Adopted pattern:
- OpenAI-compatible LLM router abstraction with model list fallback.
- Graceful degradation: if LLM fails, deterministic template output is kept.

## 5) OpenAI Cookbook-style structured output practice

Reference:
- https://github.com/openai/openai-cookbook

Adopted pattern:
- Rewrite step requests strict JSON and enforces validation gates before acceptance.
