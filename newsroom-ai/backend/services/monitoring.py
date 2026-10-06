import json
import re
import unicodedata
from sqlalchemy import text
from services.embeddings import embed_story

SEMANTIC_TOPIC_THRESHOLD = 0.90
DOMAIN_SEMANTIC_THRESHOLD = 0.86

# Solo il 25% dell'urgency_boost configurato
# entra direttamente nell'urgenza.
TOPIC_URGENCY_MULTIPLIER = 0.25

def _embedding_to_string(
    embedding: list[float],
) -> str:
    return (
        "["
        + ",".join(
            str(value)
            for value in embedding
        )
        + "]"
    )


def _get_topic_story_similarity(
    *,
    engine,
    story_id: int,
    topic: str,
) -> float | None:

    topic_embedding = embed_story(
        title=topic,
        summary="",
    )

    embedding_string = (
        _embedding_to_string(
            topic_embedding
        )
    )

    with engine.connect() as connection:

        row = connection.execute(
            text("""
                SELECT
                    1 - (
                        embedding <=>
                        CAST(
                            :embedding
                            AS vector
                        )
                    ) AS similarity

                FROM story_embeddings

                WHERE story_id = :story_id

                LIMIT 1
            """),
            {
                "story_id": story_id,
                "embedding": embedding_string,
            },
        ).mappings().first()

    if not row:
        return None

    if row["similarity"] is None:
        return None

    return round(
        float(row["similarity"]),
        4,
    )

def _normalize_word(word: str) -> str:
    """
    Very small Portuguese lexical normalizer.

    It is intentionally conservative: its purpose is only to avoid missing
    obvious plural/orthographic variants, not to perform linguistic stemming.
    """
    word = word.strip().lower()

    if len(word) <= 3:
        return word

    # Common Portuguese plural transformations after accent removal.
    if len(word) > 5 and word.endswith("oes"):
        return word[:-3] + "ao"

    if len(word) > 5 and word.endswith("aes"):
        return word[:-3] + "ao"

    if len(word) > 5 and word.endswith("ais"):
        return word[:-3] + "al"

    if len(word) > 5 and word.endswith("eis"):
        return word[:-3] + "el"

    if len(word) > 5 and word.endswith("is"):
        # Avoid aggressive conversion; only remove final plural s.
        return word[:-1]

    if len(word) > 4 and word.endswith("s"):
        return word[:-1]

    return word


def _normalize_text(value: str | None) -> str:
    value = value or ""

    value = unicodedata.normalize(
        "NFKD",
        value,
    )

    value = "".join(
        ch
        for ch in value
        if not unicodedata.combining(ch)
    )

    value = value.lower()

    # Keep letters/numbers, turn punctuation into spaces.
    value = re.sub(
        r"[^a-z0-9]+",
        " ",
        value,
    )

    tokens = [
        _normalize_word(token)
        for token in value.split()
        if token
    ]

    return " ".join(tokens).strip()


def _topic_matches(
    search_text: str,
    topic: str,
) -> bool:
    normalized_search = _normalize_text(
        search_text
    )

    normalized_topic = _normalize_text(
        topic
    )

    if not normalized_topic:
        return False

    # Acronyms / very short signals need word boundaries.
    if len(normalized_topic) <= 4:
        pattern = (
            rf"(?<!\w)"
            rf"{re.escape(normalized_topic)}"
            rf"(?!\w)"
        )

        return (
            re.search(
                pattern,
                normalized_search,
            )
            is not None
        )

    # For multi-word domain concepts, token-normalized phrase matching
    # tolerates accents and simple singular/plural differences.
    return (
        normalized_topic
        in normalized_search
    )


def _priority_value(priority_score) -> float:
    if priority_score is None:
        return 0.0

    try:
        return max(
            0.0,
            min(1.0, float(priority_score)),
        )
    except (TypeError, ValueError):
        return 0.0


def _calculate_relevance(
    matched_topics: list[dict],
) -> float:

    if not matched_topics:
        return 0.0

    contributions = []

    for item in matched_topics:

        weight = max(
            0.0,
            min(
                1.0,
                float(
                    item.get("weight")
                    or 0.0
                ),
            ),
        )

        direct_match = bool(
            item.get(
                "direct_match"
            )
            or item.get(
                "keyword_match"
            )
        )

        domain_match = bool(
            item.get(
                "domain_match"
            )
        )

        semantic_similarity = float(
            item.get(
                "semantic_similarity"
            )
            or 0.0
        )

        # Direct/entity match = strongest.
        if direct_match:

            strength = 0.78

        # Domain term + semantic confirmation = relevant,
        # but slightly weaker than a direct match.
        elif (
            domain_match
            and semantic_similarity
            >= DOMAIN_SEMANTIC_THRESHOLD
        ):

            normalized = (
                semantic_similarity
                - DOMAIN_SEMANTIC_THRESHOLD
            ) / (
                1.0
                - DOMAIN_SEMANTIC_THRESHOLD
            )

            normalized = max(
                0.0,
                min(
                    1.0,
                    normalized,
                ),
            )

            strength = (
                0.60
                + 0.12 * normalized
            )

        else:

            strength = 0.0

        contributions.append(
            strength * weight
        )

    strongest = max(
        contributions,
        default=0.0,
    )

    additional_matches = max(
        0,
        len(contributions) - 1,
    )

    score = (
        strongest
        + min(
            0.25,
            additional_matches * 0.08,
        )
    )

    return round(
        min(1.0, score),
        4,
    )

def _load_story_change(
    engine,
    story_id: int,
) -> dict:
    with engine.connect() as connection:
        row = connection.execute(
            text("""
                SELECT
                    has_meaningful_change,
                    new_information,
                    new_actor,
                    new_measure,
                    status_change,
                    date_change,
                    quantitative_change,
                    contradiction

                FROM story_changes

                WHERE story_id = :story_id

                LIMIT 1
            """),
            {
                "story_id": story_id,
            },
        ).mappings().first()

    if not row:
        return {
            "meaningful_change_score": 0.0,
            "new_information_score": 0.0,
            "new_actor_score": 0.0,
            "new_measure_score": 0.0,
            "status_change_score": 0.0,
            "date_change_score": 0.0,
            "quantitative_change_score": 0.0,
            "contradiction_score": 0.0,
        }

    return {
        "meaningful_change_score": float(
            row["has_meaningful_change"]
            or 0.0
        ),
        "new_information_score": float(
            row["new_information"]
            or 0.0
        ),
        "new_actor_score": float(
            row["new_actor"]
            or 0.0
        ),
        "new_measure_score": float(
            row["new_measure"]
            or 0.0
        ),
        "status_change_score": float(
            row["status_change"]
            or 0.0
        ),
        "date_change_score": float(
            row["date_change"]
            or 0.0
        ),
        "quantitative_change_score": float(
            row["quantitative_change"]
            or 0.0
        ),
        "contradiction_score": float(
            row["contradiction"]
            or 0.0
        ),
    }


def _calculate_urgency(
    *,
    profile: dict,
    story: dict,
    relevance_score: float,
    change: dict,
    matched_topics: list[dict],
) -> tuple[float, list[dict]]:
    priority_score = _priority_value(
        story.get("priority_score")
    )

    meaningful_change = float(
        change.get(
            "meaningful_change_score",
            0.0,
        )
        or 0.0
    )

    score = (
        0.35 * priority_score
        + 0.45 * relevance_score
        + 0.20 * meaningful_change
    )

    reasons = [
        {
            "type": "priority",
            "score": round(priority_score, 4),
        },
        {
            "type": "relevance",
            "score": round(relevance_score, 4),
        },
        {
            "type": "meaningful_change",
            "score": round(
                meaningful_change,
                4,
            ),
        },
    ]

    configured_topic_boost = max(
        [
            float(
                item.get(
                    "urgency_boost"
                )
                or 0.0
            )
            for item in matched_topics
        ],
        default=0.0,
    )

    effective_topic_boost = (
        configured_topic_boost
        * TOPIC_URGENCY_MULTIPLIER
    )

    if effective_topic_boost > 0:
        score += effective_topic_boost

        reasons.append(
            {
                "type": "topic_urgency_boost",
                "configured": round(
                    configured_topic_boost,
                    4,
                ),
                "effective_boost": round(
                    effective_topic_boost,
                    4,
                ),
            }
        )

    if (
        profile.get(
            "alert_on_status_change"
        )
        and change.get(
            "status_change_score",
            0.0,
        ) >= 0.60
    ):
        score += 0.10
        reasons.append(
            {
                "type": "status_change",
                "score": round(
                    float(
                        change[
                            "status_change_score"
                        ]
                    ),
                    4,
                ),
                "boost": 0.10,
            }
        )

    if (
        profile.get(
            "alert_on_new_measure"
        )
        and change.get(
            "new_measure_score",
            0.0,
        ) >= 0.60
    ):
        score += 0.10
        reasons.append(
            {
                "type": "new_measure",
                "score": round(
                    float(
                        change[
                            "new_measure_score"
                        ]
                    ),
                    4,
                ),
                "boost": 0.10,
            }
        )

    if (
        profile.get(
            "alert_on_date_change"
        )
        and change.get(
            "date_change_score",
            0.0,
        ) >= 0.60
    ):
        score += 0.08
        reasons.append(
            {
                "type": "date_change",
                "score": round(
                    float(
                        change[
                            "date_change_score"
                        ]
                    ),
                    4,
                ),
                "boost": 0.08,
            }
        )

    if (
        profile.get(
            "alert_on_contradiction"
        )
        and change.get(
            "contradiction_score",
            0.0,
        ) >= 0.70
    ):
        score += 0.15
        reasons.append(
            {
                "type": "contradiction",
                "score": round(
                    float(
                        change[
                            "contradiction_score"
                        ]
                    ),
                    4,
                ),
                "boost": 0.15,
            }
        )

    return (
        round(
            min(1.0, score),
            4,
        ),
        reasons,
    )



def _save_monitoring_alert(
    *,
    engine,
    profile_id: int,
    story_id: int,
    relevance_score: float,
    urgency_score: float,
    matched_topics: list[dict],
    reasons: list[dict],
) -> None:
    """
    Persists a client-specific alert.

    The unique(profile_id, story_id) constraint prevents duplicate alerts
    for the same monitoring profile and story. Re-evaluations refresh the
    scores and diagnostic data without resetting an existing alert status.
    """
    with engine.begin() as connection:
        connection.execute(
            text("""
                INSERT INTO monitoring_alerts (
                    profile_id,
                    story_id,
                    relevance_score,
                    urgency_score,
                    matched_topics,
                    reasons,
                    status,
                    created_at,
                    updated_at
                )

                VALUES (
                    :profile_id,
                    :story_id,
                    :relevance_score,
                    :urgency_score,
                    CAST(:matched_topics AS JSONB),
                    CAST(:reasons AS JSONB),
                    'new',
                    NOW(),
                    NOW()
                )

                ON CONFLICT (
                    profile_id,
                    story_id
                )

                DO UPDATE SET
                    relevance_score =
                        EXCLUDED.relevance_score,

                    urgency_score =
                        EXCLUDED.urgency_score,

                    matched_topics =
                        EXCLUDED.matched_topics,

                    reasons =
                        EXCLUDED.reasons,

                    updated_at = NOW()
            """),
            {
                "profile_id": profile_id,
                "story_id": story_id,
                "relevance_score": relevance_score,
                "urgency_score": urgency_score,
                "matched_topics": json.dumps(
                    matched_topics,
                    ensure_ascii=False,
                ),
                "reasons": json.dumps(
                    reasons,
                    ensure_ascii=False,
                ),
            },
        )


def get_monitoring_alerts(
    *,
    engine,
    profile_id: int | None = None,
    status: str | None = None,
    limit: int = 50,
) -> dict:
    """
    Lists persisted client-specific alerts.
    """
    limit = max(
        1,
        min(
            200,
            int(limit),
        ),
    )

    clauses = []
    params = {
        "limit": limit,
    }

    if profile_id is not None:
        clauses.append(
            "a.profile_id = :profile_id"
        )
        params["profile_id"] = profile_id

    if status:
        clauses.append(
            "a.status = :status"
        )
        params["status"] = status

    where_sql = ""

    if clauses:
        where_sql = (
            "WHERE "
            + " AND ".join(clauses)
        )

    query = text(
        f"""
            SELECT
                a.id,
                a.profile_id,
                p.name AS profile_name,
                a.story_id,
                s.title,
                s.summary,
                s.source,
                s.category,
                s.priority,
                s.priority_score,
                s.published_at,
                a.relevance_score,
                a.urgency_score,
                a.matched_topics,
                a.reasons,
                a.status,
                a.created_at,
                a.updated_at

            FROM monitoring_alerts a

            JOIN monitoring_profiles p
                ON p.id = a.profile_id

            JOIN stories s
                ON s.id = a.story_id

            {where_sql}

            ORDER BY
                a.created_at DESC,
                a.id DESC

            LIMIT :limit
        """
    )

    with engine.connect() as connection:
        rows = connection.execute(
            query,
            params,
        ).mappings().all()

    return {
        "success": True,
        "count": len(rows),
        "alerts": [
            {
                "id": row["id"],
                "profile": {
                    "id": row["profile_id"],
                    "name": row["profile_name"],
                },
                "story": {
                    "id": row["story_id"],
                    "title": row["title"],
                    "summary": row["summary"],
                    "source": row["source"],
                    "category": row["category"],
                    "priority": row["priority"],
                    "priority_score": (
                        float(
                            row["priority_score"]
                        )
                        if row["priority_score"] is not None
                        else 0.0
                    ),
                    "published_at": row["published_at"],
                },
                "relevance_score": float(
                    row["relevance_score"]
                ),
                "urgency_score": float(
                    row["urgency_score"]
                ),
                "matched_topics": (
                    row["matched_topics"]
                    or []
                ),
                "reasons": (
                    row["reasons"]
                    or []
                ),
                "status": row["status"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        ],
    }

def evaluate_story_for_profile(
    *,
    engine,
    story_id: int,
    profile_id: int,
    create_alert: bool = True,
) -> dict:
    with engine.connect() as connection:
        story = connection.execute(
            text("""
                SELECT
                    id,
                    title,
                    summary,
                    source,
                    category,
                    priority,
                    priority_score,
                    published_at,
                    discovered_at

                FROM stories

                WHERE id = :story_id

                LIMIT 1
            """),
            {
                "story_id": story_id,
            },
        ).mappings().first()

        profile = connection.execute(
            text("""
                SELECT
                    id,
                    name,
                    description,
                    enabled,
                    min_relevance_score,
                    min_urgency_score,
                    alert_on_status_change,
                    alert_on_new_measure,
                    alert_on_date_change,
                    alert_on_contradiction

                FROM monitoring_profiles

                WHERE id = :profile_id

                LIMIT 1
            """),
            {
                "profile_id": profile_id,
            },
        ).mappings().first()

        topics = connection.execute(
            text("""
                SELECT
                    id,
                    topic,
                    semantic_description,
                    direct_terms,
                    domain_terms,
                    expanded_terms,
                    weight,
                    urgency_boost

                FROM monitoring_topics

                WHERE
                    profile_id = :profile_id
                    AND enabled = TRUE

                ORDER BY id ASC
            """),
            {
                "profile_id": profile_id,
            },
        ).mappings().all()

    if not story:
        return {
            "success": False,
            "reason": "story_not_found",
            "story_id": story_id,
        }

    if not profile:
        return {
            "success": False,
            "reason": "profile_not_found",
            "profile_id": profile_id,
        }

    profile = dict(profile)

    if not profile["enabled"]:
        return {
            "success": True,
            "matched": False,
            "reason": "profile_disabled",
            "story_id": story_id,
            "profile_id": profile_id,
        }

    search_text = _normalize_text(
        f"{story['title'] or ''} "
        f"{story['summary'] or ''}"
    )

    matched_topics = []
    topic_diagnostics = []

    for topic_row in topics:
        topic_row = dict(topic_row)

        topic = topic_row["topic"]

        # -------------------------------------------------
        # DIRECT TERMS
        # Exact names / acronyms / official equivalents.
        # A direct hit is sufficient for a strong match.
        # -------------------------------------------------
        direct_terms = (
            topic_row.get(
                "direct_terms"
            )
            or []
        )

        if not isinstance(
            direct_terms,
            list,
        ):
            direct_terms = []

        # Safety / backwards compatibility:
        # the original user topic is always a direct signal.
        direct_candidates = [
            topic
        ] + [
            term
            for term in direct_terms
            if isinstance(
                term,
                str,
            )
        ]

        direct_term_matches = []

        seen_direct = set()

        for term in direct_candidates:
            key = (
                term.strip().casefold()
                if isinstance(
                    term,
                    str,
                )
                else ""
            )

            if (
                not key
                or key in seen_direct
            ):
                continue

            seen_direct.add(key)

            if _topic_matches(
                search_text,
                term,
            ):
                direct_term_matches.append(
                    term
                )

        direct_match = bool(
            direct_term_matches
        )

        # -------------------------------------------------
        # DOMAIN TERMS
        # Specific subjects inside the topic's competence/domain.
        # They need semantic confirmation.
        # -------------------------------------------------
        domain_terms = (
            topic_row.get(
                "domain_terms"
            )
            or []
        )

        if not isinstance(
            domain_terms,
            list,
        ):
            domain_terms = []

        domain_term_matches = [
            term
            for term in domain_terms
            if (
                isinstance(
                    term,
                    str,
                )
                and _topic_matches(
                    search_text,
                    term,
                )
            )
        ]

        semantic_query = (
            topic_row.get(
                "semantic_description"
            )
            or topic
        )

        semantic_similarity = (
            _get_topic_story_similarity(
                engine=engine,
                story_id=story_id,
                topic=semantic_query,
            )
        )

        domain_semantic_passed = (
            semantic_similarity
            is not None
            and semantic_similarity
            >= DOMAIN_SEMANTIC_THRESHOLD
        )

        domain_match = (
            bool(domain_term_matches)
            and domain_semantic_passed
        )

        # Semantic similarity alone never creates relevance.
        matched = (
            direct_match
            or domain_match
        )

        topic_diagnostics.append(
            {
                "topic_id": (
                    topic_row["id"]
                ),
                "topic": topic,
                "semantic_query": (
                    semantic_query
                ),
                "direct_terms": (
                    direct_terms
                ),
                "direct_term_matches": (
                    direct_term_matches
                ),
                "direct_match": (
                    direct_match
                ),
                "domain_terms": (
                    domain_terms
                ),
                "domain_term_matches": (
                    domain_term_matches
                ),
                "semantic_similarity": (
                    semantic_similarity
                ),
                "domain_semantic_threshold": (
                    DOMAIN_SEMANTIC_THRESHOLD
                ),
                "domain_semantic_passed": (
                    domain_semantic_passed
                ),
                "domain_match": (
                    domain_match
                ),
                "matched": matched,
            }
        )

        if not matched:
            continue

        if direct_match and domain_match:
            match_type = "hybrid"

        elif direct_match:
            match_type = "direct"

        else:
            match_type = "domain"

        matched_topics.append(
            {
                "topic_id": (
                    topic_row["id"]
                ),
                "topic": topic,
                "semantic_query": (
                    semantic_query
                ),
                "direct_term_matches": (
                    direct_term_matches
                ),
                "domain_term_matches": (
                    domain_term_matches
                ),
                "direct_match": (
                    direct_match
                ),
                "domain_match": (
                    domain_match
                ),
                "weight": float(
                    topic_row["weight"]
                    or 0.0
                ),
                "urgency_boost": float(
                    topic_row[
                        "urgency_boost"
                    ]
                    or 0.0
                ),
                "match_type": (
                    match_type
                ),
                "keyword_match": (
                    direct_match
                ),
                "semantic_similarity": (
                    semantic_similarity
                ),
            }
        )

    relevance_score = (
        _calculate_relevance(
            matched_topics
        )
    )

    change = _load_story_change(
        engine,
        story_id,
    )

    urgency_score, reasons = (
        _calculate_urgency(
            profile=profile,
            story=dict(story),
            relevance_score=(
                relevance_score
            ),
            change=change,
            matched_topics=(
                matched_topics
            ),
        )
    )

    relevance_passed = (
        relevance_score
        >= float(
            profile[
                "min_relevance_score"
            ]
        )
    )

    urgency_passed = (
        urgency_score
        >= float(
            profile[
                "min_urgency_score"
            ]
        )
    )

    matched = (
        bool(matched_topics)
        and relevance_passed
    )

    should_alert = (
        matched
        and urgency_passed
    )

    alert_persisted = False

    if should_alert and create_alert:
        _save_monitoring_alert(
            engine=engine,
            profile_id=profile_id,
            story_id=story_id,
            relevance_score=relevance_score,
            urgency_score=urgency_score,
            matched_topics=matched_topics,
            reasons=reasons,
        )
        alert_persisted = True

    if matched:
        with engine.begin() as connection:
            connection.execute(
                text("""
                    INSERT INTO monitoring_matches (
                        profile_id,
                        story_id,
                        relevance_score,
                        urgency_score,
                        matched_topics,
                        reasons,
                        created_at
                    )

                    VALUES (
                        :profile_id,
                        :story_id,
                        :relevance_score,
                        :urgency_score,
                        CAST(
                            :matched_topics
                            AS JSONB
                        ),
                        CAST(
                            :reasons
                            AS JSONB
                        ),
                        NOW()
                    )

                    ON CONFLICT (
                        profile_id,
                        story_id
                    )

                    DO UPDATE SET
                        relevance_score =
                            EXCLUDED.relevance_score,

                        urgency_score =
                            EXCLUDED.urgency_score,

                        matched_topics =
                            EXCLUDED.matched_topics,

                        reasons =
                            EXCLUDED.reasons,

                        created_at = NOW()
                """),
                {
                    "profile_id": profile_id,
                    "story_id": story_id,
                    "relevance_score": (
                        relevance_score
                    ),
                    "urgency_score": (
                        urgency_score
                    ),
                    "matched_topics": (
                        json.dumps(
                            matched_topics,
                            ensure_ascii=False,
                        )
                    ),
                    "reasons": (
                        json.dumps(
                            reasons,
                            ensure_ascii=False,
                        )
                    ),
                },
            )

    return {
        "success": True,
        "matched": matched,
        "should_alert": should_alert,
        "alert_persisted": alert_persisted,

        "profile": {
            "id": profile["id"],
            "name": profile["name"],
        },

        "story": {
            "id": story["id"],
            "title": story["title"],
            "source": story["source"],
            "category": story["category"],
            "priority": story["priority"],
            "priority_score": (
                float(
                    story["priority_score"]
                )
                if story[
                    "priority_score"
                ]
                is not None
                else 0.0
            ),
        },

        "relevance_score": (
            relevance_score
        ),

        "urgency_score": (
            urgency_score
        ),

        "thresholds": {
            "min_relevance_score": (
                float(
                    profile[
                        "min_relevance_score"
                    ]
                )
            ),

            "min_urgency_score": (
                float(
                    profile[
                        "min_urgency_score"
                    ]
                )
            ),

            "semantic_topic_threshold": (
                SEMANTIC_TOPIC_THRESHOLD
            ),
        },

        "matched_topics": (
            matched_topics
        ),

        "topic_diagnostics": (
            topic_diagnostics
        ),

        "change_signals": (
            change
        ),

        "reasons": reasons,
    }


def evaluate_story_for_all_profiles(
    *,
    engine,
    story_id: int,
) -> dict:
    with engine.connect() as connection:
        profiles = connection.execute(
            text("""
                SELECT id

                FROM monitoring_profiles

                WHERE enabled = TRUE

                ORDER BY id ASC
            """)
        ).mappings().all()

    results = [
        evaluate_story_for_profile(
            engine=engine,
            story_id=story_id,
            profile_id=row["id"],
        )
        for row in profiles
    ]

    return {
        "story_id": story_id,
        "profiles_evaluated": (
            len(results)
        ),
        "matches": [
            result
            for result in results
            if result.get("matched")
        ],
        "alerts": [
            result
            for result in results
            if result.get(
                "should_alert"
            )
        ],
        "results": results,
    }



# =========================================================
# HISTORICAL PROFILE BACKFILL
# =========================================================

def backfill_monitoring_profile(
    *,
    engine,
    profile_id: int,
    days: int = 30,
    limit: int = 1000,
) -> dict:
    """
    Re-evaluates recent historical stories for one monitoring profile.

    Historical evaluation:
    - creates/updates monitoring_matches
    - calculates whether each item requires attention
    - DOES NOT create monitoring_alerts
    - therefore DOES NOT trigger retroactive Telegram delivery

    This is intentionally synchronous for the MVP. It can later be moved
    to a background job if the number of stories grows substantially.
    """
    days = max(1, min(365, int(days)))
    limit = max(1, min(5000, int(limit)))

    with engine.connect() as connection:
        profile = connection.execute(
            text("""
                SELECT
                    id,
                    name,
                    enabled,
                    min_urgency_score
                FROM monitoring_profiles
                WHERE id = :profile_id
                LIMIT 1
            """),
            {"profile_id": profile_id},
        ).mappings().first()

        if not profile:
            return {
                "success": False,
                "reason": "profile_not_found",
                "profile_id": profile_id,
            }

        topic_count = connection.execute(
            text("""
                SELECT COUNT(*)
                FROM monitoring_topics
                WHERE
                    profile_id = :profile_id
                    AND enabled = TRUE
            """),
            {"profile_id": profile_id},
        ).scalar_one()

        if not topic_count:
            return {
                "success": False,
                "reason": "profile_has_no_enabled_topics",
                "profile_id": profile_id,
                "days": days,
            }

        story_rows = connection.execute(
            text("""
                SELECT id
                FROM stories
                WHERE
                    COALESCE(
                        published_at,
                        discovered_at
                    )
                    >= NOW() - (:days * INTERVAL '1 day')
                ORDER BY
                    COALESCE(
                        published_at,
                        discovered_at
                    ) DESC,
                    id DESC
                LIMIT :limit
            """),
            {
                "days": days,
                "limit": limit,
            },
        ).mappings().all()

    story_ids = [
        int(row["id"])
        for row in story_rows
    ]

    # Rebuild matches only for the requested historical window.
    # Existing live alert records are deliberately left untouched.
    with engine.begin() as connection:
        connection.execute(
            text("""
                DELETE FROM monitoring_matches
                WHERE
                    profile_id = :profile_id
                    AND story_id IN (
                        SELECT id
                        FROM stories
                        WHERE
                            COALESCE(
                                published_at,
                                discovered_at
                            )
                            >= NOW() - (
                                :days * INTERVAL '1 day'
                            )
                    )
            """),
            {
                "profile_id": profile_id,
                "days": days,
            },
        )

    evaluated = 0
    matched = 0
    requires_attention = 0
    errors = []

    for story_id in story_ids:
        try:
            result = evaluate_story_for_profile(
                engine=engine,
                story_id=story_id,
                profile_id=profile_id,
                create_alert=False,
            )

            evaluated += 1

            if result.get("matched"):
                matched += 1

            if result.get("should_alert"):
                requires_attention += 1

        except Exception as exc:
            errors.append(
                {
                    "story_id": story_id,
                    "error": str(exc),
                }
            )

    return {
        "success": True,
        "profile": {
            "id": int(profile["id"]),
            "name": profile["name"],
        },
        "days": days,
        "stories_found": len(story_ids),
        "stories_evaluated": evaluated,
        "matches": matched,
        "requires_attention": requires_attention,
        "alerts_created": 0,
        "retroactive_notifications": False,
        "errors": errors,
    }


# =========================================================
# CALIBRATION REPORT
# =========================================================

def get_topic_calibration_report(
    *,
    engine,
    topic_id: int,
    limit: int = 30,
) -> dict:
    """
    Ranks existing stories by semantic similarity against one monitoring
    topic. Useful for calibrating SEMANTIC_TOPIC_THRESHOLD with real data.

    The report does not modify monitoring matches or alerts.
    """
    limit = max(
        1,
        min(
            200,
            int(limit),
        ),
    )

    with engine.connect() as connection:
        topic_row = connection.execute(
            text("""
                SELECT
                    id,
                    profile_id,
                    topic,
                    semantic_description,
                    weight,
                    urgency_boost,
                    enabled

                FROM monitoring_topics

                WHERE id = :topic_id

                LIMIT 1
            """),
            {
                "topic_id": topic_id,
            },
        ).mappings().first()

    if not topic_row:
        return {
            "success": False,
            "reason": "topic_not_found",
            "topic_id": topic_id,
        }

    topic_row = dict(topic_row)

    semantic_query = (
        topic_row.get(
            "semantic_description"
        )
        or topic_row["topic"]
    )

    topic_embedding = embed_story(
        title=semantic_query,
        summary="",
    )

    topic_embedding_string = (
        _embedding_to_string(
            topic_embedding
        )
    )

    with engine.connect() as connection:
        rows = connection.execute(
            text("""
                SELECT
                    s.id,
                    s.title,
                    s.summary,
                    s.source,
                    s.category,
                    s.priority,
                    s.priority_score,
                    s.published_at,
                    s.discovered_at,

                    1 - (
                        e.embedding <=>
                        CAST(
                            :topic_embedding
                            AS vector
                        )
                    ) AS semantic_similarity

                FROM story_embeddings e

                JOIN stories s
                    ON s.id = e.story_id

                ORDER BY
                    e.embedding <=>
                    CAST(
                        :topic_embedding
                        AS vector
                    )

                LIMIT :limit
            """),
            {
                "topic_embedding": (
                    topic_embedding_string
                ),
                "limit": limit,
            },
        ).mappings().all()

    results = []

    above_threshold = 0
    keyword_matches = 0
    semantic_only_matches = 0

    for row in rows:
        row = dict(row)

        similarity = round(
            float(
                row[
                    "semantic_similarity"
                ]
                or 0.0
            ),
            4,
        )

        search_text = _normalize_text(
            f"{row['title'] or ''} "
            f"{row['summary'] or ''}"
        )

        keyword_match = (
            _topic_matches(
                search_text,
                topic_row["topic"],
            )
        )

        semantic_match = (
            similarity
            >= SEMANTIC_TOPIC_THRESHOLD
        )

        if semantic_match:
            above_threshold += 1

        if keyword_match:
            keyword_matches += 1

        if (
            semantic_match
            and not keyword_match
        ):
            semantic_only_matches += 1

        results.append(
            {
                "story_id": row["id"],
                "title": row["title"],
                "summary": row["summary"],
                "source": row["source"],
                "category": row["category"],
                "priority": row["priority"],
                "priority_score": (
                    float(
                        row[
                            "priority_score"
                        ]
                    )
                    if row[
                        "priority_score"
                    ]
                    is not None
                    else 0.0
                ),
                "published_at": (
                    row["published_at"]
                ),
                "discovered_at": (
                    row["discovered_at"]
                ),
                "semantic_similarity": (
                    similarity
                ),
                "keyword_match": (
                    keyword_match
                ),
                "semantic_match": (
                    semantic_match
                ),
                "match_type": (
                    "hybrid"
                    if (
                        keyword_match
                        and semantic_match
                    )
                    else (
                        "keyword"
                        if keyword_match
                        else (
                            "semantic"
                            if semantic_match
                            else "none"
                        )
                    )
                ),
            }
        )

    return {
        "success": True,

        "topic": {
            "id": topic_row["id"],
            "profile_id": (
                topic_row["profile_id"]
            ),
            "name": topic_row["topic"],
            "semantic_query": (
                semantic_query
            ),
            "threshold": (
                SEMANTIC_TOPIC_THRESHOLD
            ),
        },

        "summary": {
            "stories_returned": (
                len(results)
            ),
            "above_threshold": (
                above_threshold
            ),
            "keyword_matches": (
                keyword_matches
            ),
            "semantic_only_matches": (
                semantic_only_matches
            ),
        },

        "results": results,
    }


# =========================================================
# DAILY / PERIOD DIGEST
# =========================================================

def get_monitoring_digest(
    *,
    engine,
    profile_id: int,
    hours: int = 24,
    limit: int = 50,
) -> dict:
    """
    Builds a client-specific digest from monitoring_matches.

    The digest includes all relevant stories matched for the profile
    during the requested time window. Stories that also generated an
    immediate personalized alert are marked with is_alert=True.
    """
    hours = max(
        1,
        min(
            168,
            int(hours),
        ),
    )

    limit = max(
        1,
        min(
            200,
            int(limit),
        ),
    )

    with engine.connect() as connection:
        profile = connection.execute(
            text("""
                SELECT
                    id,
                    name,
                    description,
                    enabled,
                    min_relevance_score,
                    min_urgency_score

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

    with engine.connect() as connection:
        rows = connection.execute(
            text("""
                SELECT
                    m.id AS match_id,
                    m.story_id,
                    m.relevance_score,
                    m.urgency_score,
                    m.matched_topics,
                    m.reasons,
                    m.created_at AS matched_at,

                    s.title,
                    s.summary,
                    s.source,
                    s.category,
                    s.priority,
                    s.priority_score,
                    s.published_at,

                    a.id AS alert_id,
                    a.status AS alert_status

                FROM monitoring_matches m

                JOIN stories s
                    ON s.id = m.story_id

                LEFT JOIN monitoring_alerts a
                    ON a.profile_id = m.profile_id
                    AND a.story_id = m.story_id

                WHERE
                    m.profile_id = :profile_id
                    AND m.created_at >= (
                        NOW()
                        - make_interval(
                            hours => :hours
                        )
                    )

                ORDER BY
                    CASE
                        WHEN a.id IS NOT NULL
                        THEN 1
                        ELSE 0
                    END DESC,

                    m.urgency_score DESC,
                    m.relevance_score DESC,
                    m.created_at DESC

                LIMIT :limit
            """),
            {
                "profile_id": profile_id,
                "hours": hours,
                "limit": limit,
            },
        ).mappings().all()

    items = []

    alert_count = 0
    relevant_only_count = 0

    categories = {}
    topics = {}

    for row in rows:
        row = dict(row)

        is_alert = (
            row["alert_id"] is not None
        )

        if is_alert:
            alert_count += 1
        else:
            relevant_only_count += 1

        category = (
            row["category"]
            or "Sem categoria"
        )

        categories[category] = (
            categories.get(
                category,
                0,
            )
            + 1
        )

        matched_topics = (
            row["matched_topics"]
            or []
        )

        for topic in matched_topics:
            topic_name = topic.get(
                "topic"
            )

            if topic_name:
                topics[topic_name] = (
                    topics.get(
                        topic_name,
                        0,
                    )
                    + 1
                )

        items.append(
            {
                "match_id": row["match_id"],

                "story": {
                    "id": row["story_id"],
                    "title": row["title"],
                    "summary": row["summary"],
                    "source": row["source"],
                    "category": row["category"],
                    "priority": row["priority"],
                    "priority_score": (
                        float(
                            row[
                                "priority_score"
                            ]
                        )
                        if row[
                            "priority_score"
                        ]
                        is not None
                        else 0.0
                    ),
                    "published_at": (
                        row["published_at"]
                    ),
                },

                "relevance_score": (
                    float(
                        row[
                            "relevance_score"
                        ]
                    )
                ),

                "urgency_score": (
                    float(
                        row[
                            "urgency_score"
                        ]
                    )
                ),

                "matched_topics": (
                    matched_topics
                ),

                "reasons": (
                    row["reasons"]
                    or []
                ),

                "is_alert": is_alert,

                "alert": (
                    {
                        "id": row["alert_id"],
                        "status": (
                            row["alert_status"]
                        ),
                    }
                    if is_alert
                    else None
                ),

                "matched_at": (
                    row["matched_at"]
                ),
            }
        )

    top_categories = [
        {
            "category": key,
            "count": value,
        }
        for key, value in sorted(
            categories.items(),
            key=lambda item: (
                -item[1],
                item[0],
            ),
        )
    ]

    top_topics = [
        {
            "topic": key,
            "count": value,
        }
        for key, value in sorted(
            topics.items(),
            key=lambda item: (
                -item[1],
                item[0],
            ),
        )
    ]

    return {
        "success": True,

        "profile": {
            "id": profile["id"],
            "name": profile["name"],
            "description": (
                profile["description"]
            ),
        },

        "period": {
            "hours": hours,
        },

        "summary": {
            "total_relevant": len(items),
            "immediate_alerts": (
                alert_count
            ),
            "relevant_only": (
                relevant_only_count
            ),
            "top_categories": (
                top_categories[:5]
            ),
            "top_topics": (
                top_topics[:10]
            ),
        },

        "items": items,
    }


# =========================================================
# CLIENT BRIEFING
# =========================================================

def _format_score(value: float) -> str:
    return f"{round(float(value) * 100)}%"


def get_monitoring_briefing(
    *,
    engine,
    profile_id: int,
    hours: int = 24,
    limit: int = 50,
) -> dict:
    """
    Builds a human-readable client briefing from the monitoring digest.

    This version is deterministic and does not call an LLM.
    It is intended as the presentation layer for the MVP.
    """
    digest = get_monitoring_digest(
        engine=engine,
        profile_id=profile_id,
        hours=hours,
        limit=limit,
    )

    if not digest.get("success"):
        return digest

    profile = digest["profile"]
    summary = digest["summary"]
    items = digest["items"]

    urgent_items = [
        item
        for item in items
        if item.get("is_alert")
    ]

    relevant_items = [
        item
        for item in items
        if not item.get("is_alert")
    ]

    lines = []

    lines.append(
        f"Briefing de monitoramento — {profile['name']}"
    )
    lines.append(
        f"Período analisado: últimas {hours} horas"
    )
    lines.append("")

    lines.append(
        (
            f"Foram identificados {summary['total_relevant']} "
            f"desenvolvimentos relevantes, sendo "
            f"{summary['immediate_alerts']} de atenção imediata "
            f"e {summary['relevant_only']} para acompanhamento."
        )
    )

    top_topics = summary.get("top_topics") or []

    if top_topics:
        topic_text = ", ".join(
            (
                f"{item['topic']} "
                f"({item['count']})"
            )
            for item in top_topics[:5]
        )
        lines.append(
            f"Temas em destaque: {topic_text}."
        )

    lines.append("")

    if urgent_items:
        lines.append("ATENÇÃO IMEDIATA")
        lines.append("")

        for item in urgent_items:
            story = item["story"]

            lines.append(
                f"• {story['title']} — {story['source']}"
            )
            lines.append(
                story["summary"] or "Sem resumo disponível."
            )
            lines.append(
                (
                    "  Relevância: "
                    f"{_format_score(item['relevance_score'])} | "
                    "Urgência: "
                    f"{_format_score(item['urgency_score'])}"
                )
            )

            matched_topics = (
                item.get("matched_topics")
                or []
            )

            if matched_topics:
                topic_names = ", ".join(
                    topic.get("topic", "")
                    for topic in matched_topics
                    if topic.get("topic")
                )

                if topic_names:
                    lines.append(
                        f"  Temas: {topic_names}"
                    )

            lines.append("")

    if relevant_items:
        lines.append("ACOMPANHAMENTO")
        lines.append("")

        for item in relevant_items:
            story = item["story"]

            lines.append(
                f"• {story['title']} — {story['source']}"
            )
            lines.append(
                story["summary"] or "Sem resumo disponível."
            )
            lines.append(
                (
                    "  Relevância: "
                    f"{_format_score(item['relevance_score'])} | "
                    "Urgência: "
                    f"{_format_score(item['urgency_score'])}"
                )
            )

            matched_topics = (
                item.get("matched_topics")
                or []
            )

            if matched_topics:
                topic_names = ", ".join(
                    topic.get("topic", "")
                    for topic in matched_topics
                    if topic.get("topic")
                )

                if topic_names:
                    lines.append(
                        f"  Temas: {topic_names}"
                    )

            lines.append("")

    if not items:
        lines.append(
            "Nenhum desenvolvimento relevante foi identificado "
            "no período analisado."
        )

    return {
        "success": True,
        "profile": profile,
        "period": digest["period"],
        "summary": summary,
        "briefing_text": "\n".join(lines).strip(),
        "items": items,
    }


# =========================================================
# MONITORING PROFILE MANAGEMENT
# =========================================================

def get_monitoring_profile(
    *,
    engine,
    profile_id: int,
) -> dict:
    """
    Returns one monitoring profile with its active/inactive topics
    and a compact activity summary.
    """
    with engine.connect() as connection:
        profile = connection.execute(
            text("""
                SELECT
                    id,
                    name,
                    description,
                    enabled,
                    min_relevance_score,
                    min_urgency_score,
                    alert_on_status_change,
                    alert_on_new_measure,
                    alert_on_date_change,
                    alert_on_contradiction,
                    created_at,
                    updated_at
                FROM monitoring_profiles
                WHERE id = :profile_id
                LIMIT 1
            """),
            {"profile_id": profile_id},
        ).mappings().first()

        if not profile:
            return {
                "success": False,
                "reason": "profile_not_found",
                "profile_id": profile_id,
            }

        topics = connection.execute(
            text("""
                SELECT
                    id,
                    topic,
                    semantic_description,
                    weight,
                    urgency_boost,
                    enabled,
                    created_at
                FROM monitoring_topics
                WHERE profile_id = :profile_id
                ORDER BY id ASC
            """),
            {"profile_id": profile_id},
        ).mappings().all()

        stats = connection.execute(
            text("""
                SELECT
                    (
                        SELECT COUNT(*)
                        FROM monitoring_matches
                        WHERE profile_id = :profile_id
                    ) AS total_matches,
                    (
                        SELECT COUNT(*)
                        FROM monitoring_alerts
                        WHERE profile_id = :profile_id
                    ) AS total_alerts,
                    (
                        SELECT COUNT(*)
                        FROM monitoring_alerts
                        WHERE profile_id = :profile_id
                          AND status = 'new'
                    ) AS new_alerts
            """),
            {"profile_id": profile_id},
        ).mappings().first()

    return {
        "success": True,
        "profile": dict(profile),
        "topics": [
            {
                **dict(row),
                "weight": float(row["weight"] or 0.0),
                "urgency_boost": float(
                    row["urgency_boost"] or 0.0
                ),
            }
            for row in topics
        ],
        "stats": {
            "total_matches": int(
                stats["total_matches"] or 0
            ),
            "total_alerts": int(
                stats["total_alerts"] or 0
            ),
            "new_alerts": int(
                stats["new_alerts"] or 0
            ),
        },
    }


def update_monitoring_profile(
    *,
    engine,
    profile_id: int,
    values: dict,
) -> dict:
    """
    Partially updates a monitoring profile.
    Only whitelisted fields are accepted.
    """
    allowed = {
        "name",
        "description",
        "enabled",
        "min_relevance_score",
        "min_urgency_score",
        "alert_on_status_change",
        "alert_on_new_measure",
        "alert_on_date_change",
        "alert_on_contradiction",
    }

    updates = {
        key: value
        for key, value in values.items()
        if key in allowed
    }

    if not updates:
        return get_monitoring_profile(
            engine=engine,
            profile_id=profile_id,
        )

    if (
        "min_relevance_score" in updates
        and updates["min_relevance_score"] is not None
    ):
        updates["min_relevance_score"] = max(
            0.0,
            min(
                1.0,
                float(
                    updates[
                        "min_relevance_score"
                    ]
                ),
            ),
        )

    if (
        "min_urgency_score" in updates
        and updates["min_urgency_score"] is not None
    ):
        updates["min_urgency_score"] = max(
            0.0,
            min(
                1.0,
                float(
                    updates[
                        "min_urgency_score"
                    ]
                ),
            ),
        )

    assignments = []

    params = {
        "profile_id": profile_id,
    }

    for key, value in updates.items():
        assignments.append(
            f"{key} = :{key}"
        )
        params[key] = value

    assignments.append(
        "updated_at = NOW()"
    )

    with engine.begin() as connection:
        row = connection.execute(
            text(
                f"""
                    UPDATE monitoring_profiles
                    SET {", ".join(assignments)}
                    WHERE id = :profile_id
                    RETURNING id
                """
            ),
            params,
        ).mappings().first()

    if not row:
        return {
            "success": False,
            "reason": "profile_not_found",
            "profile_id": profile_id,
        }

    return get_monitoring_profile(
        engine=engine,
        profile_id=profile_id,
    )


def delete_monitoring_profile(
    *,
    engine,
    profile_id: int,
) -> dict:
    """
    Deletes a monitoring profile.
    Related topics, matches and monitoring alerts are deleted through
    the database foreign-key cascade configured for the profile.
    """
    with engine.begin() as connection:
        row = connection.execute(
            text("""
                DELETE FROM monitoring_profiles
                WHERE id = :profile_id
                RETURNING id, name
            """),
            {"profile_id": profile_id},
        ).mappings().first()

    if not row:
        return {
            "success": False,
            "reason": "profile_not_found",
            "profile_id": profile_id,
        }

    return {
        "success": True,
        "deleted": True,
        "profile": {
            "id": row["id"],
            "name": row["name"],
        },
    }


def update_monitoring_topic(
    *,
    engine,
    topic_id: int,
    values: dict,
) -> dict:
    """
    Partially updates one monitoring topic.
    """
    allowed = {
        "topic",
        "semantic_description",
        "weight",
        "urgency_boost",
        "enabled",
    }

    updates = {
        key: value
        for key, value in values.items()
        if key in allowed
    }

    if not updates:
        with engine.connect() as connection:
            row = connection.execute(
                text("""
                    SELECT
                        id,
                        profile_id,
                        topic,
                        semantic_description,
                        weight,
                        urgency_boost,
                        enabled,
                        created_at
                    FROM monitoring_topics
                    WHERE id = :topic_id
                    LIMIT 1
                """),
                {"topic_id": topic_id},
            ).mappings().first()

        if not row:
            return {
                "success": False,
                "reason": "topic_not_found",
                "topic_id": topic_id,
            }

        result = dict(row)
        result["weight"] = float(
            result["weight"] or 0.0
        )
        result["urgency_boost"] = float(
            result["urgency_boost"] or 0.0
        )

        return {
            "success": True,
            "topic": result,
        }

    if "weight" in updates:
        updates["weight"] = max(
            0.0,
            min(
                1.0,
                float(
                    updates["weight"]
                ),
            ),
        )

    if "urgency_boost" in updates:
        updates["urgency_boost"] = max(
            0.0,
            min(
                1.0,
                float(
                    updates[
                        "urgency_boost"
                    ]
                ),
            ),
        )

    assignments = []
    params = {
        "topic_id": topic_id,
    }

    for key, value in updates.items():
        assignments.append(
            f"{key} = :{key}"
        )
        params[key] = value

    with engine.begin() as connection:
        row = connection.execute(
            text(
                f"""
                    UPDATE monitoring_topics
                    SET {", ".join(assignments)}
                    WHERE id = :topic_id
                    RETURNING
                        id,
                        profile_id,
                        topic,
                        semantic_description,
                        weight,
                        urgency_boost,
                        enabled,
                        created_at
                """
            ),
            params,
        ).mappings().first()

    if not row:
        return {
            "success": False,
            "reason": "topic_not_found",
            "topic_id": topic_id,
        }

    result = dict(row)
    result["weight"] = float(
        result["weight"] or 0.0
    )
    result["urgency_boost"] = float(
        result["urgency_boost"] or 0.0
    )

    return {
        "success": True,
        "topic": result,
    }


def get_monitoring_profile_matches(
    *,
    engine,
    profile_id: int,
    limit: int = 50,
) -> dict:
    """
    Returns relevant stories already matched to one profile.
    """
    limit = max(
        1,
        min(
            200,
            int(limit),
        ),
    )

    with engine.connect() as connection:
        profile = connection.execute(
            text("""
                SELECT
                    id,
                    name,
                    min_urgency_score
                FROM monitoring_profiles
                WHERE id = :profile_id
                LIMIT 1
            """),
            {"profile_id": profile_id},
        ).mappings().first()

        if not profile:
            return {
                "success": False,
                "reason": "profile_not_found",
                "profile_id": profile_id,
            }

        rows = connection.execute(
            text("""
                SELECT
                    m.id AS match_id,
                    m.story_id,
                    m.relevance_score,
                    m.urgency_score,
                    m.matched_topics,
                    m.reasons,
                    m.created_at,
                    s.title,
                    s.summary,
                    s.source,
                    s.category,
                    s.priority,
                    s.priority_score,
                    s.published_at,
                    CASE
                        WHEN a.id IS NULL THEN FALSE
                        ELSE TRUE
                    END AS is_alert
                FROM monitoring_matches m
                JOIN stories s
                    ON s.id = m.story_id
                LEFT JOIN monitoring_alerts a
                    ON a.profile_id = m.profile_id
                    AND a.story_id = m.story_id
                WHERE m.profile_id = :profile_id
                ORDER BY
                    m.urgency_score DESC,
                    m.relevance_score DESC,
                    m.created_at DESC
                LIMIT :limit
            """),
            {
                "profile_id": profile_id,
                "limit": limit,
            },
        ).mappings().all()

    return {
        "success": True,
        "profile": {
            "id": profile["id"],
            "name": profile["name"],
        },
        "count": len(rows),
        "matches": [
            {
                "match_id": row["match_id"],
                "story": {
                    "id": row["story_id"],
                    "title": row["title"],
                    "summary": row["summary"],
                    "source": row["source"],
                    "category": row["category"],
                    "priority": row["priority"],
                    "priority_score": (
                        float(
                            row["priority_score"]
                        )
                        if row["priority_score"] is not None
                        else 0.0
                    ),
                    "published_at": row["published_at"],
                },
                "relevance_score": float(
                    row["relevance_score"]
                ),
                "urgency_score": float(
                    row["urgency_score"]
                ),
                "matched_topics": (
                    row["matched_topics"]
                    or []
                ),
                "reasons": (
                    row["reasons"]
                    or []
                ),
                "is_alert": bool(
                    row["is_alert"]
                ),
                "requires_attention": (
                    float(row["urgency_score"])
                    >= float(
                        profile["min_urgency_score"]
                    )
                ),
                "created_at": row["created_at"],
            }
            for row in rows
        ],
    }
