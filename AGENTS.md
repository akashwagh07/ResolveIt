# Standing Instructions for Agents

- Always read `docs/ARCHITECTURE.md` and `docs/STATUS.md` before changing code.
- Agents never write to the database directly; they output command blocks that the backend validates and executes.
- Severity, department mapping, SLA timing and state transitions are deterministic code, never LLM opinion.
- Every agent output is a pydantic-validated schema with a confidence score and reasons. Every state change writes an audit event.
- Use typed Python, small functions, and pytest tests for the state machine, rule engine and command validator.
- Never commit secrets. Use a single `llm.py` wrapper for all LLM calls.
- Keep changes scoped to what the current prompt asks for.
