# What this project is

This project is a simple gatekeeper for AI agents that use document search and answer generation.

It does not decide what the answer should be. It does not replace the document search or the model. Instead, it sits in front of those steps and decides whether a request should be allowed through, whether it should be stopped, and whether it can be reused from a cache.

In plain terms, it helps answer a basic question:

- Is this request from a valid agent?
- Is it noisy or low-quality?
- Has it been repeated too often?
- Is there a cached answer we can safely reuse?
- Does the answer actually match the source material?
- Is the agent still allowed to spend its budget?
- Should we keep a record of what happened?

# What it does for agents

The system is designed to reduce a few common failure modes in agent workflows:

- repeat spam or looped requests
- blocked or invalid identities
- low-quality prompts that waste compute
- repeated answers that do not reflect the source material
- agents spending more than they should
- weak traceability when something goes wrong

It works by checking each request in a fixed sequence before an answer is released.

1. Is the agent known and active?
2. Is the request meaningful enough to process?
3. Has the agent triggered too many requests in a short time?
4. Is there an exact cached answer already known?
5. Is there a retrieval cache for the same question and source set?
6. Does the agent still have budget available?
7. Did the model return an answer that matches the source material closely enough?
8. Was the request logged in a way that can be audited later?

If any of these checks fail, the request is held and the reason is recorded.

# The bottlenecks it is meant to solve

This project is focused on operational bottlenecks, not model quality.

The main problems it tries to reduce are:

- wasted inference on repeated questions
- runaway requests from a single agent
- garbage or vague prompts that still trigger full processing
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

# How this project is different

This project is intentionally simple and deterministic.

It does not rely on hidden model judgment to decide whether an answer is acceptable. It uses fixed checks, cached results, source matching, and an append-only audit trail. That makes it easier to understand, easier to test, and easier to reason about during small experiments or lab setups.

The key idea is to make agent calls more predictable and less wasteful before they reach a model or a document pipeline.

# What this project is not

This project does not:

- guarantee the model is safe
- guarantee the agent is trustworthy
- guarantee that the answer is correct
- manage credentials or secrets
- replace proper security controls
- act as a complete production control plane for a large system

It is a practical guardrail for a small, controlled deployment where the goal is to reduce waste, limit repetition, and provide basic traceability.

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
