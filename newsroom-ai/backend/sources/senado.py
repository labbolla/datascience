import httpx

from datetime import datetime

from sources.base import (
    SourceStory,
    SOURCE_TYPE_OFFICIAL,
)


BASE_URL = (
    "https://legis.senado.leg.br/dadosabertos"
)


async def fetch_recent_senado_matters(
    days: int = 1,
):
    """
    Fetches matters updated recently in Senado Federal.
    """

    url = (
        f"{BASE_URL}/materia/atualizadas.json"
    )

    params = {
        "numdias": days,
    }

    async with httpx.AsyncClient(
        timeout=30
    ) as client:

        response = await client.get(
            url,
            params=params,
            headers={
                "Accept": "application/json",
                "User-Agent": (
                    "NewsroomAI/0.1"
                ),
            },
        )

        response.raise_for_status()

        return response.json()


def _find_matter_list(
    data: dict,
) -> list[dict]:
    """
    Senado APIs may wrap the result in several nested
    objects. This helper searches recursively for the
    list containing legislative matters.

    We keep this isolated because Senado's JSON structure
    is different from Câmara's.
    """

    if not isinstance(
        data,
        dict,
    ):
        return []

    preferred_keys = (
        "Materias",
        "Materia",
        "materias",
        "materia",
    )

    for key in preferred_keys:

        value = data.get(key)

        if isinstance(
            value,
            list,
        ):
            return value

        if isinstance(
            value,
            dict,
        ):

            nested = (
                _find_matter_list(
                    value
                )
            )

            if nested:
                return nested

    for value in data.values():

        if isinstance(
            value,
            dict,
        ):

            nested = (
                _find_matter_list(
                    value
                )
            )

            if nested:
                return nested

    return []


def _first_value(
    item: dict,
    *names: str,
):
    """
    Returns the first existing non-empty field.

    Senado's API commonly uses PascalCase field names,
    while newer representations may differ.
    """

    for name in names:

        value = item.get(
            name
        )

        if value not in (
            None,
            "",
        ):
            return value

    return None


def normalize_senado_matter(
    matter: dict,
) -> list[SourceStory]:
    """
    Converts one Senado matter into one or more
    SourceStory objects.

    Each recent update becomes a separate story so that
    future changes to the same legislative matter are
    not lost by deduplication.
    """

    identification = (
        matter.get(
            "IdentificacaoMateria"
        )
        or {}
    )

    basic_data = (
        matter.get(
            "DadosBasicosMateria"
        )
        or {}
    )

    recent_updates = (
        matter.get(
            "AtualizacoesRecentes"
        )
        or {}
    )

    # -------------------------------------------------
    # MATTER IDENTIFICATION
    # -------------------------------------------------

    codigo = identification.get(
        "CodigoMateria"
    )

    sigla = identification.get(
        "SiglaSubtipoMateria"
    )

    numero = identification.get(
        "NumeroMateria"
    )

    ano = identification.get(
        "AnoMateria"
    )

    if not codigo:
        raise ValueError(
            "Senado matter without CodigoMateria"
        )

    # -------------------------------------------------
    # TITLE
    # -------------------------------------------------

    if sigla and numero and ano:
        try:
            numero_formatado = str(
                int(numero)
            )
        except ValueError:
            numero_formatado = str(
                numero
            )

        title = (
            f"{sigla} "
            f"{numero_formatado}/{ano}"
        )

    else:
        title = (
            identification.get(
                "DescricaoIdentificacaoMateria"
            )
            or f"Matéria {codigo}"
        )

    # -------------------------------------------------
    # SUMMARY
    # -------------------------------------------------

    summary = (
        basic_data.get(
            "EmentaMateria"
        )
        or None
    )

    # -------------------------------------------------
    # URL
    # -------------------------------------------------

    url = (
        "https://www25.senado.leg.br/"
        "web/atividade/materias/-/materia/"
        f"{codigo}"
    )

    # -------------------------------------------------
    # RECENT UPDATES
    # -------------------------------------------------

    updates = recent_updates.get(
        "Atualizacao",
        [],
    )

    if isinstance(
        updates,
        dict,
    ):
        updates = [
            updates
        ]

    stories: list[
        SourceStory
    ] = []

    # -------------------------------------------------
    # ONE STORY PER UPDATE
    # -------------------------------------------------

    for update in updates:

        update_type = (
            update.get(
                "InformacaoAtualizada"
            )
            or "ATUALIZACAO"
        )

        raw_update_date = (
            update.get(
                "DataUltimaAtualizacao"
            )
        )

        published_at = None

        if raw_update_date:
            try:
                published_at = (
                    datetime.strptime(
                        raw_update_date,
                        "%Y-%m-%d %H:%M:%S",
                    )
                )
            except ValueError:
                try:
                    published_at = (
                        datetime.fromisoformat(
                            raw_update_date
                        )
                    )
                except ValueError:
                    published_at = None

        # ---------------------------------------------
        # EVENT-SPECIFIC EXTERNAL ID
        # ---------------------------------------------

        date_key = (
            raw_update_date
            or basic_data.get(
                "DataApresentacao"
            )
            or "unknown"
        )

        external_id = (
            f"senado:{codigo}:"
            f"{update_type}:"
            f"{date_key}"
        )

        stories.append(
            {
                "external_id": (
                    external_id
                ),

                "title": (
                    title
                ),

                "summary": (
                    summary
                ),

                "url": (
                    url
                ),

                "source": (
                    "Senado Federal"
                ),

                "source_type": (
                    SOURCE_TYPE_OFFICIAL
                ),

                "source_entity_id": (
                    f"senado:{codigo}"
                ),

                "source_event_type": (
                    update_type
                ),

                "published_at": (
                    published_at
                ),
            }
        )

    # -------------------------------------------------
    # FALLBACK:
    # matter without AtualizacoesRecentes
    # -------------------------------------------------

    if not stories:

        raw_date = (
            basic_data.get(
                "DataApresentacao"
            )
        )

        published_at = None

        if raw_date:
            try:
                published_at = (
                    datetime.fromisoformat(
                        raw_date
                    )
                )
            except ValueError:
                pass

        stories.append(
            {
                "external_id": (
                    f"senado:{codigo}:"
                    f"apresentacao:{raw_date}"
                ),

                "title": (
                    title
                ),

                "summary": (
                    summary
                ),

                "url": (
                    url
                ),

                "source": (
                    "Senado Federal"
                ),

                "source_type": (
                    SOURCE_TYPE_OFFICIAL
                ),

                "published_at": (
                    published_at
                ),
                "source_entity_id": (
                    f"senado:{codigo}"
                ),

                "source_event_type": (
                    "APRESENTACAO"
                ),
            }
        )

    return stories

async def fetch_senado_stories(
    days: int = 1,
    limit: int = 10,
):
    """
    Fetches recently updated Senado matters and
    normalizes their recent updates into SourceStory
    objects.
    """

    raw = (
        await fetch_recent_senado_matters(
            days=days
        )
    )

    matters = (
        _find_matter_list(
            raw
        )
    )

    stories: list[
        SourceStory
    ] = []

    for matter in matters:

        try:
            matter_stories = (
                normalize_senado_matter(
                    matter
                )
            )

            stories.extend(
                matter_stories
            )

        except Exception as exc:
            print(
                "[SENADO NORMALIZE ERROR]",
                str(exc),
                matter,
            )

        if len(stories) >= limit:
            break

    return stories[:limit]