# What this project is

This project is a simple gatekeeper for AI agents that use document search and answer generation.

It does not decide what the answer should be. It does not replace the document search or the model. Instead, it sits in front of those steps and decides whether a request should be allowed through, whether it should be stopped, and whether it can be reused from a cache.

In plain terms, it helps answer a basic question:

- Is this request from a valid agent?
- Is it noisy or low-quality?
- Has it been repeated too often?
- Is there a cached answer we can safely reuse?
- Is the answer grounded in the source material?
- Is the agent still allowed to spend its budget?
- Should we keep a record of what happened?

# What it does for agents

The system is designed to reduce a few common bottlenecks in agent workflows:

- repeated spam or looped requests
- blocked or invalid identities
- low-quality prompts that waste compute
- repeated answers that do not reflect the source material
- agents spending more than they should
- weak traceability when something goes wrong

The exact checks are always run in the same order. A request is allowed to continue only if each check passes.

1. Is the agent known and active?
2. Is the request useful enough to process?
3. Has the agent triggered too many requests in a short time?
4. Is there an exact cached answer already known?
5. Is there a retrieval cache for the same question and source set?
6. Does the agent still have budget available?
7. Does the answer match the source material closely enough?
8. Was the request logged in a way that can be audited later?

If any check fails, the request is held and the reason is recorded.

# The bottlenecks it is meant to solve

This project is focused on operational bottlenecks, not model quality.

The main problems it tries to reduce are:

- wasted inference on repeated questions
- runaway requests from a single agent
- vague or low-quality prompts that still trigger full processing
- answers that sound plausible but do not reflect the actual source material
- hard-to-debug request chains without a record of what happened
- no clear spend control for agent activity

It is not trying to solve:

- model safety
- prompt injection protection
- secret handling
- user identity trust
- general AI alignment
- multi-tenant security isolation

Those are separate concerns and need different controls.

# How the project decides

This project is intentionally simple and deterministic.

It does not rely on hidden model judgment to decide whether an answer is acceptable. It uses fixed checks, cached results, source matching, and an append-only audit trail. The source match check is also deterministic: it compares the answer against the cited material using fixed rules such as lexical overlap, citation coverage, and a minimum threshold for agreement. In other words, there is no secret scoring model deciding pass or fail.

The key idea is to make agent calls more predictable and less wasteful before they reach a model or a document pipeline.

# Cache and audit behavior

The project keeps two main kinds of cache.

- Exact answer cache: a final answer for a request fingerprint. If the same question and same source material are seen again, the system can return the stored answer instead of running the full path again.
- Retrieval cache: stored document matches for the same question and source set. This reduces repeated lookups when the same content is being reviewed again.

The cache is only reused when the request still matches the same source set and the version of the adapter has not changed. If the inputs or version change, the system treats it as a miss and continues normally.

Every decision is also written to an audit trail. The system records the request fingerprint, agent ID, outcome, reason code, timestamp, and the cache key or source reference involved.

# What gets stored

For each request, the system keeps a small record of:

- request fingerprint
- agent ID
- decision outcome
- reason code
- timestamp
- cache key or source key

This is enough to explain why a request was allowed, held, or reused without needing a full operational logging system.

# Decision table

This is the fixed sequence in a short form:

```text
CHECK              PASS                       FAIL
identity           known + active            hold, log "invalid_identity"
usefulness         score >= T                hold, log "low_quality"
rate               under limit               hold, log "rate_exceeded"
exact cache        miss -> continue          hit -> return cached
retrieval cache    miss -> continue          hit -> return cached
budget             remaining > 0             hold, log "budget_exhausted"
source match       score >= T                hold, log "ungrounded"
audit              written                   always recorded
```

# What this project is not

This project does not:

- guarantee the model is safe
- guarantee the agent is trustworthy
- guarantee that the answer is correct
- manage credentials or secrets
- replace proper security controls
- act as a complete production control plane for a large system

It is a practical guardrail for a small, controlled deployment where the goal is to reduce waste, limit repetition, and provide basic traceability.

# When to use it and when not to use it

Use it when:

- you are running a single team or a small internal toolchain
- you want a simple lab or pilot setup
- you need a clear gate before agent requests hit a model or retrieval layer
- you want to reduce repeated work and make requests easier to explain

Do not rely on it as the main control for:

- large multi-tenant production systems
- strict compliance environments
- systems that need deep identity, security, or policy enforcement
- deployments where the answer quality itself must be judged by a separate governance process

# Example flow

A request comes in.

- the agent is checked
- the prompt is examined for usefulness
- the rate of requests is checked
- cached results are considered
- available budget is checked
- the answer is compared to the source material
- the decision is recorded

If the answer passes, it is released. If not, it is held.

# Limitations

This project is a baseline tool, not a full enterprise platform.

It is best for a single-node, small-lab, or controlled internal environment. It stores its state in a local SQLite database and is not designed to replace a larger operational system with heavy traffic, many teams, or strict compliance requirements.

In other words, it is useful for reducing obvious agent bottlenecks and making request behavior easier to understand, but it is not a complete production security or governance system on its own.

# License

MIT.
