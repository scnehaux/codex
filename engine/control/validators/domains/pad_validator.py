from engine.control.validators.base import BaseValidator


class PADValidator(BaseValidator):
    doc_type_name: str = "PAD"

    def validate_type_specific(self) -> None:
        """
        Execute rules specific to Platform Architecture Documents (PAD).

        Enforces bidirectional traceability and capability realization:
        - Downward traceability: Validates the `fulfilled_by` field. If populated, it must reference valid SAD IDs.
          Additionally checks that those SADs declare this PAD as their `parent_pad` (bidirectional link).
        - Upward traceability: Validates the `realizes_capability` field. It is strictly mandatory and must point
          to a valid EAD ID in the registry, ensuring the platform architecture maps back to business capabilities.

        <pre>Args:
            None

        Returns:
            None
        </pre>
        """
        # @flow-domain: StartPAD((Start PAD Validation)) --> CheckFulfilled["Check 'fulfilled_by' metadata"]
        if not self.doc_meta:
            return

        # fulfilled_by is expected to list SADs, but can be empty/missing if SADs are not yet built
        fulfilled_by = self.doc_meta.get("fulfilled_by")
        if fulfilled_by is not None:
            # @flow-domain: CheckFulfilled --> IsFulfilledEmpty{"Is list empty?"}
            if not isinstance(fulfilled_by, list) or len(fulfilled_by) == 0:
                # @flow-domain: IsFulfilledEmpty -->|Yes| WarnFulfilled["Warn: Consider linking SAD"]
                # Warning if fulfilled_by is empty, not a hard block
                self.add_error(
                    "cross_reference_missing",
                    "PAD 'fulfilled_by' is empty. Consider linking a SAD once implementation begins.",
                )
            else:
                # @flow-domain: IsFulfilledEmpty -->|No| LoopFulfilled{"For each SAD ID"}
                self_id = self.doc_meta.get("id")
                for sad_id in fulfilled_by:
                    # @flow-domain: LoopFulfilled --> CheckSADExist{"SAD exists?"}
                    if sad_id not in self.all_doc_ids:
                        # @flow-domain: CheckSADExist -->|No| ErrSADMissing["Error: SAD does not exist"]
                        self.add_error(
                            "traceability_violation",
                            f"PAD 'fulfilled_by' in metadata references SAD '{sad_id}' which does not exist in the repository.",
                        )
                    else:
                        # @flow-domain: CheckSADExist -->|Yes| CheckSADBidirectional{"SAD points to this PAD?"}
                        # Bidirectional check: ensure SAD points back to this PAD
                        sad_meta = self.all_doc_metadata.get(sad_id)
                        if sad_meta:
                            parent_pad = sad_meta.get("parent_pad")
                            parent_list = (
                                parent_pad
                                if isinstance(parent_pad, list)
                                else ([parent_pad] if parent_pad else [])
                            )
                            if self_id not in parent_list:
                                # @flow-domain: CheckSADBidirectional -->|No| ErrBidirBroken["Error: Bidirectional traceability broken"]
                                self.add_error(
                                    "traceability_violation",
                                    f"PAD '{self_id}' lists SAD '{sad_id}' in 'fulfilled_by', but SAD '{sad_id}' does not reference this PAD as its 'parent_pad'. Bidirectional traceability is broken.",
                                )

        # @flow-domain: CheckFulfilled --> CheckRealizes["Check 'realizes_capability' metadata"]
        realizes_capability = self.doc_meta.get("realizes_capability")
        # @flow-domain: CheckRealizes --> IsRealizesMissing{"Missing or Empty?"}
        if realizes_capability is None or (
            isinstance(realizes_capability, list) and len(realizes_capability) == 0
        ):
            # @flow-domain: IsRealizesMissing -->|Yes| ErrRealizesMissing["Error: Must trace to EAD"]
            self.add_error(
                "traceability_violation",
                "PAD document is missing required traceability field: 'realizes_capability'. "
                "Every PAD must trace upward to at least one EAD business capability.",
            )
        else:
            # @flow-domain: IsRealizesMissing -->|No| LoopRealizes{"For each EAD ID"}
            ead_ids = (
                realizes_capability
                if isinstance(realizes_capability, list)
                else [realizes_capability]
            )
            for ead_id in ead_ids:
                # @flow-domain: LoopRealizes --> CheckEADExist{"EAD exists?"}
                if ead_id not in self.all_doc_ids:
                    # @flow-domain: CheckEADExist -->|No| ErrEADMissing["Error: EAD does not exist"]
                    self.add_error(
                        "traceability_violation",
                        f"PAD 'realizes_capability' references EAD '{ead_id}' which does not exist in the repository.",
                    )
