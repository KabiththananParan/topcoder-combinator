from dataclasses import dataclass

from app.matrix.models import RequirementMatrix

from .provenance_ledger import ProvenanceLedgerBuilder


@dataclass(frozen=True)
class RegisteredEvidence:
    evidence_id: str
    submission_id: str
    requirement_id: str
    path: str
    start_line: int | None
    end_line: int | None
    symbol: str | None
    evidence_type: str


class EvidenceRegistrationService:
    """
    Registers matrix evidence with the provenance ledger.

    The provenance ledger is the canonical owner of stable
    evidence IDs. This service only connects matrix evidence
    to those IDs.
    """

    def register_matrix_evidence(
        self,
        matrix: RequirementMatrix,
        ledger_builder: ProvenanceLedgerBuilder,
    ) -> dict[tuple[str, str], list[str]]:
        evidence_refs: dict[tuple[str, str], list[str]] = {}

        for entry in matrix.entries:
            key = (
                entry.requirement_id,
                entry.submission_id,
            )

            refs: list[str] = []

            for evidence in entry.assessment.evidence:
                evidence_id = ledger_builder.add_evidence(
                    submission_id=entry.submission_id,
                    requirement_id=entry.requirement_id,
                    path=str(evidence.get("path", "")),
                    start_line=evidence.get("startLine"),
                    end_line=evidence.get("endLine"),
                    symbol=evidence.get("symbol"),
                    evidence_type=self._evidence_type(
                        evidence
                    ),
                    description=self._description(
                        evidence
                    ),
                )

                refs.append(evidence_id)

            evidence_refs[key] = refs

        return evidence_refs

    @staticmethod
    def _evidence_type(evidence: dict) -> str:
        path = str(evidence.get("path", "")).lower()

        filename = path.split("/")[-1]

        if (
            ".test." in filename
            or ".spec." in filename
            or "_test." in filename
            or filename.startswith("test_")
            or "/tests/" in f"/{path}/"
            or "/test/" in f"/{path}/"
            or "/__tests__/" in f"/{path}/"
        ):
            return "test"

        if (
            path.endswith(".md")
            or path.endswith(".rst")
            or path.endswith(".txt")
            or "/docs/" in f"/{path}/"
        ):
            return "documentation"

        return "source"

    @staticmethod
    def _description(evidence: dict) -> str:
        path = str(evidence.get("path", ""))

        start_line = evidence.get("startLine")
        end_line = evidence.get("endLine")
        symbol = evidence.get("symbol")

        location = path

        if start_line is not None:
            if end_line is not None:
                location += f":{start_line}-{end_line}"
            else:
                location += f":{start_line}"

        if symbol:
            location += f" ({symbol})"

        return f"Evidence located at {location}."