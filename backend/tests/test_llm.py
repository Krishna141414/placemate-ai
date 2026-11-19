"""LLM providers and the fallback router."""

from __future__ import annotations

import re
import types

import pytest

from app.config import get_settings
from app.llm import router
from app.llm.base import LLMRequest, Passage, ProviderError
from app.llm.extractive import ExtractiveProvider, split_sentences
from app.llm.gemini import GeminiProvider
from app.llm.local import LocalProvider, _cache_dir_for
from app.rag.prompts import SYSTEM_PROMPT, build_prompt

PASSAGES = [
    Passage(
        n=1,
        title="Nimbusware Technologies - Software Engineer Trainee",
        section="Eligibility",
        text="- Branches: CSE, IT and ECE.\n- Minimum CGPA: 7.0.\n- Active backlogs: at most 1 at the time of applying.\n- Batch: 2027 graduates.",
        score=7.5,
    ),
    Passage(
        n=2,
        title="Placement Policy 2026-27",
        section="13. Dress code and conduct",
        text="Formal dress is compulsory for all interview rounds. Jeans are not allowed.",
        score=-4.0,
    ),
]


def make_request(question: str = "What is the minimum CGPA for Nimbusware?") -> LLMRequest:
    return LLMRequest(system=SYSTEM_PROMPT, prompt=build_prompt(question, PASSAGES), question=question, passages=PASSAGES)


class Scripted:
    def __init__(self, name, text=None, error=None, usable=True):
        self.name, self.model = name, f"fake-{name}"
        self._text, self._error, self._usable = text, error, usable
        self.calls = 0

    def available(self):
        return (self._usable, "" if self._usable else "no API key")

    def generate(self, request):
        self.calls += 1
        if self._error:
            raise ProviderError(self._error)
        return self._text


# --- router ---------------------------------------------------------------


@pytest.mark.parametrize(
    "start,expected",
    [
        ("gemini", ["gemini", "local", "extractive"]),
        ("local", ["local", "extractive"]),
        ("extractive", ["extractive"]),
        ("something-else", ["gemini", "local", "extractive"]),
    ],
)
def test_chain_always_runs_gemini_local_extractive_from_the_configured_start(start, expected):
    assert [provider.name for provider in router.provider_chain(start)] == expected


def test_first_working_provider_answers(monkeypatch):
    first = Scripted("gemini", text="Answer [1].")
    second = Scripted("local", text="unused")
    monkeypatch.setattr(router, "provider_chain", lambda start=None: [first, second])
    result = router.generate(make_request())
    assert (result.provider, result.text, result.fallbacks) == ("gemini", "Answer [1].", [])
    assert second.calls == 0


def test_fallback_chain_records_why_each_provider_was_skipped(monkeypatch):
    chain = [
        Scripted("gemini", usable=False),
        Scripted("local", error="could not load (OSError)"),
        router.get_provider("extractive"),
    ]
    monkeypatch.setattr(router, "provider_chain", lambda start=None: chain)
    result = router.generate(make_request())
    assert result.provider == "extractive"
    assert result.fallbacks == ["gemini: no API key", "local: could not load (OSError)"]
    assert chain[0].calls == 0


def test_rejected_answer_moves_to_the_next_provider(monkeypatch):
    chain = [Scripted("gemini", text="no citations here"), Scripted("local", text="Good answer [1].")]
    monkeypatch.setattr(router, "provider_chain", lambda start=None: chain)
    result = router.generate(make_request(), accept=lambda text: None if "[1]" in text else "no citation")
    assert result.provider == "local"
    assert result.fallbacks == ["gemini: no citation"]


def test_extractive_is_never_rejected(monkeypatch):
    monkeypatch.setattr(router, "provider_chain", lambda start=None: [router.get_provider("extractive")])
    result = router.generate(make_request(), accept=lambda text: "always reject")
    assert result.provider == "extractive"


def test_all_providers_failing_raises(monkeypatch):
    monkeypatch.setattr(router, "provider_chain", lambda start=None: [Scripted("gemini", error="boom")])
    with pytest.raises(ProviderError):
        router.generate(make_request())


def test_provider_status_lists_all_three():
    status = router.provider_status()
    assert [row["name"] for row in status] == ["gemini", "local", "extractive"]
    by_name = {row["name"]: row for row in status}
    assert by_name["extractive"]["available"] is True
    assert by_name["gemini"]["available"] is False  # no key in the test environment
    assert by_name["gemini"]["reason"] == "no API key"
    assert by_name["extractive"]["configured"] is True


# --- extractive -----------------------------------------------------------


def test_extractive_answer_is_made_only_of_source_sentences(app):
    answer = ExtractiveProvider().generate(make_request())
    assert "Minimum CGPA: 7.0." in answer
    assert re.findall(r"\[(\d)\]", answer)
    source_text = " ".join(passage.text.replace("- ", "") for passage in PASSAGES)
    for sentence in re.split(r"\s*\[\d\]\s*", answer):
        if sentence:
            assert sentence in source_text


def test_extractive_ignores_passages_far_below_the_best(app):
    answer = ExtractiveProvider().generate(make_request())
    assert "[2]" not in answer  # the dress-code passage scored far lower
    assert "Jeans" not in answer


def test_extractive_keeps_a_list_together(app):
    answer = ExtractiveProvider().generate(make_request("Who is eligible for Nimbusware?"))
    assert "Branches: CSE, IT and ECE." in answer and "Batch: 2027 graduates." in answer


def test_extractive_with_nothing_to_extract_raises(app):
    request = LLMRequest(system="", prompt="", question="anything", passages=[Passage(n=1, title="T", section="", text="...")])
    with pytest.raises(ProviderError):
        ExtractiveProvider().generate(request)


def test_sentence_splitting():
    assert split_sentences("First sentence here. Second one follows! Is this the third?") == [
        "First sentence here.",
        "Second one follows!",
        "Is this the third?",
    ]
    assert split_sentences("- **Bold item** with text here.\n- ok") == ["Bold item with text here."]


# --- gemini ---------------------------------------------------------------


class _FakeModels:
    def __init__(self, text=None, error=None):
        self._text, self._error = text, error
        self.kwargs = None

    def generate_content(self, **kwargs):
        self.kwargs = kwargs
        if self._error:
            raise self._error
        return types.SimpleNamespace(text=self._text)


def _gemini_with(models) -> GeminiProvider:
    provider = GeminiProvider()
    provider._client = types.SimpleNamespace(models=models)
    return provider


def test_gemini_is_unavailable_without_a_key():
    assert GeminiProvider().available() == (False, "no API key")


def test_gemini_is_available_with_a_key(monkeypatch):
    monkeypatch.setattr(get_settings(), "gemini_api_key", "test-key")
    assert GeminiProvider().available() == (True, "")


def test_gemini_sends_system_instruction_and_returns_text():
    models = _FakeModels(text="  The minimum CGPA is 7.0 [1].  ")
    answer = _gemini_with(models).generate(make_request())
    assert answer == "The minimum CGPA is 7.0 [1]."
    assert models.kwargs["model"] == get_settings().gemini_model
    assert models.kwargs["config"].system_instruction == SYSTEM_PROMPT
    assert "<source n=\"1\"" in models.kwargs["contents"]


def test_gemini_empty_response_is_a_provider_error():
    with pytest.raises(ProviderError, match="empty response"):
        _gemini_with(_FakeModels(text="")).generate(make_request())


def test_gemini_api_error_is_a_provider_error_without_details():
    from google.genai import errors

    api_error = errors.APIError(429, {"error": {"message": "quota exceeded for key ABC123", "status": "RESOURCE_EXHAUSTED"}})
    with pytest.raises(ProviderError) as info:
        _gemini_with(_FakeModels(error=api_error)).generate(make_request())
    assert "429" in str(info.value)
    assert "ABC123" not in str(info.value)


def test_gemini_network_failure_is_a_provider_error():
    with pytest.raises(ProviderError, match="TimeoutError"):
        _gemini_with(_FakeModels(error=TimeoutError("timed out"))).generate(make_request())


# --- local ----------------------------------------------------------------


def test_local_reports_missing_model(monkeypatch):
    monkeypatch.setattr(get_settings(), "local_model", "nobody/not-a-real-model")
    assert LocalProvider().available() == (False, "model not in local cache")


def test_local_load_failure_is_remembered(monkeypatch, tmp_path):
    monkeypatch.setattr(get_settings(), "local_model", "nobody/not-a-real-model")
    monkeypatch.setenv("HF_HUB_CACHE", str(tmp_path))
    (tmp_path / "models--nobody--not-a-real-model").mkdir()
    provider = LocalProvider()
    assert provider.available()[0] is True
    with pytest.raises(ProviderError):
        provider.generate(make_request())
    usable, reason = provider.available()
    assert usable is False and "could not load" in reason


@pytest.mark.slow
def test_local_model_generates_text():
    """Runs the real cached Qwen model on CPU. Skipped when it is not cached."""
    if not _cache_dir_for(get_settings().local_model).exists():
        pytest.skip("local model is not in the Hugging Face cache")
    provider = LocalProvider()
    answer = provider.generate(make_request())
    assert isinstance(answer, str) and len(answer.split()) >= 3
    assert provider.available() == (True, "")
