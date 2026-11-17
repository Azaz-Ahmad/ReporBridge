# Architecture

Vite serves the React application and proxies its API traffic to FastAPI on loopback. React Router renders the five views. TanStack Query refreshes the persisted workspace after mutations, including blocked closure attempts. The frontend uses Tailwind, Radix Slot, and reusable interface components.

FastAPI authenticates each protected request and delegates to SQLAlchemy services. PostgreSQL is the default database. A file-backed SQLite mode supports native Windows development without Docker. Alembic creates the workflow schema.

The database records patients, immutable clinical evidence, life-stage events, pathways, rule versions, obligations, dependency edges, agent executions, coordination tasks, clinical approvals, closure evidence, and sequenced audit events. Obligation creation, review, and closure each run in transactions with their audit writes. PostgreSQL advisory transactions and SQLite write transactions serialize demo updates. Blocked closure decisions commit their audit event before returning HTTP 409.

A deterministic LangGraph state graph takes authorized same-patient source and completion observations, reconciles evidence, prepares an administrative proposal, and routes it to the review queue. Reviewer decisions use a separate authenticated API and are bound to the graph run and current evidence. Failed graph invocations persist an audit trace and no actionable proposal. Clinical rule evaluation runs outside the graph.

Future interoperability adapters can translate institution-specific profiles into the validated input boundary. Epic, Oracle Health, and Malaffi connectivity would require separate adapters, contracts, credentials, mapping validation, and authorization. Any mother–child link would connect distinct records through an independently authorized relationship.
