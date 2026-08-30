from engine.control.validators.base import BaseValidator
import re


class GDCValidator(BaseValidator):
    doc_type_name: str = "GDC"

    def validate_type_specific(self) -> None:
        """
        Execute rules specific to Governance Documents (GDC).

        Enforces meta-governance constraints for guideline artifacts:
        - If the document is a guideline (e.g., *-guideline.md), it dynamically fetches
          required downstream subsections from `base.schema.json`.
        - It strictly enforces the presence and sequential order of these subsections
          nested under their respective parent headings to ensure structural consistency
          across all domain templates (SAD, PAD, etc.).

        <pre>Args:
            None

        Returns:
            None
        </pre>
        """
        # @flow-domain: StartGDC((Start GDC Validation)) --> CheckIsGuideline{"Is filename a guideline?"}
        if not self.doc_meta:
            return

        # Enforce Downstream Guideline Interface
        if self.filename.endswith("-guideline.md"):
            # @flow-domain: CheckIsGuideline -->|Yes| FetchReqSub["Fetch required downstream subsections"]
            # Read required downstream subsections directly from the yaml ruleset (SSOT)
            downstream_subsections = (
                self.global_rules.get("rules", {})
                .get("structure", {})
                .get("required_downstream_guideline_subsections", {})
            )

            if downstream_subsections:
                # @flow-domain: FetchReqSub --> LoopParent{"For each parent section"}
                for parent, sub_sections in downstream_subsections.items():
                    # @flow-domain: LoopParent --> FindParent["Regex search for parent heading"]
                    # Extract the block starting from the parent heading until the next heading of the same or higher level
                    parent_pattern = (
                        r"^#{2,4}\s+(?:[\d\.]+\s+)?" + re.escape(parent) + r"\b"
                    )
                    parent_match = re.search(
                        parent_pattern, self.content, re.IGNORECASE | re.MULTILINE
                    )

                    if not parent_match:
                        # @flow-domain: FindParent -->|Not Found| ErrParentMissing["Error: Parent section missing"]
                        self.add_error(
                            "missing_section",
                            f"Downstream Guideline is missing parent section '{parent}' for required subsections.",
                        )
                        continue

                    start_idx = parent_match.end()
                    # Find the level of the parent heading
                    level_match = re.match(r"^#+", parent_match.group(0).strip())
                    assert level_match is not None
                    level = len(level_match.group(0))

                    # Find the next heading of the same or higher level
                    next_heading_pattern = r"^#{1," + str(level) + r"}\s+"
                    next_match = re.search(
                        next_heading_pattern, self.content[start_idx:], re.MULTILINE
                    )

                    if next_match:
                        parent_text = self.content[
                            start_idx : start_idx + next_match.start()
                        ]
                    else:
                        parent_text = self.content[start_idx:]
                    last_match_idx = -1
                    last_section = None

                    # @flow-domain: FindParent -->|Found| LoopSub{"For each required subsection"}
                    for section_name in sub_sections:
                        # @flow-domain: LoopSub --> FindSub["Regex search for subsection"]
                        # Match standard headers (## to #####) OR bold pseudo-headers (**Section Name**)
                        pattern = (
                            r"^(?:#{2,5}\s+(?:[\d\.]+\s+)?|\*\*)"
                            + re.escape(section_name)
                            + r"\b"
                        )
                        match = re.search(
                            pattern, parent_text, re.IGNORECASE | re.MULTILINE
                        )
                        if not match:
                            # @flow-domain: FindSub -->|Not Found| ErrSubMissing["Error: Subsection missing"]
                            self.add_error(
                                "missing_section",
                                f"Downstream Guideline is missing mandatory subsection '{section_name}' under '{parent}'.",
                            )
                        else:
                            # @flow-domain: FindSub -->|Found| CheckOrder{"Is order correct?"}
                            if match.start() < last_match_idx:
                                self.add_error(
                                    "subsection_order_violation",
                                    f"Subsection '{section_name}' is out of order. It must appear after '{last_section}'.",
                                )
                            last_match_idx = match.start()
                            last_section = section_name
