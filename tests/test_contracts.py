import json
import unittest

from pydantic import ValidationError

from hermes_council.contracts import (
    Answer,
    ArtifactReference,
    Brief,
    Claim,
    ClaimBasis,
    CouncilResult,
    DebatePhase,
    DebateState,
    Disagreement,
    DocketQuestion,
    Evidence,
    FailureCase,
    Mandate,
    ModelUsage,
    Mode,
    Position,
    ResultStatus,
    Revision,
    Round,
    RunEvent,
    StateTransition,
    StopDecision,
    StopReason,
    Synthesis,
    TraceableStatement,
    Usage,
    Verification,
)


class CouncilContractsTest(unittest.TestCase):
    def brief(self, mode=Mode.QUICK):
        count = 3 if mode is Mode.QUICK else 5
        return Brief(
            question="Should we launch?",
            context="Customer feedback is mixed.",
            evidence=[Evidence(id="e1", claim="Demand exists", source="survey", excerpt="62% interested")],
            mode=mode,
            mandates=[Mandate(id=f"s{i}", focus=f"focus {i}") for i in range(1, count + 1)],
        )

    def positions(self, count):
        return [
            Position(
                seat_id=f"s{i}",
                claims=[Claim(id=f"c{i}", text=f"claim {i}", basis=ClaimBasis.EVIDENCE, evidence_ids=["e1"])],
                strongest_failure_case=FailureCase(text="Cost may rise", claim_ids=[f"c{i}"]),
            )
            for i in range(1, count + 1)
        ]

    def test_valid_quick_run_round_trips_through_json(self):
        state = DebateState(
            run_id="run-quick",
            brief=self.brief(),
            phase=DebatePhase.VERIFICATION,
            positions=self.positions(3),
            rounds=[
                Round(
                    number=1,
                    questions=[DocketQuestion(id="q1", text="What changes?", target_seat_id="s1", target_claim_id="c1")],
                    answers=[Answer(question_id="q1", seat_id="s1", text="Pricing changes", claim_ids=["c1"])],
                    revisions=[Revision(id="r1", seat_id="s1", question_id="q1", claim_id="c1", revised_text="qualified claim")],
                )
            ],
            stop=StopDecision(reason=StopReason.CONSENSUS, rounds_completed=1),
            synthesis=Synthesis(statements=[TraceableStatement(id="st1", text="Launch carefully", claim_ids=["c1"], question_ids=["q1"], evidence_ids=["e1"])]),
            verification=Verification(accepted=True),
            usage=Usage(calls=9, repairs=1, estimated_cost=0.12, model_usage=[ModelUsage(role="chair", calls=1, tokens=200, provider="host", model="model")]),
            events=[RunEvent(id="ev1", type="started", occurred_at="2026-07-20T00:00:00Z")],
        )
        restored = DebateState.model_validate_json(state.model_dump_json())
        self.assertEqual(state, restored)

    def test_standard_stable_disagreement_round_trips_through_json(self):
        state = DebateState(
            run_id="run-split",
            brief=self.brief(Mode.STANDARD),
            phase=DebatePhase.COMPLETED,
            positions=self.positions(5),
            rounds=[Round(number=1, questions=[DocketQuestion(id="q1", text="When should we launch?", target_seat_id="s1", target_claim_id="c1")])],
            stop=StopDecision(reason=StopReason.STABLE_DISAGREEMENT, rounds_completed=1, unresolved_question_ids=["q1"]),
            synthesis=Synthesis(
                statements=[TraceableStatement(id="st1", text="Demand is uncertain", claim_ids=["c1"], evidence_ids=["e1"])],
                disagreements=[Disagreement(id="d1", topic="Launch timing", side_a_claim_ids=["c1"], side_b_claim_ids=["c2"], stakes="Revenue", settling_evidence_needed=["A controlled launch cohort"] )],
            ),
            verification=Verification(accepted=True),
            usage=Usage(calls=12),
        )
        result = CouncilResult(
            run_id=state.run_id,
            state=state,
            status=ResultStatus.SPLIT,
            artifact=ArtifactReference(location="artifacts/run-split.json"),
            quorum=3,
            participating_seats=5,
        )
        restored = CouncilResult.model_validate_json(result.model_dump_json())
        self.assertEqual(result, restored)

    def test_invalid_ids_references_bounds_transitions_and_unknown_fields_are_rejected(self):
        with self.subTest("duplicate evidence"):
            with self.assertRaises(ValidationError):
                Brief(question="q", evidence=[Evidence(id="e", claim="c", source="s", excerpt="x"), Evidence(id="e", claim="c", source="s", excerpt="x")])
        with self.subTest("dangling evidence"):
            with self.assertRaises(ValidationError):
                DebateState(run_id="run", brief=self.brief(), positions=[Position(seat_id="s1", claims=[Claim(id="c1", text="c", basis=ClaimBasis.EVIDENCE, evidence_ids=["missing"])], strongest_failure_case=FailureCase(text="f"))])
        with self.subTest("empty evidence basis"):
            with self.assertRaises(ValidationError):
                Claim(id="c1", text="c", basis=ClaimBasis.EVIDENCE)
        with self.subTest("illegal mandate count"):
            with self.assertRaises(ValidationError):
                Brief(question="q", mode=Mode.QUICK, mandates=[Mandate(id="s1", focus="f")])
        with self.subTest("illegal call ceiling"):
            with self.assertRaises(ValidationError):
                DebateState(run_id="run", brief=self.brief(), usage=Usage(calls=10))
        with self.subTest("impossible transition"):
            with self.assertRaises(ValidationError):
                StateTransition(from_phase=DebatePhase.INITIALIZED, to_phase=DebatePhase.VERIFICATION)
        with self.subTest("transition from terminal"):
            with self.assertRaises(ValidationError):
                StateTransition(from_phase=DebatePhase.COMPLETED, to_phase=DebatePhase.DEBATE)
        with self.subTest("fictional persona"):
            with self.assertRaises(ValidationError):
                Mandate(id="s1", focus="f", persona="fictional biography")
        with self.subTest("provider routing"):
            with self.assertRaises(ValidationError):
                Brief(question="q", provider="caller-selected")
        with self.subTest("aggregate provider routing"):
            with self.assertRaises(ValidationError):
                Usage(calls=0, provider="caller-selected")

    def test_adversarial_protocol_constructions_are_rejected(self):
        positions = self.positions(3)
        with self.subTest("question target claim belongs to another seat"):
            with self.assertRaises(ValidationError):
                DebateState(run_id="run", brief=self.brief(), positions=positions, rounds=[Round(number=1, questions=[DocketQuestion(id="q1", text="q", target_seat_id="s1", target_claim_id="c2")])])
        with self.subTest("revision seat differs from question target"):
            with self.assertRaises(ValidationError):
                DebateState(run_id="run", brief=self.brief(), positions=positions, rounds=[Round(number=1, questions=[DocketQuestion(id="q1", text="q", target_seat_id="s1", target_claim_id="c1")], revisions=[Revision(id="r1", seat_id="s2", question_id="q1", claim_id="c2", revised_text="r")])])
        with self.subTest("revision claim belongs to another seat"):
            with self.assertRaises(ValidationError):
                DebateState(run_id="run", brief=self.brief(), positions=positions, rounds=[Round(number=1, questions=[DocketQuestion(id="q1", text="q", target_seat_id="s1", target_claim_id="c1")], revisions=[Revision(id="r1", seat_id="s1", question_id="q1", claim_id="c2", revised_text="r")])])
        with self.subTest("verification phase lacks synthesis"):
            with self.assertRaises(ValidationError):
                DebateState(run_id="run", brief=self.brief(), phase=DebatePhase.VERIFICATION, positions=positions, stop=StopDecision(reason=StopReason.CONSENSUS, rounds_completed=0))
        with self.subTest("synthesis phase lacks stop"):
            with self.assertRaises(ValidationError):
                DebateState(run_id="run", brief=self.brief(), phase=DebatePhase.SYNTHESIS, positions=positions)
        with self.subTest("completed phase lacks accepted verification"):
            with self.assertRaises(ValidationError):
                DebateState(run_id="run", brief=self.brief(), phase=DebatePhase.COMPLETED, positions=positions, stop=StopDecision(reason=StopReason.CONSENSUS, rounds_completed=0), synthesis=Synthesis(statements=[TraceableStatement(id="st1", text="supported", claim_ids=["c1"])]))
        with self.subTest("verification failed phase accepts verification"):
            with self.assertRaises(ValidationError):
                DebateState(run_id="run", brief=self.brief(), phase=DebatePhase.VERIFICATION_FAILED, positions=positions, stop=StopDecision(reason=StopReason.CONSENSUS, rounds_completed=0), synthesis=Synthesis(statements=[TraceableStatement(id="st1", text="supported", claim_ids=["c1"])]), verification=Verification(accepted=True))
        with self.subTest("rejected verification has no errors"):
            with self.assertRaises(ValidationError):
                Verification(accepted=False)
        with self.subTest("dangling unresolved question"):
            with self.assertRaises(ValidationError):
                DebateState(run_id="run", brief=self.brief(), positions=positions, stop=StopDecision(reason=StopReason.STABLE_DISAGREEMENT, rounds_completed=0, unresolved_question_ids=["missing"]))
        with self.subTest("untraced synthesis statement"):
            with self.assertRaises(ValidationError):
                Synthesis(statements=[TraceableStatement(id="st1", text="unsupported")])
        with self.subTest("completed state has failure stop reason"):
            with self.assertRaises(ValidationError):
                DebateState(run_id="run", brief=self.brief(), phase=DebatePhase.COMPLETED, positions=positions, stop=StopDecision(reason=StopReason.QUORUM_LOSS, rounds_completed=0), synthesis=Synthesis(statements=[TraceableStatement(id="st1", text="supported", claim_ids=["c1"])]), verification=Verification(accepted=True))
        with self.subTest("event data is not JSON serializable"):
            with self.assertRaises(ValidationError):
                RunEvent.model_validate({"id": "ev1", "type": "invalid", "occurred_at": "2026-07-20T00:00:00Z", "data": {"value": object()}})

    def test_quick_mode_can_complete_with_quorum(self):
        state = DebateState(
            run_id="run-quorum",
            brief=self.brief(),
            phase=DebatePhase.COMPLETED,
            positions=self.positions(2),
            stop=StopDecision(reason=StopReason.INSUFFICIENT_EVIDENCE, rounds_completed=0),
            synthesis=Synthesis(statements=[TraceableStatement(id="st1", text="More evidence is needed", claim_ids=["c1"])]),
            verification=Verification(accepted=True),
        )
        result = CouncilResult(
            run_id=state.run_id,
            state=state,
            status=ResultStatus.DEFER,
            quorum=2,
            participating_seats=2,
        )
        self.assertEqual(result.participating_seats, 2)

    def test_phase_schemas_are_plain_json_schema_dictionaries(self):
        for model in (Position, Round, Synthesis, Verification, CouncilResult):
            schema = model.model_json_schema()
            self.assertIsInstance(schema, dict)
            json.dumps(schema)


if __name__ == "__main__":
    unittest.main()
