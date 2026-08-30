from engine.control.validators.base import BaseValidator


class SADValidator(BaseValidator):
    doc_type_name: str = "SAD"

    def validate_type_specific(self) -> None:
        """
        Execute rules specific to System Architecture Documents (SAD).

        Enforces upward traceability, bidirectional consistency, and activation state:
        - Validates the mandatory `parent_pad` field, ensuring the system maps to a recognized platform.
        - Checks that the referenced PAD exists in the repository.
        - Checks that the referenced PAD declares this SAD in its `fulfilled_by` array.
        - Prevents an active SAD (`draft` or `approved`) beneath a non-approved PAD.
        """
        if not self.doc_meta:
            return

        parent_pad = self.doc_meta.get("parent_pad")
        if parent_pad is None or (
            isinstance(parent_pad, list) and len(parent_pad) == 0
        ):
            self.add_error(
                "traceability_violation",
                "SAD document is missing required traceability field: 'parent_pad'.",
            )
            return

        pad_ids = parent_pad if isinstance(parent_pad, list) else [parent_pad]

        for pad_id in pad_ids:
            if pad_id not in self.all_doc_ids:
                self.add_error(
                    "traceability_violation",
                    f"SAD 'parent_pad' in metadata references PAD '{pad_id}' which does not exist in the repository.",
                )
                continue

            pad_meta = self.all_doc_metadata.get(pad_id)
            if not pad_meta:
                continue

            fulfilled_by = pad_meta.get("fulfilled_by")
            fulfilled_list = (
                fulfilled_by
                if isinstance(fulfilled_by, list)
                else ([fulfilled_by] if fulfilled_by else [])
            )
            self_id = self.doc_meta.get("id")

            if self_id not in fulfilled_list:
                self.add_error(
                    "traceability_violation",
                    f"SAD '{self_id}' references parent PAD '{pad_id}', but PAD '{pad_id}' does not list this SAD in its 'fulfilled_by'. Bidirectional traceability is broken.",
                )

            sad_status = str(self.doc_meta.get("status", "")).lower()
            pad_status = str(pad_meta.get("status", "")).lower()

            if sad_status in {"draft", "approved"} and pad_status != "approved":
                self.add_error(
                    "traceability_violation",
                    f"SAD '{self_id}' has status '{sad_status}' but parent PAD '{pad_id}' has status '{pad_status or 'unknown'}'. "
                    "A SAD may enter 'draft' or 'approved' only when its parent PAD is 'approved'. "
                    "Keep the SAD 'chartered' until the PAD is promoted.",
                )
