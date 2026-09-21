# Declarative Framework Contract

Slice 11.1 introduces the governed authored contract boundary for Scnehaux Codex.
The canonical entrypoint is `governance/framework/contract-set.yaml`; its family
files live under `governance/framework/contracts/`.

The contract set is **staged as an exact semantic mirror**. Existing Python
registries still own runtime execution until Slices 11.2 and 11.3 migrate their
families. Slice 11.4 then compiles declarative inputs into `ExecutableFramework`.
A staged contract therefore cannot silently change runtime behavior.

## Contract families

| Family             | Authored responsibility                            |
| ------------------ | -------------------------------------------------- |
| identity           | framework identity and semantic version            |
| artifact-types     | artifact vocabulary                                |
| repository-layout  | canonical artifact directories                     |
| lifecycle          | lifecycle classes, validation profiles, age policy |
| relationships      | relationship ontology and authority constraints    |
| schema-bindings    | base and artifact schema references                |
| validator-bindings | artifact-to-validator capability bindings          |
| governance-policy  | governance/severity policy references              |
| extensions         | extension declarations and compatibility metadata  |

Each semantic ownership key belongs to exactly one family. The loader rejects
duplicate YAML keys, duplicate family paths, path traversal, symlinked contract
inputs, conflicting ownership, missing families, unknown top-level fields, and
unsupported versions.

## REC-11-001 - Mirror before semantic-authority cutover

**Status: selected and implemented in Slice 11.1.**

Create a lossless declarative mirror and continuously compare it with the current
runtime before removing Python-owned registries. This avoids a flag-day migration,
keeps rollback straightforward, and makes semantic drift observable.

Trade-off: during the migration window, ordinary semantic changes must update both
the authored mirror and the legacy runtime representation. That temporary cost is
intentional. The equivalence gate prevents either copy from drifting unnoticed.
The mirror is not yet runtime authority and must not be described as such.

Alternatives rejected:

- switching runtime authority to YAML in the same change that first defines it;
- leaving the mirror advisory without a fail-closed equivalence gate;
- allowing separate teams to evolve YAML and Python independently.

Acceptance: the current artifact, layout, lifecycle, relationship, schema,
validator, governance-reference, and extension semantics are represented without
loss and the repository fails qualification when they diverge.

## REC-11-002 - Strict deterministic contract loading

**Status: selected and implemented in Slice 11.1.**

Use one bounded loader for the contract set and reject ambiguous YAML or semantic
ownership before runtime compilation exists. The loaded representation is frozen
and has a deterministic canonical SHA-256 identity.

This follows the principle that ambiguity must be eliminated at the trust boundary,
not repaired downstream. Duplicate-key YAML is especially dangerous because common
parsers otherwise accept last-write-wins behavior.

The canonical hash identifies normalized contract data; it is not a signature,
approval, or Git provenance proof. Provenance-bound loading is a later Phase 11
slice and must not be inferred from this hash.

## REC-11-003 - Migrate authority family by family

**Status: selected migration plan; execution belongs to Slices 11.2-11.4.**

Cut over artifact/layout/lifecycle semantics in Slice 11.2, relationship ontology
in Slice 11.3, then introduce the deterministic compiler and immutable
`ExecutableFramework` in Slice 11.4. Delete or demote each legacy semantic registry
only when its declarative replacement is consumed by runtime and equivalence is
proven.

Do not create a second permanent registry, and do not move semantic authority into
JSON Schema. Schemas remain structural validation boundaries. Provider adapters,
generators, and validators consume compiled framework state only after the relevant
cutover slice.

Revisit this sequence only if evidence shows a family cannot be migrated without a
different dependency order. Such a change requires an explicit recorded decision,
not an ad-hoc import from one legacy registry into another.

## Verification

`python scripts/framework_contract_check.py` validates the complete authored set and
its exact equivalence to the current runtime representation. The same assertion is
part of `scripts/governance_qualify.py`, so a green qualification cannot ignore
contract drift.
