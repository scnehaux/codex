from engine.control.validators.base import BaseValidator


class STDValidator(BaseValidator):
    doc_type_name: str = "STD"

    def validate_type_specific(self) -> None:
        """
        Execute rules specific to Standard Documents (STD).

        Enforces lifecycle constraints for enterprise standards:
        - Checks the `status` field. If a standard is marked as 'hold' (meaning it is slated
          for retirement or deprecation), an `operational_stability_violation` is raised to
          warn implementers against adopting it for new work.

        <pre>Args:
            None

        Returns:
            None
        </pre>
        """
        # @flow-domain: StartSTD((Start STD Validation)) --> CheckStatus{"Is status 'hold'?"}
        if not self.doc_meta:
            return

        status = str(self.doc_meta.get("status", "")).lower()
        if status == "hold":
            # @flow-domain: CheckStatus -->|Yes| WarnHold["Warning: STD is on hold"]
            self.add_error(
                "operational_stability_violation",
                "STD document has status 'hold' (retirement phase). "
                "New implementations MUST NOT adopt this standard. "
                "Existing implementations must schedule migration.",
            )
        # @flow-domain: CheckStatus -->|No| OKStatus["Continue"]
