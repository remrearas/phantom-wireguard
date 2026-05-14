# ADR-0001 — Architectural Decision Records

## Status

Accepted — 2026-04-20

## Context

The Phantom-WG Mac application is not an ordinary VPN client; it's a product matured on top of the Retro-era legacy, with discrete building blocks such as Ghost Mode (wstunnel + WireGuard), Split-Tunneling, Reset Connection, and Session-Scoped Logs layered on.

Behind each of these building blocks sits a concrete decision answering the question *why Y instead of X*.

Since I run the project as a solo developer, architectural decisions have accumulated in scattered form throughout this period — in my own mind, in notes kept on my device, and in long commit messages. This dispersal made my life easier during fast iteration, but it wasn't turning into persistent memory; it was evolving into tacit knowledge. I crystallized the critical decisions in the structure of the 1.2.0 release; when I applied the final polish to them with 1.2.1, I decided to bind them to a written, immutable record. It's fair to say that at this point the Phantom-WG Mac architecture has reached a maturity that can be documented retrospectively. This ADR directory is where the written record of architectural decisions lives; future decision changes are captured here as well.

## Decision

1. **Format — Nygard ADR.** Every document consists of four sections:
   
   - **Status**: `Proposed` / `Accepted` / `Superseded by ADR-XXXX` / `Deprecated`
   - **Context**: the rationale, constraints, and alternatives that led to the decision
   - **Decision**: what was concretely done
   - **Consequences**: what trade-offs this decision brought, what it led to
   
2. **Numbering — sequential, four digits.** `0001`, `0002`, … Numbers increment without gaps; even if an ADR is removed, its number is not reused.

3. **Language flow — TR draft → approval → EN translation.** ADRs are written in Turkish first, reviewed, and receive Production sign-off; the English translation is prepared afterwards. The two languages run in parallel, but the chronology is serial.

4. **Directory layout.** Documentation lives in the same repo as the codebase (`ARAS-Workspace/phantom-wg`), on the `app/mac` branch:
   ```
   Documentation/
   └── ADR/
       ├── Turkish/
       │   └── NNNN-title.md
       └── English/
           └── NNNN-title.md
   ```

5. **Immutability principle.** An accepted ADR is not modified for corrections. Only typo and language fixes are allowed. If the decision itself changes:
   - The old ADR's status is updated to `Superseded by ADR-XXXX`.
   - A new ADR is opened; the context section references the prior decision.

6. **The boundary of an ADR.** An ADR records a single decision — *"X was done, not Y, because Z"*. Written the moment the decision is taken, immutable afterwards. Only decisions that change the architecture go into an ADR; describing the current structure as a whole is not an ADR's job.

7. **Scope — Mac application only.** This directory (`Documentation/ADR/`) contains architectural decisions for the Mac client application alone.

## Consequences

- Each new architectural decision naturally fits the same format.
- The immutability rule forces clarity in the first draft.
- The TR/EN dual stream adds writing overhead but makes the documents readable without a language barrier.
- The history of past decisions (the supersession chain) remains traceable.
