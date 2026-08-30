import re

from engine.control.validators.base import BaseValidator


_IMPLEMENTATION_TECHNOLOGIES = (
    "PostgreSQL",
    "MySQL",
    "MariaDB",
    "Oracle",
    "SQL Server",
    "MongoDB",
    "DynamoDB",
    "Cassandra",
    "Redis",
    "Memcached",
    "Kafka",
    "RabbitMQ",
    "NATS",
    "Pulsar",
    "Kubernetes",
    "Docker",
    "OpenShift",
    "ECS",
    "EKS",
    "AKS",
    "GKE",
    "Lambda",
    "EC2",
    "RDS",
    "S3",
    "Keycloak",
    "Zitadel",
    "Okta",
    "React",
    "Angular",
    "Vue",
    "Next.js",
    "NestJS",
    "Spring Boot",
    ".NET",
    "Go",
    "Java",
)

_TECH_PATTERN = "|".join(
    sorted(
        (re.escape(item) for item in _IMPLEMENTATION_TECHNOLOGIES),
        key=len,
        reverse=True,
    )
)

_PRESCRIPTIVE_IMPLEMENTATION_RE = re.compile(
    rf"""
    (?:
        \b(?:use|uses|using|adopt|adopts|adopting)\b
        |\bstandardize(?:s|d)?\s+on\b
        |\bdeploy(?:s|ed|ing)?\s+(?:on|to)\b
        |\brun(?:s|ning)?\s+on\b
        |\bhost(?:s|ed|ing)?\s+on\b
        |\bbacked\s+by\b
        |\bpowered\s+by\b
        |\bimplemented\s+(?:in|with)\b
    )
    [^.!?\n]{{0,80}}
    \b(?:{_TECH_PATTERN})\b
    """,
    re.I | re.X,
)

_LABELED_IMPLEMENTATION_RE = re.compile(
    rf"""
    \b(?:database|datastore|cache|broker|queue|runtime|orchestrator|
        framework|language|identity\s+provider|cloud\s+provider)
    \s*[:=]\s*
    (?:{_TECH_PATTERN})\b
    """,
    re.I | re.X,
)

_NEGATING_CONTEXT_RE = re.compile(
    r"\b(?:not|never|avoid|avoids|avoiding|example|examples|e\.g\.)\s+$",
    re.I,
)

_FENCED_CODE_RE = re.compile(r"```.*?```|~~~.*?~~~", re.S)


class EADValidator(BaseValidator):
    doc_type_name: str = "EAD"

    def validate_type_specific(self) -> None:
        """Enforce the GDC-006 implementation-agnostic EAD boundary."""
        if not self.doc_meta:
            return

        ead_id = str(self.doc_meta.get("id", "")).strip().upper()

        # GDC-006 explicitly permits EAD-005 to define enterprise technology
        # portfolio and execution runtimes.
        if ead_id == "EAD-005":
            return

        technologies = self.doc_meta.get("technologies")
        if technologies:
            self.add_error(
                "structural_integrity_violation",
                "EADs other than EAD-005 must remain implementation-agnostic and "
                "must not declare concrete technologies in metadata.",
            )

        prose = _FENCED_CODE_RE.sub("", self.content)

        for pattern in (
            _PRESCRIPTIVE_IMPLEMENTATION_RE,
            _LABELED_IMPLEMENTATION_RE,
        ):
            for match in pattern.finditer(prose):
                prefix = prose[max(0, match.start() - 24) : match.start()]
                if _NEGATING_CONTEXT_RE.search(prefix):
                    continue

                excerpt = " ".join(match.group(0).split())
                self.add_error(
                    "structural_integrity_violation",
                    "EAD implementation leakage detected. GDC-006 requires EADs "
                    "other than EAD-005 to stay conceptually agnostic; move concrete "
                    f"technology selection to STD/SAD. Detected: '{excerpt}'.",
                )
                return
