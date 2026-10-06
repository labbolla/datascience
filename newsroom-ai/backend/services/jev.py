import os

import httpx
from dotenv import load_dotenv

load_dotenv()

TYPESAFE_API_KEY = os.getenv("TYPESAFE_API_KEY")

BASE_URL = "https://api.typesafe.ai"


def get_headers():
    if not TYPESAFE_API_KEY:
        raise RuntimeError(
            "TYPESAFE_API_KEY não encontrada no arquivo .env"
        )

    return {
        "Authorization": f"Bearer {TYPESAFE_API_KEY}",
        "Content-Type": "application/json",
    }


async def get_models():
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f"{BASE_URL}/v1/models",
            headers=get_headers(),
        )

        response.raise_for_status()
        return response.json()


async def classify_story(title: str, summary: str):
    state = f"""
Título:
{title}

Conteúdo:
{summary}
""".strip()

    payload = {
        "model": "jev-latest",
        "state": state,
        "questions": {

            # PRIORIDADE
            "high_priority": {
                "type": "noul",
                "instructions": (
                    "Esta informação tem potencial relevância jornalística "
                    "imediata para uma redação nacional brasileira?"
                ),
            },

            # CONTEXTO POLÍTICO
            "political_relevance": {
                "type": "noul",
                "instructions": (
                    "Esta informação possui relevância política, legislativa "
                    "ou governamental significativa?"
                ),
            },

            # CATEGORIAS EDITORIAIS
            "economy": {
                "type": "noul",
                "instructions": (
                    "O tema principal pertence ao campo de economia, finanças, "
                    "empresas, energia, trabalho ou mercados?"
                ),
            },

            "health": {
                "type": "noul",
                "instructions": (
                    "O tema principal pertence ao campo de saúde pública, "
                    "medicina, medicamentos ou sistema de saúde?"
                ),
            },

            "environment": {
                "type": "noul",
                "instructions": (
                    "O tema principal pertence ao campo de meio ambiente, "
                    "clima, recursos naturais ou sustentabilidade?"
                ),
            },

            "technology": {
                "type": "noul",
                "instructions": (
                    "O tema principal pertence ao campo de tecnologia, "
                    "telecomunicações, internet, inteligência artificial "
                    "ou inovação?"
                ),
            },

            "education": {
                "type": "noul",
                "instructions": (
                    "O tema principal pertence ao campo de educação, "
                    "universidades, escolas ou formação profissional?"
                ),
            },

            "security": {
                "type": "noul",
                "instructions": (
                    "O tema principal pertence ao campo de segurança pública, "
                    "criminalidade, polícia ou defesa?"
                ),
            },

            "justice": {
                "type": "noul",
                "instructions": (
                    "O tema principal pertence ao campo jurídico, judicial, "
                    "regulatório ou de direitos?"
                ),
            },

            "culture": {
                "type": "noul",
                "instructions": (
                    "O tema principal pertence ao campo de cultura, "
                    "arte, entretenimento ou patrimônio?"
                ),
            },

            "sports": {
                "type": "noul",
                "instructions": (
                    "O tema principal pertence ao campo de esportes?"
                ),
            },

            "international": {
                "type": "noul",
                "instructions": (
                    "O tema principal pertence a relações internacionais, "
                    "política externa ou assuntos internacionais?"
                ),
            },

            "public_administration": {
                "type": "noul",
                "instructions": (
                    "O tema principal pertence à administração pública, "
                    "gestão governamental, serviço público ou funcionamento "
                    "institucional do Estado?"
                ),
            },
        },
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{BASE_URL}/v1/systemone",
            headers=get_headers(),
            json=payload,
        )

        response.raise_for_status()
        return response.json()


def interpret_classification(result: dict):
    answers = result.get("answers", {})

    def score(name: str) -> float:
        value = answers.get(name, {}).get("noul", 0.0)

        if isinstance(value, (int, float)):
            return float(value)

        return 0.0

    priority_score = score("high_priority")
    political_relevance = score("political_relevance")

    category_scores = {
        "Economia": score("economy"),
        "Saúde": score("health"),
        "Meio Ambiente": score("environment"),
        "Tecnologia": score("technology"),
        "Educação": score("education"),
        "Segurança": score("security"),
        "Justiça": score("justice"),
        "Cultura": score("culture"),
        "Esportes": score("sports"),
        "Internacional": score("international"),
        "Administração Pública": score("public_administration"),
    }

    category = max(
        category_scores,
        key=category_scores.get,
    )

    category_score = category_scores[category]

    if category_score < 0.50:
        category = "Outros"

    tags = [
        name
        for name, value in category_scores.items()
        if value >= 0.70
    ]

    if priority_score >= 0.80:
        priority = "Alta"
    elif priority_score >= 0.50:
        priority = "Média"
    else:
        priority = "Baixa"

    return {
        "priority": priority,
        "priority_score": priority_score,
        "category": category,
        "category_score": category_score,
        "political_relevance": political_relevance,
        "tags": tags,
        "category_scores": category_scores,
    }



async def compare_story_with_candidates(
    story: dict,
    candidates: list[dict],
):
    if not candidates:
        return {
            "model": None,
            "answers": {},
            "usage": {},
        }

    state_parts = [
        "STORY NOVA:",
        f"Título: {story.get('title', '')}",
        f"Conteúdo: {story.get('summary', '')}",
        "",
        (
            "Avalie cada candidato de forma independente. "
            "Compare sempre o candidato apenas com a STORY NOVA. "
            "Não compare os candidatos entre si."
        ),
        "",
        (
            "IMPORTANTE: documentos podem ter linguagem legislativa, "
            "órgãos, relatores ou formatos semelhantes sem pertencerem "
            "ao mesmo desenvolvimento jornalístico."
        ),
        "",
    ]

    questions = {}

    for index, candidate in enumerate(
        candidates,
        start=1,
    ):
        state_parts.extend(
            [
                f"CANDIDATO {index}:",
                f"ID: {candidate.get('id')}",
                f"Título: {candidate.get('title', '')}",
                f"Conteúdo: {candidate.get('summary', '')}",
                "",
            ]
        )

        # -------------------------------------------------
        # SIGNAL 1: SAME THREAD
        # -------------------------------------------------

        questions[f"same_thread_{index}"] = {
            "type": "noul",
            "instructions": (
                f"A STORY NOVA e o CANDIDATO {index} tratam "
                "do mesmo fato, processo, medida, evento ou "
                "desenvolvimento jornalístico específico? "
                "Não considere suficiente apenas o fato de "
                "pertencerem ao mesmo setor, órgão, comissão, "
                "categoria legislativa ou assunto genérico."
            ),
        }

        # -------------------------------------------------
        # SIGNAL 2: DIRECT CONTINUATION
        # -------------------------------------------------

        questions[
            f"direct_continuation_{index}"
        ] = {
            "type": "noul",
            "instructions": (
                f"A STORY NOVA representa uma continuação, "
                f"nova etapa, resposta, consequência, atualização "
                f"ou desenvolvimento direto do CANDIDATO {index}? "
                "Considere baixa a resposta quando os documentos "
                "são apenas semelhantes em forma ou tema."
            ),
        }

        # -------------------------------------------------
        # SIGNAL 3: SHARED SPECIFIC REFERENCE
        # -------------------------------------------------

        questions[
            f"shared_specific_reference_{index}"
        ] = {
            "type": "noul",
            "instructions": (
                f"A STORY NOVA e o CANDIDATO {index} compartilham "
                "uma referência factual específica que indique "
                "fortemente que pertencem ao mesmo caso? "
                "Exemplos: mesma proposição de origem, indicação, "
                "processo, investigação, pessoa central, decisão, "
                "medida, evento, contrato ou fato concreto. "
                "Não considere suficiente compartilhar apenas "
                "um ministério, relator, partido, área temática "
                "ou tipo de documento."
            ),
        }

    payload = {
        "model": "jev-latest",
        "state": "\n".join(state_parts),
        "questions": questions,
    }

    async with httpx.AsyncClient(
        timeout=30
    ) as client:
        response = await client.post(
            f"{BASE_URL}/v1/systemone",
            headers=get_headers(),
            json=payload,
        )

        response.raise_for_status()

        return response.json()


def interpret_thread_candidates(
    result: dict,
    candidates: list[dict],
):
    answers = result.get(
        "answers",
        {},
    )

    def extract_score(
        question_name: str,
    ) -> float:
        answer = answers.get(
            question_name,
            {},
        )

        score = answer.get(
            "noul",
            0.0,
        )

        if not isinstance(
            score,
            (int, float),
        ):
            return 0.0

        return float(score)

    evaluated = []

    for index, candidate in enumerate(
        candidates,
        start=1,
    ):
        same_thread = extract_score(
            f"same_thread_{index}"
        )

        direct_continuation = extract_score(
            f"direct_continuation_{index}"
        )

        shared_specific_reference = (
            extract_score(
                f"shared_specific_reference_{index}"
            )
        )

        evaluated.append(
            {
                **candidate,

                "same_thread_score": (
                    same_thread
                ),

                "direct_continuation_score": (
                    direct_continuation
                ),

                "shared_specific_reference_score": (
                    shared_specific_reference
                ),
            }
        )

    evaluated.sort(
        key=lambda item: (
            item[
                "same_thread_score"
            ],
            item[
                "shared_specific_reference_score"
            ],
            item[
                "direct_continuation_score"
            ],
        ),
        reverse=True,
    )

    return evaluated

async def analyze_story_changes(
    current_story: dict,
    previous_stories: list[dict],
):
    if not previous_stories:
        return {
            "model": None,
            "answers": {},
            "usage": {},
        }

    state_parts = [
        "NOVA STORY:",
        f"Título: {current_story.get('title', '')}",
        f"Conteúdo: {current_story.get('summary', '')}",
        "",
        "HISTÓRICO JÁ CONHECIDO PELA REDAÇÃO:",
        "",
    ]

    for index, story in enumerate(
        previous_stories,
        start=1,
    ):
        state_parts.extend(
            [
                f"DOCUMENTO ANTERIOR {index}:",
                f"Título: {story.get('title', '')}",
                f"Conteúdo: {story.get('summary', '')}",
                "",
            ]
        )

    questions = {
        "meaningful_change": {
            "type": "noul",
            "instructions": (
                "A NOVA STORY acrescenta informação jornalisticamente "
                "relevante ao histórico já conhecido, em vez de apenas "
                "repetir ou reformular informações anteriores?"
            ),
        },

        "new_information": {
            "type": "noul",
            "instructions": (
                "A NOVA STORY apresenta fatos ou informações substantivas "
                "que não estavam presentes no histórico anterior?"
            ),
        },

        "new_actor": {
            "type": "noul",
            "instructions": (
                "A NOVA STORY introduz um novo ator relevante, como pessoa, "
                "órgão, instituição, empresa ou autoridade, que não tinha "
                "papel relevante no histórico anterior?"
            ),
        },

        "new_measure": {
            "type": "noul",
            "instructions": (
                "A NOVA STORY introduz uma nova medida, proposta, decisão, "
                "providência, obrigação ou ação concreta em relação ao "
                "histórico anterior?"
            ),
        },

        "status_change": {
            "type": "noul",
            "instructions": (
                "A NOVA STORY indica mudança de status ou etapa do processo, "
                "como aprovação, rejeição, sanção, votação, encaminhamento, "
                "abertura de investigação ou outra evolução procedural?"
            ),
        },

        "date_change": {
            "type": "noul",
            "instructions": (
                "A NOVA STORY apresenta nova data, prazo, calendário ou "
                "alteração temporal relevante em comparação com o histórico?"
            ),
        },

        "quantitative_change": {
            "type": "noul",
            "instructions": (
                "A NOVA STORY apresenta novo valor, percentual, quantidade, "
                "meta, orçamento ou outro dado numérico relevante?"
            ),
        },

        "contradiction": {
            "type": "noul",
            "instructions": (
                "A NOVA STORY contradiz, corrige, substitui ou modifica "
                "materialmente alguma informação presente no histórico anterior?"
            ),
        },
    }

    payload = {
        "model": "jev-latest",
        "state": "\n".join(state_parts),
        "questions": questions,
    }

    async with httpx.AsyncClient(
        timeout=30
    ) as client:
        response = await client.post(
            f"{BASE_URL}/v1/systemone",
            headers=get_headers(),
            json=payload,
        )

        response.raise_for_status()

        return response.json()

def interpret_story_changes(
    result: dict,
):
    answers = result.get(
        "answers",
        {},
    )

    def score(name: str) -> float:
        value = (
            answers
            .get(name, {})
            .get("noul", 0.0)
        )

        if isinstance(
            value,
            (int, float),
        ):
            return float(value)

        return 0.0

    return {
        "meaningful_change": score(
            "meaningful_change"
        ),
        "new_information": score(
            "new_information"
        ),
        "new_actor": score(
            "new_actor"
        ),
        "new_measure": score(
            "new_measure"
        ),
        "status_change": score(
            "status_change"
        ),
        "date_change": score(
            "date_change"
        ),
        "quantitative_change": score(
            "quantitative_change"
        ),
        "contradiction": score(
            "contradiction"
        ),
    }