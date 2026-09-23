# Declarative Framework Contract

Slice 11.1 introduces the governed authored contract boundary for Scnehaux Codex.
The canonical entrypoint is `governance/framework/contract-set.yaml`; its family
files live under `governance/framework/contracts/`.

The contract set began as an **exact semantic mirror** in Slice 11.1. Slices 11.2
and 11.3 cut artifact/layout/lifecycle/binding and relationship semantics over to
immutable typed projections. Slice 11.4 now composes all governed families into one
`ExecutableFramework`; Python facades may execute behavior but cannot independently
author migrated semantics. Fragment views remain compatibility projections only.

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

**Status: selected and fully implemented through Slice 11.4.**

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

## REC-11-004 - Use a typed subset runtime view before the full compiler

**Status: selected and implemented in Slice 11.2.**

Project the artifact vocabulary, family identity, canonical roots, lifecycle,
schema bindings, and validator bindings into one immutable typed runtime view
directly from the governed contracts. Existing call sites may retain compatibility
facades, but those facades must delegate to the view and cannot author values.

This avoided prematurely introducing the full `ExecutableFramework` before
relationship semantics were declarative. The transitional subset projection was
subsumed by the Slice 11.4 compiler and remains only as a compatibility view; it
must stay small, deterministic, dependency-light, and contain no independent defaults.

JSON Schema remains a checked structural/configuration projection rather than the
source of artifact topology. Slice 11.3 extends the same principle to relationship
ontology: Python retains compatibility and behavioral execution only, not authored
relationship meaning. Revisit this decision if either typed subset starts acquiring
unrelated semantic families or behavior that belongs in `ExecutableFramework`; that
is a stop signal, not permission to grow another permanent runtime registry.

## REC-11-005 - Compile relationship ontology before the full framework compiler

**Status: selected and implemented in Slice 11.3.**

Compile the governed relationship family into one immutable typed ontology view
before the full `ExecutableFramework` exists. The compiler validates relation
identity, source/target vocabulary, cardinality, direction, DAG participation,
inverse consistency, authority requirements, and lifecycle/status constraints.

This kept semantic authority in declarative contracts while preserving existing
behavior functions and minimizing migration blast radius. The second transitional
typed projection was subsumed alongside the Slice 11.2 artifact view by the Slice
11.4 `ExecutableFramework`; both remain compatibility projections only.

A golden ontology semantic digest locks the pre-cutover meaning for this migration;
it is regression evidence, not an independent runtime authority. Revisit this
choice if relationship behavior needs semantics that cannot be represented by the
current contract family; that requires a separately governed ontology change rather
than hidden Python branching.

## REC-11-006 - Make ExecutableFramework the single runtime composition root

**Status: selected and implemented in Slice 11.4.**

Compile all governed framework families into one immutable `ExecutableFramework`
and make it the only runtime composition root. Artifact/layout/lifecycle/binding
and relationship subset views remain available only as compatibility projections;
production consumers obtain migrated semantics through the compiled framework.

The compiler also exposes governance/severity policy and extension declarations,
checks exact contract identity across fragment compilers, and assigns a normalized
semantic SHA-256 to the compiled state. Mapping order and semantically unordered
relationship/extension declaration order do not change that digest; semantic
changes do. The contract hash remains a separate identity for authored bytes/data.

This avoids multiple runtime authorities while preserving evolutionary migration
seams and testability. The trade-off is that Slice 11.5 still has to move remaining
non-structural runtime configuration out of JSON Schema; compiling a checked schema
projection here does not legitimize JSON Schema as long-term semantic authority.

## REC-11-007 - Separate structural schema from runtime policy and gate promotion

**Status: selected and implemented in Slice 11.5.**

Keep JSON Schema responsible only for JSON/document structural shape. Move repository
discovery policy, content policy, severity mappings, blocking severities and the
existing NFR taxonomy into the governed declarative governance-policy family compiled
by `ExecutableFramework`. Compatibility projections may feed existing validators but
must not make schema configuration authoritative again.

Introduce explicit immutable `SourceDocument`, `ParsedArtifact` and
`ArtifactCandidate` states. Deterministic validation produces a `ValidationReport`;
only a candidate bound to a PASS report can be promoted into `RepositoryModel`.
Invalid candidates remain available for diagnostics, and multi-candidate promotion
also rejects relationship-DAG violations.

This is intentionally not the final canonical repository trust boundary. Git
repository/revision/content-digest provenance is Slice 11.6 and
`ValidatedRepositorySnapshot` is Slice 11.7. Do not collapse those later trust
boundaries into this slice or imply that an unversioned promoted `RepositoryModel`
is canonical knowledge.

## Verification

`python scripts/framework_contract_check.py` validates the complete authored set,
full `FrameworkCompiler` composition, deterministic `ExecutableFramework` semantic
identity, and remaining checked schema/profile projections. The same assertion is
part of `scripts/governance_qualify.py`, so a green qualification cannot ignore
compiler, contract, or migration-boundary drift.
