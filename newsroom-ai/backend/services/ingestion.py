import inspect

import json



from sqlalchemy import text

from services.embeddings import (

    embed_story,

    MODEL_NAME as EMBEDDING_MODEL_NAME,

)

from services.monitoring import (
    evaluate_story_for_all_profiles,
)





async def resolve_maybe_async(value):

    """

    Await an awaitable value; otherwise return it unchanged.



    The generic ingestion pipeline receives callbacks from main.py,

    and some of them are async while others are synchronous.

    """

    if inspect.isawaitable(value):

        return await value



    return value





async def ingest_source_stories(

    items: list[dict],

    *,

    engine,

    classify_story,

    interpret_classification,

    build_ai_metadata,

    auto_assign_story_to_thread,

    run_what_changed,

    create_story_alert,

):

    """

    Generic ingestion pipeline for normalized source stories.



    Every item should contain at least:

    - external_id

    - title

    - source

    - source_type

    - summary

    - url

    - published_at



    Source-specific fetching must happen before calling

    this function.

    """



    counters = {

        "inserted": 0,

        "skipped": 0,



        "ai_failures": 0,

        "embedding_failures": 0,

        "thread_failures": 0,

        "change_failures": 0,

        "changes_generated": 0,



        "alert_failures": 0,

        "alerts_created": 0,



        "monitoring_failures": 0,

        "monitoring_profiles_evaluated": 0,

        "monitoring_matches": 0,

        "monitoring_alerts": 0,



        "errors": 0,



        "total_received": len(items),

    }



    results = []



    for item in items:



        external_id = item.get(

            "external_id"

        )



        if not external_id:

            counters["errors"] += 1



            results.append(

                {

                    "success": False,

                    "reason": (

                        "missing_external_id"

                    ),

                    "item": item,

                }

            )



            continue



        # -------------------------------------------------

        # DEDUPE

        # -------------------------------------------------



        try:

            with engine.connect() as connection:



                existing = connection.execute(

                    text("""

                        SELECT id



                        FROM stories



                        WHERE external_id = :external_id



                        LIMIT 1

                    """),

                    {

                        "external_id": (

                            external_id

                        ),

                    },

                ).mappings().first()



            if existing:

                counters[

                    "skipped"

                ] += 1



                results.append(

                    {

                        "success": True,

                        "inserted": False,

                        "reason": (

                            "already_exists"

                        ),

                        "story_id": (

                            existing["id"]

                        ),

                        "external_id": (

                            external_id

                        ),

                    }

                )



                continue



        except Exception as exc:

            counters["errors"] += 1



            results.append(

                {

                    "success": False,

                    "external_id": (

                        external_id

                    ),

                    "stage": "dedupe",

                    "error": str(exc),

                }

            )



            continue



        # -------------------------------------------------

        # AI CLASSIFICATION

        # -------------------------------------------------



        priority = "Não classificada"

        category = "Não classificada"

        priority_score = None

        category_score = None

        ai_metadata = None



        try:

            jev_result = await resolve_maybe_async(

                classify_story(

                    title=(

                        item.get("title")

                        or ""

                    ),

                    summary=(

                        item.get("summary")

                        or ""

                    ),

                )

            )



            classification = (

                interpret_classification(

                    jev_result

                )

            )



            priority = classification[

                "priority"

            ]



            category = classification[

                "category"

            ]



            priority_score = classification[

                "priority_score"

            ]



            category_score = classification[

                "category_score"

            ]



            ai_metadata = build_ai_metadata(

                jev_result,

                classification,

            )



        except Exception as exc:

            counters[

                "ai_failures"

            ] += 1



            ai_metadata = {

                "provider": "TypeSafe",

                "status": "failed",

                "error": str(exc),

            }



            print(

                "[INGESTION AI ERROR]",

                external_id,

                str(exc),

            )



        # -------------------------------------------------

        # INSERT STORY

        # -------------------------------------------------



        try:

            with engine.begin() as connection:



                inserted = connection.execute(

                    text("""

                        INSERT INTO stories (

                            title,

                            source,

                            source_type,

                            source_entity_id,

                            source_event_type,

                            time,

                            priority,

                            category,

                            summary,

                            external_id,

                            url,

                            published_at,

                            discovered_at,

                            status,

                            priority_score,

                            category_score,

                            ai_metadata

                        )



                        VALUES (

                            :title,

                            :source,

                            :source_type,

                            :source_entity_id,

                            :source_event_type,

                            :time,

                            :priority,

                            :category,

                            :summary,

                            :external_id,

                            :url,

                            :published_at,

                            NOW(),

                            'new',

                            :priority_score,

                            :category_score,

                            CAST(

                                :ai_metadata

                                AS JSONB

                            )

                        )



                        RETURNING id

                    """),

                    {

                        "title": (

                            item.get(

                                "title"

                            )

                        ),



                        "source": (

                            item.get(

                                "source"

                            )

                        ),



                        "source_type": (

                            item.get(

                                "source_type",

                                "official",

                            )

                        ),

                        "source_entity_id": (

                            item.get(

                                "source_entity_id"

                            )

                        ),



                        "source_event_type": (

                            item.get(

                                "source_event_type"

                            )

                        ),



                        "time": (

                            item.get(

                                "time"

                            )

                        ),



                        "priority": (

                            priority

                        ),



                        "category": (

                            category

                        ),



                        "summary": (

                            item.get(

                                "summary"

                            )

                        ),



                        "external_id": (

                            external_id

                        ),



                        "url": (

                            item.get(

                                "url"

                            )

                        ),



                        "published_at": (

                            item.get(

                                "published_at"

                            )

                        ),



                        "priority_score": (

                            priority_score

                        ),



                        "category_score": (

                            category_score

                        ),



                        "ai_metadata": (

                            json.dumps(

                                ai_metadata,

                                ensure_ascii=False,

                            )

                            if ai_metadata

                            is not None

                            else None

                        ),

                    },

                ).mappings().first()



            story_id = inserted["id"]



            counters[

                "inserted"

            ] += 1



        except Exception as exc:



            counters[

                "errors"

            ] += 1



            results.append(

                {

                    "success": False,

                    "external_id": (

                        external_id

                    ),

                    "stage": "insert",

                    "error": str(exc),

                }

            )



            continue



        # -------------------------------------------------

        # EMBEDDING

        # -------------------------------------------------



        try:

            embedding = embed_story(

                title=(

                    item.get("title")

                    or ""

                ),

                summary=(

                    item.get("summary")

                    or ""

                ),

            )



            with engine.begin() as connection:



                connection.execute(

                    text("""

                        INSERT INTO story_embeddings (

                            story_id,

                            embedding,

                            model

                        )



                        VALUES (

                            :story_id,

                            :embedding,

                            :model

                        )



                        ON CONFLICT (

                            story_id

                        )



                        DO UPDATE SET

                            embedding =

                                EXCLUDED.embedding,



                            model =

                                EXCLUDED.model,



                            created_at =

                                NOW()

                    """),

                    {

                        "story_id": (

                            story_id

                        ),



                        "embedding": (

                            embedding

                        ),



                        "model": (

                            EMBEDDING_MODEL_NAME

                        ),

                    },

                )



        except Exception as exc:



            counters[

                "embedding_failures"

            ] += 1



            print(

                "[INGESTION EMBEDDING ERROR]",

                story_id,

                str(exc),

            )



        # -------------------------------------------------

        # THREAD MATCHING

        # -------------------------------------------------



        thread_result = None



        try:

            thread_result = await resolve_maybe_async(

                auto_assign_story_to_thread(

                    story_id

                )

            )



        except Exception as exc:



            counters[

                "thread_failures"

            ] += 1



            print(

                "[INGESTION THREAD ERROR]",

                story_id,

                str(exc),

            )



        # -------------------------------------------------

        # WHAT CHANGED

        # -------------------------------------------------



        change_result = None



        try:

            if (

                thread_result

                and thread_result.get(

                    "thread_id"

                )

            ):

                change_result = await resolve_maybe_async(

                    run_what_changed(

                        story_id

                    )

                )



                if (

                    change_result

                    and change_result.get(

                        "has_history"

                    )

                ):

                    counters[

                        "changes_generated"

                    ] += 1



        except Exception as exc:



            counters[

                "change_failures"

            ] += 1



            print(

                "[INGESTION CHANGE ERROR]",

                story_id,

                str(exc),

            )



        # -------------------------------------------------

        # ALERT ENGINE

        # -------------------------------------------------



        alert_result = None



        try:

            alert_result = await resolve_maybe_async(

                create_story_alert(

                    story_id,

                    change_result=(

                        change_result

                    ),

                )

            )



            if (

                alert_result

                and alert_result.get(

                    "created"

                )

            ):

                counters[

                    "alerts_created"

                ] += 1



        except Exception as exc:



            counters[

                "alert_failures"

            ] += 1



            print(

                "[INGESTION ALERT ERROR]",

                story_id,

                str(exc),

            )



        # -------------------------------------------------

        # CLIENT MONITORING

        # -------------------------------------------------



        monitoring_result = None



        try:

            monitoring_result = await resolve_maybe_async(

                evaluate_story_for_all_profiles(

                    engine=engine,

                    story_id=story_id,

                )

            )



            if monitoring_result:

                counters[

                    "monitoring_profiles_evaluated"

                ] += int(

                    monitoring_result.get(

                        "profiles_evaluated",

                        0,

                    )

                    or 0

                )



                counters[

                    "monitoring_matches"

                ] += len(

                    monitoring_result.get(

                        "matches",

                        [],

                    )

                    or []

                )



                counters[

                    "monitoring_alerts"

                ] += len(

                    monitoring_result.get(

                        "alerts",

                        [],

                    )

                    or []

                )



        except Exception as exc:

            counters[

                "monitoring_failures"

            ] += 1



            print(

                "[INGESTION MONITORING ERROR]",

                story_id,

                str(exc),

            )



        # -------------------------------------------------

        # RESULT

        # -------------------------------------------------



        results.append(

            {

                "success": True,

                "inserted": True,

                "story_id": story_id,

                "external_id": (

                    external_id

                ),

                "source": (

                    item.get("source")

                ),

                "source_type": (

                    item.get(

                        "source_type"

                    )

                ),

                "thread": (

                    thread_result

                ),

                "change": (

                    change_result

                ),

                "alert": (

                    alert_result

                ),

                "monitoring": (

                    monitoring_result

                ),

            }

        )



    return {

        **counters,

        "results": results,

    }