from engine.control.validators.base import BaseValidator


class TDDValidator(BaseValidator):
    doc_type_name: str = "TDD"

    def validate_type_specific(self) -> None:
        """
        Execute rules specific to Technical Design Documents (TDD).

        Enforces upward traceability:
        - Validates the mandatory `parent_sad` field, ensuring the technical design maps to a system architecture.
        - Checks that the referenced SAD actually exists in the repository registry.

        <pre>Args:
            None

        Returns:
            None
        </pre>
        """
        # @flow-domain: StartTDD((Start TDD Validation)) --> CheckParentSAD["Check 'parent_sad' metadata"]
        if not self.doc_meta:
            return

        # TDD must have parent_sad traceability
        parent_sad = self.doc_meta.get("parent_sad")
        # @flow-domain: CheckParentSAD --> IsParentSADMissing{"Missing or empty?"}
        if parent_sad is None or (
            isinstance(parent_sad, list) and len(parent_sad) == 0
        ):
            # @flow-domain: IsParentSADMissing -->|Yes| ErrSADMissing["Error: parent_sad required"]
            self.add_error(
                "traceability_violation",
                "TDD document is missing required traceability field: 'parent_sad'.",
            )
        else:
            # @flow-domain: IsParentSADMissing -->|No| LoopSAD{"For each SAD ID"}
            sad_ids = parent_sad if isinstance(parent_sad, list) else [parent_sad]
            for sad_id in sad_ids:
                # @flow-domain: LoopSAD --> CheckSADExist{"SAD exists?"}
                if sad_id not in self.all_doc_ids:
                    # @flow-domain: CheckSADExist -->|No| ErrSADNotFound["Error: SAD does not exist"]
                    self.add_error(
                        "traceability_violation",
                        f"TDD 'parent_sad' in metadata references SAD '{sad_id}' which does not exist in the repository.",
                    )
