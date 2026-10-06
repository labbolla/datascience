import httpx

from datetime import datetime

from sources.base import (
    SourceStory,
    SOURCE_TYPE_OFFICIAL,
)


BASE_URL = (
    "https://dadosabertos.camara.leg.br/api/v2"
)


async def fetch_recent_propositions():
    """
    Fetches the most recent propositions from
    Câmara dos Deputados.

    Returns raw API objects.
    """

    params = {
        "itens": 10,
        "ordem": "DESC",
        "ordenarPor": "id",
    }

    async with httpx.AsyncClient(
        timeout=30
    ) as client:

        response = await client.get(
            f"{BASE_URL}/proposicoes",
            params=params,
            headers={
                "Accept": "application/json"
            },
        )

        response.raise_for_status()

        data = response.json()

    return data.get(
        "dados",
        [],
    )


async def fetch_proposition_details(
    proposition_id: int,
):
    """
    Fetches complete information for one proposition.
    """

    async with httpx.AsyncClient(
        timeout=30
    ) as client:

        response = await client.get(
            f"{BASE_URL}/proposicoes/{proposition_id}",
            headers={
                "Accept": "application/json"
            },
        )

        response.raise_for_status()

        data = response.json()

    return data.get(
        "dados",
        {},
    )


def normalize_camara_proposition(
    proposition: dict,
) -> SourceStory:
    """
    Converts a Câmara API proposition into the
    normalized SourceStory format used by the
    generic ingestion pipeline.
    """

    proposition_id = proposition[
        "id"
    ]

    sigla = (
        proposition.get(
            "siglaTipo"
        )
        or "Proposição"
    )

    numero = proposition.get(
        "numero"
    )

    ano = proposition.get(
        "ano"
    )

    # ---------------------------------------------
    # TITLE
    # ---------------------------------------------

    if numero is not None and ano:
        title = (
            f"{sigla} "
            f"{numero}/{ano}"
        )

    elif numero is not None:
        title = (
            f"{sigla} "
            f"{numero}"
        )

    else:
        title = sigla

    # ---------------------------------------------
    # SUMMARY
    # ---------------------------------------------

    summary = (
        proposition.get(
            "ementa"
        )
        or None
    )

    # ---------------------------------------------
    # PUBLISHED DATE
    # ---------------------------------------------

    published_at = None

    raw_date = proposition.get(
        "dataApresentacao"
    )

    if raw_date:
        try:
            published_at = (
                datetime.fromisoformat(
                    raw_date
                )
            )
        except ValueError:
            published_at = None

    # ---------------------------------------------
    # URL
    # ---------------------------------------------

    api_uri = proposition.get(
        "uri"
    )

    url = (
        "https://www.camara.leg.br/"
        "proposicoesWeb/"
        "fichadetramitacao"
        f"?idProposicao={proposition_id}"
    )

    # ---------------------------------------------
    # NORMALIZED STORY
    # ---------------------------------------------

    return {
        "external_id": str(proposition_id),

        "title": title,

        "summary": summary,

        "url": url,

        "source": "Câmara dos Deputados",

        "source_type": SOURCE_TYPE_OFFICIAL,

        "source_entity_id": (
            f"camara:{proposition_id}"
        ),

        "source_event_type": (
            "PROPOSICAO"
        ),

        "published_at": published_at,
    }


async def fetch_camara_stories():
    """
    Fetches Câmara propositions and returns them
    already normalized for the generic ingestion
    pipeline.
    """

    propositions = (
        await fetch_recent_propositions()
    )

    stories: list[SourceStory] = []

    for proposition in propositions:

        story = (
            normalize_camara_proposition(
                proposition
            )
        )

        stories.append(
            story
        )

    return stories