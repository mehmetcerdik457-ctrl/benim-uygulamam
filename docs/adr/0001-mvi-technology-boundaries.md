# ADR 0001: MVI technology boundaries

- Status: proposed
- Date: 2026-10-11

## Context

The repository currently contains a standard-library HTTP backend that can
send chat input to an external OpenAI service. PROJECT OMEGA requires a
local-first control plane and cannot assume that the task runner's hardware,
credentials, accounts, or services are available on the owner's machine.
Technology choices must not imply unverified capabilities.

## Decisions

- Use FastAPI for the proposed versioned MVI API and PostgreSQL for canonical
  task/provenance metadata, as explicitly requested by the MVI specification.
- Keep the model behind a provider-neutral adapter. Evaluate Ollama and
  llama.cpp on the target machine before selecting a runtime; do not make a
  cloud provider the default or claim local inference until verified.
- Keep Docker Compose as the proposed local development orchestration
  mechanism, not as a production security boundary.
- Defer vector database, graph store, secret-store product, authentication
  provider, and sandbox implementation until threat model, target environment,
  and benchmarks justify selection.
- Do not migrate or silently repurpose the existing OpenAI-backed endpoint as
  a local model adapter. Keep its cloud behavior explicit until a reviewed
  migration changes it.

## Alternatives considered

- **Keep the stdlib server for all new services:** minimizes dependencies but
  does not provide the requested FastAPI contract or a maintainable API
  foundation.
- **Choose Ollama or llama.cpp immediately:** either may fit, but target
  hardware and model quality are unknown; early selection risks claiming
  unsupported local inference.
- **Use a cloud LLM as fallback:** simplifies availability but conflicts with
  privacy-by-default. A cloud fallback requires explicit configuration,
  disclosure, policy checks, and user approval; disabled by default.
- **Select a vector/graph database now:** premature without data volume,
  retrieval benchmark, or operational constraints.

## Consequences

This is an architecture direction, not evidence that any listed component is
implemented or installed. Adding dependencies requires version review and
security advisory checks. The MVI remains incomplete until the core is built
and its acceptance tests pass. A later ADR must resolve deferred decisions
with deployment-specific evidence.
