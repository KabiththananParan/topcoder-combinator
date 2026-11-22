from dataclasses import dataclass

from app.decisions.models import DecisionSet
from app.matrix.models import RequirementMatrix
from app.provenance.models import ProvenanceLedger
from app.recommendation.models import RecommendationSet


@dataclass(frozen=True)
class RecommendationPipelineResult:
    challenge_id: str
    matrix: RequirementMatrix
    recommendations: RecommendationSet
    decisions: DecisionSet
    provenance: ProvenanceLedger