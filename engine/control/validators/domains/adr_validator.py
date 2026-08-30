from engine.control.validators.base import BaseValidator
import datetime


class ADRValidator(BaseValidator):
    doc_type_name: str = "ADR"

    def validate_type_specific(self) -> None:
        """
        Execute rules specific to Architecture Decision Records (ADRs).

        Enforces lifecycle rules for architecture exceptions:
        - If the ADR type is 'exception' and status is 'accepted', it must have a valid `expiry_date`.
        - If the `expiry_date` is in the past, an `exception_expired` error is raised to force a review.

        <pre>Args:
            None

        Returns:
            None
        </pre>
        """
        # @flow-domain: StartADR((Start ADR Validation)) --> CheckADRType{"Is ADR type 'exception'?"}
        if not self.doc_meta:
            return

        adr_type = self.doc_meta.get("adr_type")
        if adr_type == "exception":
            # @flow-domain: CheckADRType -->|Yes| CheckExceptionInfo{"Has exception_info?"}
            exception_info = self.doc_meta.get("exception_info")
            if exception_info:
                # Expired Exception Check (only for active waivers)
                status = self.doc_meta.get("status")
                # @flow-domain: CheckExceptionInfo -->|Yes| CheckStatus{"Is status 'accepted'?"}
                if status == "accepted":
                    # @flow-domain: CheckStatus -->|Yes| CheckExpiry{"Is expiry_date past?"}
                    expiry_date = exception_info.get("expiry_date")
                    if (
                        isinstance(expiry_date, datetime.date)
                        and expiry_date < datetime.date.today()
                    ):
                        # @flow-domain: CheckExpiry -->|Yes| ErrExpired["Error: Exception expired"]
                        self.add_error(
                            "exception_expired",
                            f"Exception waiver has expired on {expiry_date}.",
                        )
