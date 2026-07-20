"""Validated public data contracts for Hermes Council."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, JsonValue, StringConstraints, model_validator


NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Mode(str, Enum):
    QUICK = "quick"
    STANDARD = "standard"


class ClaimBasis(str, Enum):
    EVIDENCE = "evidence"
    INFERENCE = "inference"
    ASSUMPTION = "assumption"
    UNKNOWN = "unknown"


class ResultStatus(str, Enum):
    RECOMMEND = "recommend"
    DEFER = "defer"
    SPLIT = "split"
    FAILED = "failed"
    VERIFICATION_FAILED = "verification_failed"


class DebatePhase(str, Enum):
    INITIALIZED = "initialized"
    POSITIONS = "positions"
    DEBATE = "debate"
    SYNTHESIS = "synthesis"
    VERIFICATION = "verification"
    COMPLETED = "completed"
    FAILED = "failed"
    VERIFICATION_FAILED = "verification_failed"
    CANCELLED = "cancelled"


class Constraint(Contract):
    text: NonEmptyStr


class Evidence(Contract):
    id: NonEmptyStr
    claim: NonEmptyStr
    source: NonEmptyStr
    excerpt: NonEmptyStr


class Mandate(Contract):
    id: NonEmptyStr
    focus: NonEmptyStr


class Brief(Contract):
    question: NonEmptyStr
    context: str = ""
    constraints: list[Constraint] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    mode: Mode = Mode.STANDARD
    mandates: list[Mandate] | None = None
    retain_context: bool = False

    @model_validator(mode="after")
    def validate_ids_and_mandates(self) -> "Brief":
        _unique_ids(self.evidence, "evidence")
        if self.mandates is not None:
            _unique_ids(self.mandates, "mandate")
            if len(self.mandates) != _seat_count(self.mode):
                raise ValueError("explicit mandates must match the selected mode's seat count")
        return self


class Claim(Contract):
    id: NonEmptyStr
    text: NonEmptyStr
    basis: ClaimBasis
    evidence_ids: list[NonEmptyStr] = Field(default_factory=list)
    falsifiers: list[NonEmptyStr] = Field(default_factory=list)
    unknowns: list[NonEmptyStr] = Field(default_factory=list)
    conditions: list[NonEmptyStr] = Field(default_factory=list)

    @model_validator(mode="after")
    def evidence_basis_requires_evidence(self) -> "Claim":
        if self.basis is ClaimBasis.EVIDENCE and not self.evidence_ids:
            raise ValueError("evidence-based claim requires at least one evidence reference")
        return self


class FailureCase(Contract):
    text: NonEmptyStr
    claim_ids: list[NonEmptyStr] = Field(default_factory=list)


class Position(Contract):
    seat_id: NonEmptyStr
    claims: list[Claim] = Field(min_length=1)
    strongest_failure_case: FailureCase

    @model_validator(mode="after")
    def validate_claim_ids(self) -> "Position":
        _unique_ids(self.claims, "claim")
        return self


class DocketQuestion(Contract):
    id: NonEmptyStr
    text: NonEmptyStr
    target_seat_id: NonEmptyStr
    target_claim_id: NonEmptyStr


class Answer(Contract):
    question_id: NonEmptyStr
    seat_id: NonEmptyStr
    text: NonEmptyStr
    claim_ids: list[NonEmptyStr] = Field(default_factory=list)


class Revision(Contract):
    id: NonEmptyStr
    seat_id: NonEmptyStr
    question_id: NonEmptyStr
    claim_id: NonEmptyStr
    revised_text: NonEmptyStr


class Round(Contract):
    number: int = Field(ge=1)
    questions: list[DocketQuestion] = Field(default_factory=list)
    answers: list[Answer] = Field(default_factory=list)
    revisions: list[Revision] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_ids(self) -> "Round":
        _unique_ids(self.questions, "question")
        _unique_ids(self.revisions, "revision")
        return self


class StopReason(str, Enum):
    CONSENSUS = "consensus"
    STABLE_DISAGREEMENT = "stable_disagreement"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    QUORUM_LOSS = "quorum_loss"
    CALL_CEILING = "call_ceiling"
    CANCELLED = "cancelled"
    FAILED = "failed"


class StopDecision(Contract):
    reason: StopReason
    rounds_completed: int = Field(ge=0)
    unresolved_question_ids: list[NonEmptyStr] = Field(default_factory=list)


class TraceableStatement(Contract):
    id: NonEmptyStr
    text: NonEmptyStr
    claim_ids: list[NonEmptyStr] = Field(default_factory=list)
    question_ids: list[NonEmptyStr] = Field(default_factory=list)
    evidence_ids: list[NonEmptyStr] = Field(default_factory=list)

    @model_validator(mode="after")
    def requires_trace(self) -> "TraceableStatement":
        if not (self.claim_ids or self.question_ids or self.evidence_ids):
            raise ValueError("traceable statement requires at least one trace reference")
        return self


class Disagreement(Contract):
    id: NonEmptyStr
    topic: NonEmptyStr
    side_a_claim_ids: list[NonEmptyStr] = Field(min_length=1)
    side_b_claim_ids: list[NonEmptyStr] = Field(min_length=1)
    stakes: NonEmptyStr
    settling_evidence_needed: list[NonEmptyStr] = Field(min_length=1)


class Synthesis(Contract):
    statements: list[TraceableStatement] = Field(default_factory=list)
    agreement_statement_ids: list[NonEmptyStr] = Field(default_factory=list)
    disagreements: list[Disagreement] = Field(default_factory=list)
    unknowns: list[NonEmptyStr] = Field(default_factory=list)
    unsupported_assumptions: list[NonEmptyStr] = Field(default_factory=list)
    risks: list[NonEmptyStr] = Field(default_factory=list)
    dissent: list[NonEmptyStr] = Field(default_factory=list)
    smallest_reversible_next_action: NonEmptyStr | None = None

    @model_validator(mode="after")
    def validate_ids(self) -> "Synthesis":
        _unique_ids(self.statements, "synthesis statement")
        _unique_ids(self.disagreements, "disagreement")
        _require_known(self.agreement_statement_ids, {statement.id for statement in self.statements}, "agreement statement")
        return self


class Verification(Contract):
    accepted: bool
    errors: list[NonEmptyStr] = Field(default_factory=list)

    @model_validator(mode="after")
    def accepted_verification_has_no_errors(self) -> "Verification":
        if self.accepted and self.errors:
            raise ValueError("accepted verification cannot contain errors")
        if not self.accepted and not self.errors:
            raise ValueError("rejected verification requires at least one error")
        return self


class ModelUsage(Contract):
    role: NonEmptyStr
    calls: int = Field(ge=0)
    tokens: int = Field(ge=0)
    provider: NonEmptyStr | None = None
    model: NonEmptyStr | None = None


class Usage(Contract):
    calls: int = Field(ge=0)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    repairs: int = Field(default=0, ge=0)
    estimated_cost: float | None = Field(default=None, ge=0)
    model_usage: list[ModelUsage] = Field(default_factory=list)


class ArtifactReference(Contract):
    location: NonEmptyStr
    media_type: NonEmptyStr | None = None


class RunEvent(Contract):
    id: NonEmptyStr
    type: NonEmptyStr
    occurred_at: datetime
    data: dict[str, JsonValue] = Field(default_factory=dict)


class StateTransition(Contract):
    from_phase: DebatePhase
    to_phase: DebatePhase

    @model_validator(mode="after")
    def validate_transition(self) -> "StateTransition":
        legal = {
            DebatePhase.INITIALIZED: {DebatePhase.POSITIONS, DebatePhase.FAILED, DebatePhase.CANCELLED},
            DebatePhase.POSITIONS: {DebatePhase.DEBATE, DebatePhase.FAILED, DebatePhase.CANCELLED},
            DebatePhase.DEBATE: {DebatePhase.SYNTHESIS, DebatePhase.FAILED, DebatePhase.CANCELLED},
            DebatePhase.SYNTHESIS: {DebatePhase.VERIFICATION, DebatePhase.FAILED, DebatePhase.CANCELLED},
            DebatePhase.VERIFICATION: {
                DebatePhase.COMPLETED,
                DebatePhase.VERIFICATION_FAILED,
                DebatePhase.FAILED,
                DebatePhase.CANCELLED,
            },
        }
        if self.from_phase not in legal or self.to_phase not in legal[self.from_phase]:
            raise ValueError("illegal state transition")
        return self


class DebateState(Contract):
    run_id: NonEmptyStr
    brief: Brief
    phase: DebatePhase = DebatePhase.INITIALIZED
    positions: list[Position] = Field(default_factory=list)
    rounds: list[Round] = Field(default_factory=list)
    stop: StopDecision | None = None
    synthesis: Synthesis | None = None
    verification: Verification | None = None
    usage: Usage = Field(default_factory=lambda: Usage(calls=0))
    events: list[RunEvent] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_protocol(self) -> "DebateState":
        expected_seats = _seat_count(self.brief.mode)
        if len(self.positions) > expected_seats:
            raise ValueError("positions exceed the selected mode's seat count")
        quorum = 2 if self.brief.mode is Mode.QUICK else 3
        if self.phase in {
            DebatePhase.DEBATE,
            DebatePhase.SYNTHESIS,
            DebatePhase.VERIFICATION,
            DebatePhase.COMPLETED,
            DebatePhase.VERIFICATION_FAILED,
        } and len(self.positions) < quorum:
            raise ValueError("active debate phases require quorum")
        _unique_values([position.seat_id for position in self.positions], "seat")
        claims = [claim for position in self.positions for claim in position.claims]
        _unique_ids(claims, "claim")
        evidence_ids = {evidence.id for evidence in self.brief.evidence}
        claim_ids = {claim.id for claim in claims}
        seat_ids = {position.seat_id for position in self.positions}
        if self.brief.mandates is not None and seat_ids - {mandate.id for mandate in self.brief.mandates}:
            raise ValueError("position seat must have a mandate")
        for claim in claims:
            _require_known(claim.evidence_ids, evidence_ids, "claim evidence")
        for position in self.positions:
            _require_known(position.strongest_failure_case.claim_ids, claim_ids, "failure case claim")
        if len(self.rounds) > _round_limit(self.brief.mode):
            raise ValueError("rounds exceed the selected mode limit")
        if [round_.number for round_ in self.rounds] != list(range(1, len(self.rounds) + 1)):
            raise ValueError("round numbers must be consecutive starting at one")
        questions = [question for round_ in self.rounds for question in round_.questions]
        revisions = [revision for round_ in self.rounds for revision in round_.revisions]
        _unique_ids(questions, "question")
        _unique_ids(revisions, "revision")
        question_by_id = {question.id: question for question in questions}
        for question in questions:
            _require_known([question.target_seat_id], seat_ids, "question target seat")
            _require_known([question.target_claim_id], claim_ids, "question target claim")
            if question.target_claim_id not in _claims_for_seat(question.target_seat_id, self.positions):
                raise ValueError("question target claim must belong to the target seat")
        for round_ in self.rounds:
            for answer in round_.answers:
                question = question_by_id.get(answer.question_id)
                if question is None:
                    raise ValueError("answer references an unknown question")
                if answer.seat_id != question.target_seat_id:
                    raise ValueError("answer must come from the target seat")
                _require_known(answer.claim_ids, claim_ids, "answer claim")
            for revision in round_.revisions:
                question = question_by_id.get(revision.question_id)
                if question is None:
                    raise ValueError("revision references an unknown question")
                if revision.seat_id != question.target_seat_id:
                    raise ValueError("revision must belong to the question target seat")
                if revision.claim_id not in _claims_for_seat(revision.seat_id, self.positions):
                    raise ValueError("revision claim must belong to the revision seat")
        if self.stop is not None and self.stop.rounds_completed != len(self.rounds):
            raise ValueError("stop decision rounds must equal completed rounds")
        if self.stop is not None:
            _unique_values(self.stop.unresolved_question_ids, "unresolved question")
            _require_known(self.stop.unresolved_question_ids, question_by_id, "unresolved question")
        if self.usage.calls > _call_ceiling(self.brief.mode):
            raise ValueError("usage calls exceed the selected mode ceiling")
        _unique_ids(self.events, "event")
        if self.synthesis is not None:
            _validate_synthesis(self.synthesis, claim_ids, set(question_by_id), evidence_ids)
        if self.phase is DebatePhase.SYNTHESIS and self.stop is None:
            raise ValueError("synthesis phase requires a stop decision")
        if self.phase is DebatePhase.VERIFICATION and (self.stop is None or self.synthesis is None):
            raise ValueError("verification phase requires a stop decision and synthesis")
        if self.phase is DebatePhase.COMPLETED:
            if self.stop is None or self.synthesis is None or self.verification is None or not self.verification.accepted:
                raise ValueError("completed phase requires stop, synthesis, and accepted verification")
            if self.stop.reason in {StopReason.FAILED, StopReason.QUORUM_LOSS, StopReason.CANCELLED}:
                raise ValueError("completed phase cannot use a failure stop reason")
        if self.phase is DebatePhase.VERIFICATION_FAILED:
            if self.stop is None or self.synthesis is None or self.verification is None or self.verification.accepted:
                raise ValueError("verification_failed phase requires stop, synthesis, and rejected verification")
        return self


class CouncilResult(Contract):
    run_id: NonEmptyStr
    state: DebateState
    status: ResultStatus
    recommendation_statement_id: NonEmptyStr | None = None
    condition_statement_ids: list[NonEmptyStr] = Field(default_factory=list)
    artifact: ArtifactReference | None = None
    quorum: int = Field(ge=0)
    participating_seats: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_terminal_result(self) -> "CouncilResult":
        if self.run_id != self.state.run_id:
            raise ValueError("result run_id must match state run_id")
        expected_quorum = 2 if self.state.brief.mode is Mode.QUICK else 3
        if self.quorum != expected_quorum:
            raise ValueError("quorum must match the selected mode")
        if self.participating_seats > _seat_count(self.state.brief.mode):
            raise ValueError("participating seats exceed the selected mode's seat count")
        if self.participating_seats != len(self.state.positions):
            raise ValueError("participating seats must match the debate state")
        completed_statuses = {ResultStatus.RECOMMEND, ResultStatus.DEFER, ResultStatus.SPLIT}
        if self.status in completed_statuses:
            if self.state.phase is not DebatePhase.COMPLETED or self.participating_seats < self.quorum:
                raise ValueError("completed result requires completed accepted state and quorum")
        if self.status == ResultStatus.RECOMMEND and self.recommendation_statement_id is None:
            raise ValueError("recommend status requires a recommendation statement ID")
        if self.status == ResultStatus.RECOMMEND and self.state.stop is not None and self.state.stop.reason is not StopReason.CONSENSUS:
            raise ValueError("recommend status requires consensus stop reason")
        if self.status != ResultStatus.RECOMMEND and (self.recommendation_statement_id is not None or self.condition_statement_ids):
            raise ValueError("only recommend status may expose a recommendation or conditions")
        if self.recommendation_statement_id is not None or self.condition_statement_ids:
            if self.state.synthesis is None:
                raise ValueError("recommendation and conditions require synthesis support")
            statement_ids = {statement.id for statement in self.state.synthesis.statements}
            _require_known(
                [*self.condition_statement_ids, *([self.recommendation_statement_id] if self.recommendation_statement_id else [])],
                statement_ids,
                "result statement",
            )
        if self.status == ResultStatus.SPLIT and self.state.stop is not None and self.state.stop.reason is not StopReason.STABLE_DISAGREEMENT:
            raise ValueError("split status requires stable disagreement")
        if self.state.stop is not None and self.state.stop.reason is StopReason.STABLE_DISAGREEMENT and self.status is not ResultStatus.SPLIT:
            raise ValueError("stable disagreement requires split status")
        if self.state.stop is not None and self.state.stop.reason in {StopReason.FAILED, StopReason.QUORUM_LOSS, StopReason.CANCELLED} and self.status in completed_statuses:
            raise ValueError("terminal stop reason cannot produce a completed status")
        if self.status == ResultStatus.VERIFICATION_FAILED:
            if self.state.phase is not DebatePhase.VERIFICATION_FAILED:
                raise ValueError("verification_failed requires a verification_failed state")
        if self.status == ResultStatus.FAILED and self.state.phase not in {DebatePhase.FAILED, DebatePhase.CANCELLED}:
            raise ValueError("failed result requires failed or cancelled state")
        if self.status == ResultStatus.FAILED:
            if self.state.stop is None:
                raise ValueError("failed result requires a stop decision")
            expected_reasons = (
                {StopReason.CANCELLED}
                if self.state.phase is DebatePhase.CANCELLED
                else {StopReason.FAILED, StopReason.QUORUM_LOSS}
            )
            if self.state.stop.reason not in expected_reasons:
                raise ValueError("failed result stop reason must match the terminal state")
        return self


def _seat_count(mode: Mode) -> int:
    return 3 if mode is Mode.QUICK else 5


def _round_limit(mode: Mode) -> int:
    return 1 if mode is Mode.QUICK else 2


def _call_ceiling(mode: Mode) -> int:
    return 9 if mode is Mode.QUICK else 22


def _claims_for_seat(seat_id: str, positions: list[Position]) -> set[str]:
    for position in positions:
        if position.seat_id == seat_id:
            return {claim.id for claim in position.claims}
    return set()


def _unique_ids(items: list[Any], namespace: str) -> None:
    _unique_values([item.id for item in items], namespace)


def _unique_values(values: list[str], namespace: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"duplicate {namespace} ID")


def _require_known(references: list[str], known: set[str] | dict[str, Any], namespace: str) -> None:
    unknown = set(references) - set(known)
    if unknown:
        raise ValueError(f"unknown {namespace} reference: {sorted(unknown)[0]}")


def _validate_synthesis(
    synthesis: Synthesis, claim_ids: set[str], question_ids: set[str], evidence_ids: set[str]
) -> None:
    for statement in synthesis.statements:
        _require_known(statement.claim_ids, claim_ids, "synthesis claim")
        _require_known(statement.question_ids, question_ids, "synthesis question")
        _require_known(statement.evidence_ids, evidence_ids, "synthesis evidence")
    for disagreement in synthesis.disagreements:
        _require_known(disagreement.side_a_claim_ids, claim_ids, "disagreement claim")
        _require_known(disagreement.side_b_claim_ids, claim_ids, "disagreement claim")
