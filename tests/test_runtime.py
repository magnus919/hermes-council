import asyncio
import unittest
from dataclasses import dataclass

from pydantic import BaseModel

from hermes_council import register
from hermes_council.runtime import StructuredCall, StructuredInferenceRunner


class Answer(BaseModel):
    value: str


@dataclass
class FakeUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    cost_usd: float | None = None


@dataclass
class FakeResult:
    parsed: object
    provider: str | None = None
    model: str | None = None
    usage: FakeUsage | None = None
    text: str = ""


class FakeLlm:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.cancelled = []

    async def acomplete_structured(self, **kwargs):
        self.calls.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        if isinstance(response, tuple):
            delay, response = response
            try:
                await asyncio.sleep(delay)
            except asyncio.CancelledError:
                self.cancelled.append(kwargs["task"])
                raise
        return response


class FakeContext:
    def __init__(self, llm=None):
        self.llm = llm
        self.registered = []

    def register_auxiliary_task(self, key, **kwargs):
        self.registered.append((key, kwargs))


def call(call_id, role="member"):
    return StructuredCall(
        id=call_id,
        role=role,
        task="hermes_council_member",
        purpose="council test",
        instructions="Return an answer.",
        text="test input",
        output_model=Answer,
    )


class StructuredInferenceRunnerTest(unittest.IsolatedAsyncioTestCase):
    async def test_out_of_order_completion_preserves_ids_and_reports_quorum(self):
        llm = FakeLlm(
            [
                (0.03, FakeResult({"value": "first"})),
                (0.01, FakeResult({"value": "second"})),
            ]
        )

        outcome = await StructuredInferenceRunner(FakeContext(llm)).run([call("a"), call("b")], quorum=2)

        self.assertEqual(list(outcome.accepted), ["a", "b"])
        self.assertEqual(outcome.accepted["a"].value, "first")
        self.assertEqual(outcome.accepted["b"].value, "second")
        self.assertTrue(outcome.quorum_met)

    async def test_malformed_output_repairs_once_then_records_typed_failure(self):
        llm = FakeLlm(
            [
                FakeResult(None, text="not json"),
                FakeResult({"value": "repaired"}),
                FakeResult(None),
                FakeResult(None),
            ]
        )

        outcome = await StructuredInferenceRunner(FakeContext(llm)).run([call("good"), call("bad")], quorum=1)

        self.assertEqual(outcome.accepted["good"].value, "repaired")
        self.assertEqual(len(outcome.failures), 1)
        self.assertEqual(outcome.failures[0].id, "bad")
        self.assertEqual(outcome.failures[0].role, "member")
        self.assertEqual(outcome.failures[0].attempts, 2)
        self.assertEqual(len(llm.calls), 4)
        self.assertTrue(llm.calls[0]["json_mode"])
        self.assertNotIn("json_schema", llm.calls[0])
        self.assertIn('"value"', llm.calls[0]["instructions"])
        self.assertIn("previous response was invalid", llm.calls[1]["instructions"].lower())
        self.assertIn("not json", llm.calls[1]["input"][0]["text"])

    async def test_provider_failure_counts_as_failed_attempt_and_loses_quorum(self):
        llm = FakeLlm([ValueError("provider unavailable")])

        outcome = await StructuredInferenceRunner(FakeContext(llm)).run([call("a")], quorum=1)

        self.assertFalse(outcome.quorum_met)
        self.assertEqual(outcome.usage.calls, 1)
        self.assertEqual(outcome.failures[0].attempts, 1)
        self.assertIn("provider unavailable", outcome.failures[0].error)
        self.assertEqual(len(llm.calls), 1)

    async def test_usage_aggregates_attempts_repairs_cache_cost_and_role_models(self):
        llm = FakeLlm(
            [
                FakeResult(
                    {"value": "member"},
                    provider="host",
                    model="m1",
                    usage=FakeUsage(10, 5, 15, 2, 3, 0.10),
                ),
                FakeResult(
                    None,
                    provider="host",
                    model="m2",
                    usage=FakeUsage(7, 0, 7, 1, 0, 0.02),
                ),
                FakeResult(
                    {"value": "moderated"},
                    provider="host",
                    model="m2",
                    usage=FakeUsage(4, 6, 10, 0, 4, 0.08),
                ),
            ]
        )

        outcome = await StructuredInferenceRunner(FakeContext(llm)).run(
            [call("member", "member"), call("moderator", "moderator")], quorum=2
        )

        self.assertEqual(outcome.usage.calls, 3)
        self.assertEqual(outcome.usage.repairs, 1)
        self.assertEqual(outcome.usage.input_tokens, 21)
        self.assertEqual(outcome.usage.output_tokens, 11)
        self.assertEqual(outcome.usage.cache_read_tokens, 3)
        self.assertEqual(outcome.usage.cache_write_tokens, 7)
        self.assertEqual(outcome.usage.estimated_cost, 0.2)
        self.assertEqual(
            [(item.role, item.calls, item.tokens, item.provider, item.model) for item in outcome.usage.model_usage],
            [("member", 1, 15, "host", "m1"), ("moderator", 2, 17, "host", "m2")],
        )

    async def test_cancelling_runner_cancels_pending_calls_without_late_results(self):
        llm = FakeLlm([(1, FakeResult({"value": "late"})), (1, FakeResult({"value": "later"}))])
        runner = StructuredInferenceRunner(FakeContext(llm))
        task = asyncio.create_task(runner.run([call("a"), call("b")], quorum=1))

        while len(llm.calls) < 2:
            await asyncio.sleep(0)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        await asyncio.sleep(0)

        self.assertCountEqual(llm.cancelled, ["hermes_council_member", "hermes_council_member"])

    async def test_invalid_batch_is_rejected_before_provider_invocation(self):
        llm = FakeLlm([])
        runner = StructuredInferenceRunner(FakeContext(llm))

        with self.assertRaises(ValueError):
            await runner.run([call("duplicate"), call("duplicate")], quorum=1)
        with self.assertRaises(ValueError):
            await runner.run([call("a")], quorum=2)
        self.assertEqual(llm.calls, [])


class RegisterTest(unittest.TestCase):
    def test_registers_exactly_the_plugin_owned_task_keys(self):
        context = FakeContext()

        register(context)

        self.assertEqual(
            [key for key, _ in context.registered],
            ["hermes_council_member", "hermes_council_moderator", "hermes_council_verifier"],
        )


if __name__ == "__main__":
    unittest.main()
