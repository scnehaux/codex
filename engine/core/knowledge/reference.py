from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from engine.core.metamodel import ArtifactIdentity, SourceReference


class ReferenceKind(str, Enum):
    LOCAL = "local"
    EXTERNAL = "external"
    OBSERVED = "observed"


@dataclass(frozen=True, slots=True)
class LocalRef:
    identity: ArtifactIdentity

    def __post_init__(self) -> None:
        if not isinstance(self.identity, ArtifactIdentity):
            raise TypeError("identity must be ArtifactIdentity")

    @property
    def kind(self) -> ReferenceKind:
        return ReferenceKind.LOCAL

    @property
    def key(self) -> str:
        return self.identity.canonical_key


@dataclass(frozen=True, slots=True)
class ExternalRef:
    uri: str
    authority: str
    provenance: SourceReference | None = None

    def __post_init__(self) -> None:
        uri = self.uri.strip()
        authority = self.authority.strip()
        if not uri:
            raise ValueError("uri must not be blank")
        if not authority:
            raise ValueError("authority must not be blank")
        if (
            self.provenance is not None
            and not isinstance(self.provenance, SourceReference)
        ):
            raise TypeError("provenance must be SourceReference or None")
        object.__setattr__(self, "uri", uri)
        object.__setattr__(self, "authority", authority)

    @property
    def kind(self) -> ReferenceKind:
        return ReferenceKind.EXTERNAL

    @property
    def key(self) -> str:
        return self.uri


@dataclass(frozen=True, slots=True)
class ObservedRef:
    source_key: str
    source_kind: str
    provenance: SourceReference

    def __post_init__(self) -> None:
        source_key = self.source_key.strip()
        source_kind = self.source_kind.strip()
        if not source_key:
            raise ValueError("source_key must not be blank")
        if not source_kind:
            raise ValueError("source_kind must not be blank")
        if not isinstance(self.provenance, SourceReference):
            raise TypeError("provenance must be SourceReference")
        object.__setattr__(self, "source_key", source_key)
        object.__setattr__(self, "source_kind", source_kind)

    @property
    def kind(self) -> ReferenceKind:
        return ReferenceKind.OBSERVED

    @property
    def key(self) -> str:
        return self.source_key


KnowledgeReference = LocalRef | ExternalRef | ObservedRef
