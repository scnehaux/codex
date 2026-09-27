# Company Packs

Company packs are optional governed declarative extension layers consumed by the
single Scnehaux `FrameworkCompiler`. A pack is not discovered by directory scanning:
it becomes active only when explicitly listed in
`governance/framework/contracts/extensions.yaml`.

Composition order is deterministic:

```text
core framework -> framework profile -> declared company packs -> ExecutableFramework
```

Each pack must use this top-level contract:

```yaml
contract_version: 1
kind: scnehaux-company-pack
pack_id: example-company
pack_version: 1.0.0
profile:
  id: scnehaux-codex-default
  version: 2
compatibility:
  framework:
    minimum: 0.2.0
    maximum_exclusive: 1.0.0
  ontology:
    minimum: 1.0.0
    maximum_exclusive: 2.0.0
operations: []
```

Each operation has exactly `mode`, `target`, and `definition`. The current governed
policy permits only additive `artifact-type` and `relationship-type` operations.
`governed-restriction` and `compatibility-preserving-override` are modeled explicitly
but default-denied. `forbidden-core-semantic-override` always fails closed.

An additive artifact type must define its artifact identity/family, unique repository
directory, complete lifecycle, schema path, and validator binding. Company-specific
validator modules must live under the `company_packs.*` Python namespace. An additive
relationship must provide the complete relationship ontology entry and may reference
core or previously composed artifact types.

A pack may not replace a core artifact type or relationship, reuse an occupied
repository root, or introduce a conflicting relationship metadata field for the same
source type. All such conflicts fail compilation.

Compatibility is explicit and fail-closed. Every pack declares half-open framework
and ontology ranges; the current compiled versions must fall inside both ranges before
any operation is applied. Core compatibility metadata also requires explicit migration
paths and deprecation policy. Compatibility, migration, or removals are never inferred
from pack contents or Python implementation details.
