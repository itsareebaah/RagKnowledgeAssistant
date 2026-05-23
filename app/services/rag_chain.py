import httpx
from openai import OpenAI

from app.config import settings
from app.models.schemas import SourceChunk

SYSTEM_PROMPT = """You are a helpful company knowledge assistant.
Answer questions using ONLY the provided context from company documents.
If the context does not contain enough information, say so clearly.
Cite which document(s) your answer draws from when possible.
Be concise and accurate."""


def _build_context(hits: list[dict]) -> str:
    blocks = []
    for i, hit in enumerate(hits, 1):
        blocks.append(
            f"[Source {i} | {hit['filename']} | relevance: {hit['score']}]\n{hit['text']}"
        )
    return "\n\n---\n\n".join(blocks)


def _hits_to_sources(hits: list[dict]) -> list[SourceChunk]:
    return [
        SourceChunk(text=h["text"], filename=h["filename"], score=h["score"])
        for h in hits
    ]


def _generate_openai(question: str, context: str) -> str:
    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {question}",
            },
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content or ""


def _ollama_prompt(question: str, context: str) -> str:
    return f"{SYSTEM_PROMPT}\n\nContext:\n{context}\n\nQuestion: {question}"


def _generate_ollama(question: str, context: str) -> str:
    base = settings.ollama_base_url.rstrip("/")
    model = settings.ollama_model
    prompt = _ollama_prompt(question, context)

    with httpx.Client(timeout=120.0) as client:
        chat = client.post(
            f"{base}/api/chat",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": f"Context:\n{context}\n\nQuestion: {question}",
                    },
                ],
                "stream": False,
            },
        )
        if chat.status_code == 200:
            return chat.json()["message"]["content"]

        # Older Ollama builds use /api/generate instead of /api/chat
        gen = client.post(
            f"{base}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
        )
        gen.raise_for_status()
        return gen.json()["response"]


def _generate_extractive(question: str, hits: list[dict]) -> str:
    if not hits:
        return (
            "No relevant documents found. Upload company documents first, "
            "then ask your question again."
        )

    intro = (
        "No LLM API configured (set OPENAI_API_KEY or run Ollama). "
        "Here are the most relevant passages for your question:\n\n"
    )
    passages = "\n\n".join(
        f"**{h['filename']}** (score {h['score']}):\n{h['text']}"
        for h in hits[:3]
    )
    return intro + passages


def _ollama_available() -> bool:
    try:
        base = settings.ollama_base_url.rstrip("/")
        target = settings.ollama_model.split(":")[0]
        with httpx.Client(timeout=3.0) as client:
            r = client.get(f"{base}/api/tags")
            if r.status_code != 200:
                return False
            names = [m.get("name", "") for m in r.json().get("models", [])]
            has_model = any(
                n == target or n.startswith(f"{target}:") for n in names
            )
            return has_model
    except (httpx.HTTPError, OSError, ValueError):
        return False


def _resolve_provider() -> str:
    if settings.openai_api_key:
        return "openai"
    if _ollama_available():
        return "ollama"
    return "extractive"


def generate_answer(question: str, hits: list[dict]) -> tuple[str, str]:
    context = _build_context(hits)
    provider = _resolve_provider()

    try:
        if provider == "openai":
            answer = _generate_openai(question, context)
        elif provider == "ollama":
            answer = _generate_ollama(question, context)
        else:
            answer = _generate_extractive(question, hits)
    except Exception:
        answer = _generate_extractive(question, hits)
        provider = "extractive"

    return answer, provider
