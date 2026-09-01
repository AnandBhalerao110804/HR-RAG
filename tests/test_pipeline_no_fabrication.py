from hr_rag.guardrails import NO_SOURCE_ANSWER, has_relevant_content
from hr_rag.models import RetrievedChunk


def test_no_chunks_means_no_relevant_content():
    assert has_relevant_content([]) is False


def test_blank_chunks_means_no_relevant_content():
    chunks = [RetrievedChunk(source="policy_db", text="   ", metadata={})]
    assert has_relevant_content(chunks) is False


def test_a_real_chunk_counts_as_relevant():
    chunks = [RetrievedChunk(source="policy_db", text="PTO accrues monthly.", metadata={})]
    assert has_relevant_content(chunks) is True


def test_no_source_answer_does_not_fabricate():
    assert "couldn't find" in NO_SOURCE_ANSWER
