import json
import os
import re

from openai import OpenAI
from sqlalchemy import text


TOPIC_EXPANSION_MODEL = os.getenv(
    "OPENAI_TOPIC_EXPANSION_MODEL",
    "gpt-6-luna",
)

MAX_DIRECT_TERMS = 6
MAX_DOMAIN_TERMS = 12


def _clean_json_text(value: str) -> str:
    value = (value or "").strip()

    if value.startswith("```"):
        value = re.sub(
            r"^```(?:json)?\s*",
            "",
            value,
            flags=re.IGNORECASE,
        )
        value = re.sub(
            r"\s*```$",
            "",
            value,
        )

    return value.strip()


def _normalize_terms(
    raw_terms,
    *,
    max_terms: int,
) -> list[str]:
    if not isinstance(raw_terms, list):
        return []

    terms = []
    seen = set()

    for value in raw_terms:
        if not isinstance(value, str):
            continue

        term = " ".join(
            value.strip().split()
        )

        if len(term) < 3:
            continue

        key = term.casefold()

        if key in seen:
            continue

        seen.add(key)
        terms.append(term)

        if len(terms) >= max_terms:
            break

    return terms


def expand_topic_with_ai(topic: str) -> dict:
    """
    Converts one simple user topic into internal search metadata.

    The end user only enters `topic`.

    direct_terms:
        Exact names, acronyms, official denominations and very close
        equivalents. A direct-term hit is enough to create a strong match.

    domain_terms:
        Specific subjects that clearly belong to the topic's area of
        interest. They are NOT enough alone: the monitoring engine also
        requires semantic compatibility with the topic.
    """

    clean_topic = " ".join(
        (topic or "").strip().split()
    )

    if not clean_topic:
        raise ValueError("Topic cannot be empty")

    prompt = f"""
Você está configurando um motor brasileiro de monitoramento legislativo,
regulatório e institucional.

O usuário informou apenas este tema de interesse:

TEMA: {clean_topic}

Sua tarefa é transformar esse tema em metadados INTERNOS de busca.

Gere três campos:

1. semantic_description
   Uma descrição curta e específica do assunto que o usuário quer acompanhar.

2. direct_terms
   Nomes exatos, siglas, denominações oficiais, nomes completos e equivalentes
   praticamente inequívocos do tema.
   Um documento que contenha um desses termos pode ser considerado uma
   correspondência direta.
   Inclua o próprio tema quando fizer sentido.

3. domain_terms
   Conceitos CANÔNICOS, curtos e específicos que pertencem claramente ao
   domínio do tema mesmo quando o nome exato não aparece.
   Esses termos serão usados como expressões de busca textual e somente serão
   aceitos quando houver também compatibilidade semântica.

Regras obrigatórias:
- seja conservador;
- cada domain_term deve ter preferencialmente de 1 a 4 palavras;
- prefira a forma mais curta que preserve o significado específico;
- NÃO gere frases descritivas completas;
- NÃO inclua enumerações dentro de um único termo;
- divida conceitos diferentes em termos separados;
- evite palavras genéricas isoladas como:
  "regulação", "mercado", "política", "governo", "serviço", "projeto",
  "setor", "economia", "fiscalização", "tecnologia";
- exemplos bons: "energia elétrica", "geração distribuída",
  "revisão tarifária", "bandeira tarifária", "rede elétrica";
- exemplos ruins: "concessões de geração, transmissão e distribuição de energia elétrica",
  "Procedimentos de Distribuição de Energia Elétrica no Sistema Elétrico Nacional";
- não invente relações apenas possíveis ou indiretas;
- direct_terms devem representar o próprio tema;
- domain_terms devem representar matérias realmente pertencentes ao domínio;
- no máximo {MAX_DIRECT_TERMS} direct_terms;
- no máximo {MAX_DOMAIN_TERMS} domain_terms;
- português do Brasil;
- responda SOMENTE JSON válido, sem markdown.

Formato exato:
{{
  "semantic_description": "descrição curta e específica",
  "direct_terms": [
    "termo direto 1",
    "termo direto 2"
  ],
  "domain_terms": [
    "termo de domínio 1",
    "termo de domínio 2"
  ]
}}
""".strip()

    try:
        client = OpenAI()

        response = client.responses.create(
            model=TOPIC_EXPANSION_MODEL,
            input=prompt,
        )

        raw_text = getattr(
            response,
            "output_text",
            "",
        )

        parsed = json.loads(
            _clean_json_text(raw_text)
        )

        if not isinstance(parsed, dict):
            parsed = {}

        semantic_description = (
            parsed.get("semantic_description")
        )

        if not isinstance(
            semantic_description,
            str,
        ):
            semantic_description = clean_topic

        semantic_description = " ".join(
            semantic_description.strip().split()
        ) or clean_topic

        direct_terms = _normalize_terms(
            parsed.get(
                "direct_terms",
                [],
            ),
            max_terms=MAX_DIRECT_TERMS,
        )

        # Guarantee that the user's own topic remains a direct signal.
        direct_keys = {
            value.casefold()
            for value in direct_terms
        }

        if (
            clean_topic.casefold()
            not in direct_keys
        ):
            direct_terms.insert(
                0,
                clean_topic,
            )

        direct_terms = (
            direct_terms[
                :MAX_DIRECT_TERMS
            ]
        )

        domain_terms = _normalize_terms(
            parsed.get(
                "domain_terms",
                [],
            ),
            max_terms=MAX_DOMAIN_TERMS,
        )

        # Domain terms are lexical search concepts, not long descriptions.
        # Keep only compact terms even if the model returns verbose phrases.
        domain_terms = [
            value
            for value in domain_terms
            if len(value.split()) <= 5
        ]

        direct_keys = {
            value.casefold()
            for value in direct_terms
        }

        # Keep the two groups conceptually distinct.
        domain_terms = [
            value
            for value in domain_terms
            if value.casefold()
            not in direct_keys
        ][
            :MAX_DOMAIN_TERMS
        ]

        return {
            "topic": clean_topic,
            "semantic_description": (
                semantic_description
            ),
            "direct_terms": (
                direct_terms
            ),
            "domain_terms": (
                domain_terms
            ),
            "generator": {
                "provider": "OpenAI",
                "model": (
                    TOPIC_EXPANSION_MODEL
                ),
                "response_id": getattr(
                    response,
                    "id",
                    None,
                ),
            },
        }

    except Exception as exc:
        # Safe fallback:
        # the user-provided topic still works as a direct keyword.
        return {
            "topic": clean_topic,
            "semantic_description": (
                clean_topic
            ),
            "direct_terms": [
                clean_topic
            ],
            "domain_terms": [],
            "generator": {
                "provider": "fallback",
                "model": None,
                "error": str(exc),
            },
        }


def expand_and_save_topic(
    *,
    engine,
    topic_id: int,
) -> dict:
    with engine.connect() as connection:
        row = connection.execute(
            text("""
                SELECT
                    id,
                    profile_id,
                    topic
                FROM monitoring_topics
                WHERE id = :topic_id
                LIMIT 1
            """),
            {
                "topic_id": topic_id,
            },
        ).mappings().first()

    if not row:
        return {
            "success": False,
            "reason": "topic_not_found",
            "topic_id": topic_id,
        }

    expansion = expand_topic_with_ai(
        row["topic"]
    )

    # expanded_terms is kept populated for backward compatibility,
    # but the new matching engine uses direct_terms/domain_terms.
    expanded_terms = list(
        dict.fromkeys(
            expansion["direct_terms"]
            + expansion["domain_terms"]
        )
    )

    with engine.begin() as connection:
        updated = connection.execute(
            text("""
                UPDATE monitoring_topics
                SET
                    semantic_description =
                        :semantic_description,
                    direct_terms =
                        CAST(:direct_terms AS JSONB),
                    domain_terms =
                        CAST(:domain_terms AS JSONB),
                    expanded_terms =
                        CAST(:expanded_terms AS JSONB)
                WHERE id = :topic_id
                RETURNING
                    id,
                    profile_id,
                    topic,
                    semantic_description,
                    direct_terms,
                    domain_terms,
                    expanded_terms,
                    weight,
                    urgency_boost,
                    enabled,
                    created_at
            """),
            {
                "topic_id": topic_id,
                "semantic_description": (
                    expansion[
                        "semantic_description"
                    ]
                ),
                "direct_terms": json.dumps(
                    expansion[
                        "direct_terms"
                    ],
                    ensure_ascii=False,
                ),
                "domain_terms": json.dumps(
                    expansion[
                        "domain_terms"
                    ],
                    ensure_ascii=False,
                ),
                "expanded_terms": json.dumps(
                    expanded_terms,
                    ensure_ascii=False,
                ),
            },
        ).mappings().first()

    return {
        "success": True,
        "topic": dict(updated),
        "generator": (
            expansion["generator"]
        ),
    }


def expand_profile_topics(
    *,
    engine,
    profile_id: int,
) -> dict:
    with engine.connect() as connection:
        profile = connection.execute(
            text("""
                SELECT id, name
                FROM monitoring_profiles
                WHERE id = :profile_id
                LIMIT 1
            """),
            {
                "profile_id": profile_id,
            },
        ).mappings().first()

        if not profile:
            return {
                "success": False,
                "reason": "profile_not_found",
                "profile_id": profile_id,
            }

        rows = connection.execute(
            text("""
                SELECT id
                FROM monitoring_topics
                WHERE profile_id = :profile_id
                ORDER BY id ASC
            """),
            {
                "profile_id": profile_id,
            },
        ).mappings().all()

    results = [
        expand_and_save_topic(
            engine=engine,
            topic_id=int(row["id"]),
        )
        for row in rows
    ]

    return {
        "success": True,
        "profile": dict(profile),
        "topics_processed": len(results),
        "results": results,
    }
