from sentence_transformers import SentenceTransformer


MODEL_NAME = "intfloat/multilingual-e5-base"

_model = None


def get_embedding_model():
    global _model

    if _model is None:
        print(
            f"[EMBEDDINGS] Carregando modelo: {MODEL_NAME}"
        )

        _model = SentenceTransformer(
            MODEL_NAME
        )

        print(
            "[EMBEDDINGS] Modelo carregado"
        )

    return _model


def build_story_text(
    title: str,
    summary: str,
) -> str:
    title = title or ""
    summary = summary or ""

    return f"{title}\n\n{summary}".strip()


def embed_story(
    title: str,
    summary: str,
) -> list[float]:
    model = get_embedding_model()

    text = build_story_text(
        title,
        summary,
    )

    text = f"query: {text}"

    embedding = model.encode(
        text,
        normalize_embeddings=True,
    )

    return embedding.tolist()