import json
from uuid import uuid4
from contextlib import asynccontextmanager
from fastapi import HTTPException
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, text
import os
import html
import httpx
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

from services.generator import (
    generate_change_summary,
    generate_thread_identity,
)
from services.topic_expansion import (
    expand_topic_with_ai,
    expand_and_save_topic,
    expand_profile_topics,
)
from sources.camara import (
    fetch_recent_propositions,
    fetch_proposition_details,
    fetch_camara_stories,
)

from services.jev import (
    get_models,
    classify_story,
    interpret_classification,
    compare_story_with_candidates,
    interpret_thread_candidates,
    analyze_story_changes,
    interpret_story_changes,
)

from services.embeddings import (
    embed_story,
    MODEL_NAME as EMBEDDING_MODEL_NAME,
)

from services.ingestion import (
    ingest_source_stories,
)

from sources.senado import (
    fetch_senado_stories,
)
from services.monitoring import (
    evaluate_story_for_profile,
    evaluate_story_for_all_profiles,
    get_topic_calibration_report,
    get_monitoring_alerts,
    get_monitoring_digest,
    get_monitoring_briefing,
    get_monitoring_profile,
    update_monitoring_profile,
    delete_monitoring_profile,
    update_monitoring_topic,
    get_monitoring_profile_matches,
    backfill_monitoring_profile,
)


# =========================================================
# CONFIG
# =========================================================

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not configured. Copy .env.example to .env "
        "and set your local PostgreSQL connection string."
    )

AUTO_THREAD_SAME_THRESHOLD = 0.60
AUTO_THREAD_CONTINUATION_THRESHOLD = 0.55
AUTO_THREAD_REFERENCE_THRESHOLD = 0.70
CAMARA_POLL_MINUTES = 10
DELIVERY_POLL_MINUTES = 1
SENADO_POLL_MINUTES = 10


# =========================================================
# DATABASE
# =========================================================

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)


# =========================================================
# SCHEDULER
# =========================================================

scheduler = AsyncIOScheduler()


# =========================================================
# PYDANTIC MODELS
# =========================================================

class MonitoringProfileUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    enabled: bool | None = None
    min_relevance_score: float | None = None
    min_urgency_score: float | None = None
    alert_on_status_change: bool | None = None
    alert_on_new_measure: bool | None = None
    alert_on_date_change: bool | None = None
    alert_on_contradiction: bool | None = None


class MonitoringTopicUpdate(BaseModel):
    topic: str | None = None
    semantic_description: str | None = None
    weight: float | None = None
    urgency_boost: float | None = None
    enabled: bool | None = None

class MonitoringProfileCreate(BaseModel):
    name: str
    description: str | None = None
    min_relevance_score: float = 0.50
    min_urgency_score: float = 0.70
    alert_on_status_change: bool = True
    alert_on_new_measure: bool = True
    alert_on_date_change: bool = False
    alert_on_contradiction: bool = True


class MonitoringTopicCreate(BaseModel):
    topic: str
    
class StoryStatusUpdate(BaseModel):
    status: str


class ThreadCreate(BaseModel):
    title: str
    summary: str | None = None
    category: str | None = None


class AlertStatusUpdate(BaseModel):
    status: str

class AlertDeliveryCreate(BaseModel):
    channel: str
    destination: str | None = None

class NotificationChannelCreate(BaseModel):
    name: str
    channel: str
    destination: str
    enabled: bool = True
    min_priority_score: float | None = None
    min_meaningful_change_score: float | None = None

class NotificationChannelUpdate(BaseModel):
    name: str | None = None
    destination: str | None = None
    enabled: bool | None = None
    min_priority_score: float | None = None
    min_meaningful_change_score: float | None = None

# =========================================================
# HELPERS
# =========================================================
def get_operations_health():
    now = datetime.now()

    # -----------------------------------------------------
    # SCHEDULER
    # -----------------------------------------------------

    scheduler_running = False
    scheduler_jobs = []

    try:
        scheduler_running = scheduler.running

        for job in scheduler.get_jobs():
            scheduler_jobs.append(
                {
                    "id": job.id,
                    "next_run_time": (
                        job.next_run_time.isoformat()
                        if job.next_run_time
                        else None
                    ),
                }
            )

    except Exception as exc:
        scheduler_jobs.append(
            {
                "error": str(exc),
            }
        )

    # -----------------------------------------------------
    # DATABASE HEALTH
    # -----------------------------------------------------

    with engine.connect() as connection:

        # Câmara
        camara = connection.execute(
            text("""
                SELECT
                    MAX(discovered_at)
                        AS last_story_discovered_at,

                    COUNT(*) FILTER (
                        WHERE discovered_at
                            >= NOW() - INTERVAL '24 hours'
                    )
                        AS stories_last_24h

                FROM stories

                WHERE source = 'Câmara dos Deputados'
            """)
        ).mappings().first()

        senado = connection.execute(
            text("""
                SELECT
                    MAX(discovered_at)
                        AS last_story_discovered_at,

                    COUNT(*) FILTER (
                        WHERE discovered_at
                            >= NOW() - INTERVAL '24 hours'
                    )
                        AS stories_last_24h

                FROM stories

                WHERE source = 'Senado Federal'
            """)
        ).mappings().first()

        # Deliveries
        deliveries = connection.execute(
            text("""
                SELECT
                    COUNT(*) FILTER (
                        WHERE status = 'pending'
                    ) AS pending,

                    COUNT(*) FILTER (
                        WHERE status = 'sending'
                    ) AS sending,

                    COUNT(*) FILTER (
                        WHERE status = 'failed'
                    ) AS failed,

                    COUNT(*) FILTER (
                        WHERE
                            status = 'failed'
                            AND attempt_count < max_attempts
                            AND next_attempt_at IS NOT NULL
                    ) AS retrying,

                    COUNT(*) FILTER (
                        WHERE
                            status = 'failed'
                            AND (
                                attempt_count >= max_attempts
                                OR next_attempt_at IS NULL
                            )
                    ) AS permanently_failed,

                    COUNT(*) FILTER (
                        WHERE
                            status = 'sent'
                            AND sent_at
                                >= NOW() - INTERVAL '24 hours'
                    ) AS sent_last_24h,

                    MAX(sent_at)
                        AS last_sent_at

                FROM alert_deliveries
            """)
        ).mappings().first()

        # Notification channels
        channels = connection.execute(
            text("""
                SELECT
                    COUNT(*) FILTER (
                        WHERE enabled = TRUE
                    ) AS enabled,

                    COUNT(*) FILTER (
                        WHERE enabled = FALSE
                    ) AS disabled

                FROM notification_channels
            """)
        ).mappings().first()

    # -----------------------------------------------------
    # STATUS EVALUATION
    # -----------------------------------------------------

    problems = []

    if not scheduler_running:
        problems.append(
            "scheduler_not_running"
        )

    if (
        channels["enabled"] == 0
    ):
        problems.append(
            "no_notification_channels_enabled"
        )

    if (
        deliveries["permanently_failed"] > 0
    ):
        problems.append(
            "permanent_delivery_failures"
        )

    if (
        deliveries["sending"] > 0
    ):
        problems.append(
            "deliveries_currently_sending"
        )

    status = (
        "healthy"
        if len(problems) == 0
        else "degraded"
    )

    # -----------------------------------------------------
    # RESPONSE
    # -----------------------------------------------------

    return {
        "status": status,

        "checked_at": (
            now.isoformat()
        ),

        "problems": problems,

        "scheduler": {
            "running": (
                scheduler_running
            ),
            "jobs": (
                scheduler_jobs
            ),
        },

        "camara": {
            "last_story_discovered_at": (
                camara[
                    "last_story_discovered_at"
                ].isoformat()
                if camara[
                    "last_story_discovered_at"
                ]
                else None
            ),

            "stories_last_24h": (
                camara[
                    "stories_last_24h"
                ]
            ),
        },

        "senado": {
            "last_story_discovered_at": (
                senado[
                    "last_story_discovered_at"
                ].isoformat()
                if senado[
                    "last_story_discovered_at"
                ]
                else None
            ),

            "stories_last_24h": (
                senado[
                    "stories_last_24h"
                ]
            ),
        },

        "deliveries": {
            "pending": (
                deliveries["pending"]
            ),

            "sending": (
                deliveries["sending"]
            ),

            "failed": (
                deliveries["failed"]
            ),

            "retrying": (
                deliveries["retrying"]
            ),

            "permanently_failed": (
                deliveries[
                    "permanently_failed"
                ]
            ),

            "sent_last_24h": (
                deliveries[
                    "sent_last_24h"
                ]
            ),

            "last_sent_at": (
                deliveries[
                    "last_sent_at"
                ].isoformat()
                if deliveries[
                    "last_sent_at"
                ]
                else None
            ),
        },

        "notification_channels": {
            "enabled": (
                channels["enabled"]
            ),

            "disabled": (
                channels["disabled"]
            ),
        },
    }

def recover_stuck_deliveries(
    stuck_minutes: int = 5,
):
    """
    Recovers deliveries left in 'sending' state
    after an interrupted process.
    """

    with engine.begin() as connection:

        rows = connection.execute(
            text("""
                UPDATE alert_deliveries

                SET
                    status = 'failed',

                    last_error = (
                        'Recovered from stale '
                        'sending state'
                    ),

                    next_attempt_at = NOW(),

                    updated_at = NOW()

                WHERE
                    status = 'sending'

                    AND last_attempt_at
                        < NOW()
                        - (
                            :stuck_minutes
                            * INTERVAL '1 minute'
                        )

                    AND attempt_count
                        < max_attempts

                RETURNING id
            """),
            {
                "stuck_minutes": (
                    stuck_minutes
                ),
            },
        ).mappings().all()

    return {
        "recovered": len(rows),
        "delivery_ids": [
            row["id"]
            for row in rows
        ],
    }

def get_retry_delay_minutes(
    attempt_count: int,
) -> int | None:
    """
    Returns retry delay based on the number
    of attempts already made.
    """

    retry_schedule = {
        1: 1,
        2: 5,
        3: 15,
    }

    return retry_schedule.get(
        attempt_count
    )

def process_pending_deliveries(
    limit: int = 20,
):
    """
    Processes pending deliveries and failed deliveries
    whose retry time has arrived.
    """

    with engine.connect() as connection:
        rows = connection.execute(
            text("""
                SELECT
                    id

                FROM alert_deliveries

                WHERE
                    (
                        status = 'pending'

                        OR (
                            status = 'failed'
                            AND attempt_count < max_attempts
                        )
                    )

                    AND (
                        next_attempt_at IS NULL
                        OR next_attempt_at <= NOW()
                    )

                ORDER BY
                    COALESCE(
                        next_attempt_at,
                        created_at
                    ) ASC,
                    id ASC

                LIMIT :limit
            """),
            {
                "limit": limit,
            },
        ).mappings().all()

    results = []

    processed = 0
    sent = 0
    failed = 0

    for row in rows:
        delivery_id = row["id"]

        try:
            result = process_delivery(
                delivery_id
            )

            processed += 1

            delivery_data = (
                result.get(
                    "delivery",
                    {},
                )
            )

            if (
                result.get("success")
                and delivery_data.get(
                    "status"
                )
                == "sent"
            ):
                sent += 1
            else:
                failed += 1

            results.append(
                {
                    "delivery_id": (
                        delivery_id
                    ),
                    "result": result,
                }
            )

        except Exception as exc:
            failed += 1

            results.append(
                {
                    "delivery_id": (
                        delivery_id
                    ),
                    "error": str(exc),
                }
            )

    return {
        "found": len(rows),
        "processed": processed,
        "sent": sent,
        "failed": failed,
        "results": results,
    }

def process_delivery(
    delivery_id: int,
):
    """
    Processes one delivery with retry support.

    Telegram is currently the real delivery channel.
    """

    # -----------------------------------------------------
    # LOAD + LOCK DELIVERY
    # -----------------------------------------------------

    with engine.begin() as connection:

        delivery = connection.execute(
            text("""
                SELECT
                    d.id,
                    d.alert_id,
                    d.channel,
                    d.destination,
                    d.status,
                    d.attempt_count,
                    d.max_attempts,
                    d.next_attempt_at,

                    a.title,
                    a.message,
                    a.alert_type

                FROM alert_deliveries d

                JOIN newsroom_alerts a
                    ON a.id = d.alert_id

                WHERE d.id = :delivery_id

                FOR UPDATE
            """),
            {
                "delivery_id": delivery_id,
            },
        ).mappings().first()

        if not delivery:
            return {
                "success": False,
                "reason": "delivery_not_found",
            }

        # -------------------------------------------------
        # IDEMPOTENCY
        # -------------------------------------------------

        if delivery["status"] == "sent":
            return {
                "success": True,
                "status": "sent",
                "reason": "already_sent",
                "delivery_id": delivery_id,
            }

        # -------------------------------------------------
        # MAX ATTEMPTS
        # -------------------------------------------------

        if (
            delivery["attempt_count"]
            >= delivery["max_attempts"]
        ):
            return {
                "success": False,
                "status": "failed",
                "reason": "max_attempts_reached",
                "delivery_id": delivery_id,
            }

        # -------------------------------------------------
        # MARK SENDING
        # -------------------------------------------------

        connection.execute(
            text("""
                UPDATE alert_deliveries

                SET
                    status = 'sending',
                    attempt_count =
                        attempt_count + 1,
                    last_attempt_at = NOW(),
                    updated_at = NOW(),
                    last_error = NULL

                WHERE id = :delivery_id
            """),
            {
                "delivery_id": delivery_id,
            },
        )

    current_attempt = (
        delivery["attempt_count"] + 1
    )

    # -----------------------------------------------------
    # EXTERNAL DELIVERY
    # -----------------------------------------------------

    try:
        channel = delivery[
            "channel"
        ]

        if channel == "telegram":
            provider_result = (
                send_telegram_alert(
                    destination=delivery[
                        "destination"
                    ],
                    title=delivery[
                        "title"
                    ],
                    message=delivery[
                        "message"
                    ],
                )
            )

        else:
            raise NotImplementedError(
                f"Delivery channel "
                f"'{channel}' "
                f"is not implemented yet."
            )

        external_id = (
            provider_result[
                "external_id"
            ]
        )

        # -------------------------------------------------
        # MARK SENT
        # -------------------------------------------------

        with engine.begin() as connection:

            updated = connection.execute(
                text("""
                    UPDATE alert_deliveries

                    SET
                        status = 'sent',
                        external_id = :external_id,
                        sent_at = NOW(),
                        next_attempt_at = NULL,
                        updated_at = NOW(),
                        last_error = NULL

                    WHERE id = :delivery_id

                    RETURNING
                        id,
                        alert_id,
                        channel,
                        destination,
                        status,
                        attempt_count,
                        max_attempts,
                        external_id,
                        sent_at
                """),
                {
                    "delivery_id": (
                        delivery_id
                    ),
                    "external_id": (
                        external_id
                    ),
                },
            ).mappings().first()

        return {
            "success": True,
            "delivery": dict(
                updated
            ),
            "provider": (
                provider_result[
                    "provider"
                ]
            ),
        }

    except Exception as exc:

        # -------------------------------------------------
        # RETRY CALCULATION
        # -------------------------------------------------

        retry_delay = (
            get_retry_delay_minutes(
                current_attempt
            )
        )

        max_attempts = (
            delivery["max_attempts"]
        )

        has_retry = (
            current_attempt
            < max_attempts
            and retry_delay is not None
        )

        with engine.begin() as connection:

            if has_retry:
                connection.execute(
                    text("""
                        UPDATE alert_deliveries

                        SET
                            status = 'failed',
                            last_error = :error,

                            next_attempt_at =
                                NOW()
                                + (
                                    :delay_minutes
                                    * INTERVAL '1 minute'
                                ),

                            updated_at = NOW()

                        WHERE id = :delivery_id
                    """),
                    {
                        "delivery_id": (
                            delivery_id
                        ),
                        "error": str(exc),
                        "delay_minutes": (
                            retry_delay
                        ),
                    },
                )

            else:
                connection.execute(
                    text("""
                        UPDATE alert_deliveries

                        SET
                            status = 'failed',
                            last_error = :error,
                            next_attempt_at = NULL,
                            updated_at = NOW()

                        WHERE id = :delivery_id
                    """),
                    {
                        "delivery_id": (
                            delivery_id
                        ),
                        "error": str(exc),
                    },
                )

        print(
            f"[DELIVERY ERROR] "
            f"delivery={delivery_id} "
            f"attempt={current_attempt}: "
            f"{exc}"
        )

        return {
            "success": False,
            "delivery_id": delivery_id,
            "status": "failed",
            "attempt": current_attempt,
            "retry_scheduled": has_retry,
            "retry_in_minutes": (
                retry_delay
                if has_retry
                else None
            ),
            "error": str(exc),
        }

def send_telegram_alert(
    destination: str,
    title: str,
    message: str,
) -> dict:
    """
    Sends one newsroom alert through Telegram Bot API.
    """

    token = os.getenv(
        "TELEGRAM_BOT_TOKEN"
    )

    if not token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN not configured"
        )

    if not destination:
        raise ValueError(
            "Telegram destination is missing"
        )

    telegram_url = (
        f"https://api.telegram.org/"
        f"bot{token}/sendMessage"
    )

    safe_title = html.escape(
        title or "Newsroom Alert"
    )

    safe_message = html.escape(
        message or ""
    )

    text_message = (
        f"<b>🚨 {safe_title}</b>\n\n"
        f"{safe_message}"
    )

    response = httpx.post(
        telegram_url,
        json={
            "chat_id": destination,
            "text": text_message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
        timeout=20.0,
    )

    if response.status_code >= 400:
        raise RuntimeError(
            f"Telegram error "
            f"{response.status_code}: "
            f"{response.text}"
        )

    data = response.json()

    if not data.get("ok"):
        raise RuntimeError(
            f"Telegram API rejected message: "
            f"{data}"
        )

    telegram_message = data.get(
        "result",
        {}
    )

    return {
        "external_id": str(
            telegram_message.get(
                "message_id"
            )
        ),
        "provider": "telegram",
        "response": data,
    }

def create_alert_delivery(
    alert_id: int,
    channel: str,
    destination: str | None = None,
):
    """
    Creates a pending delivery for an alert.

    Prevents duplicate deliveries for the same:
    alert + channel + destination.
    """

    allowed_channels = {
        "telegram",
        "email",
        "webhook",
    }

    if channel not in allowed_channels:
        return {
            "created": False,
            "reason": "invalid_channel",
            "allowed_channels": sorted(
                allowed_channels
            ),
        }

    with engine.begin() as connection:

        # -------------------------------------------------
        # CHECK ALERT
        # -------------------------------------------------

        alert = connection.execute(
            text("""
                SELECT
                    id,
                    status

                FROM newsroom_alerts

                WHERE id = :alert_id
            """),
            {
                "alert_id": alert_id,
            },
        ).mappings().first()

        if not alert:
            return {
                "created": False,
                "reason": "alert_not_found",
            }

        # -------------------------------------------------
        # DEDUPE
        # -------------------------------------------------

        existing = connection.execute(
            text("""
                SELECT
                    id,
                    status,
                    channel,
                    destination

                FROM alert_deliveries

                WHERE
                    alert_id = :alert_id
                    AND channel = :channel
                    AND destination IS NOT DISTINCT FROM :destination

                LIMIT 1
            """),
            {
                "alert_id": alert_id,
                "channel": channel,
                "destination": destination,
            },
        ).mappings().first()

        if existing:
            return {
                "created": False,
                "reason": "delivery_already_exists",
                "delivery_id": existing["id"],
                "status": existing["status"],
                "channel": existing["channel"],
                "destination": existing[
                    "destination"
                ],
            }

        # -------------------------------------------------
        # CREATE DELIVERY
        # -------------------------------------------------

        delivery = connection.execute(
            text("""
                INSERT INTO alert_deliveries (
                    alert_id,
                    channel,
                    destination,
                    status,
                    attempt_count,
                    next_attempt_at,
                    max_attempts
                )
                VALUES (
                    :alert_id,
                    :channel,
                    :destination,
                    'pending',
                    0,
                    NOW(),
                    3
                )

                RETURNING
                    id,
                    alert_id,
                    channel,
                    destination,
                    status,
                    attempt_count,
                    max_attempts,
                    next_attempt_at,
                    last_attempt_at,
                    external_id,
                    last_error,
                    created_at,
                    updated_at,
                    sent_at
            """),
            {
                "alert_id": alert_id,
                "channel": channel,
                "destination": destination,
            },
        ).mappings().first()

    return {
        "created": True,
        "delivery": dict(
            delivery
        ),
    }

def create_deliveries_for_alert(
    alert_id: int,
):
    """
    Creates delivery jobs for every enabled notification
    channel compatible with the alert.

    No external delivery happens here.
    This only creates pending delivery records.
    """

    with engine.connect() as connection:

        alert = connection.execute(
            text("""
                SELECT
                    id,
                    priority_score,
                    meaningful_change_score

                FROM newsroom_alerts

                WHERE id = :alert_id
            """),
            {
                "alert_id": alert_id,
            },
        ).mappings().first()

        if not alert:
            return {
                "created": 0,
                "reason": "alert_not_found",
                "deliveries": [],
            }

        channels = connection.execute(
            text("""
                SELECT
                    id,
                    name,
                    channel,
                    destination,
                    min_priority_score,
                    min_meaningful_change_score

                FROM notification_channels

                WHERE enabled = TRUE

                ORDER BY id ASC
            """)
        ).mappings().all()

    priority_score = (
        float(alert["priority_score"])
        if alert["priority_score"] is not None
        else 0.0
    )

    meaningful_change_score = (
        float(
            alert[
                "meaningful_change_score"
            ]
        )
        if (
            alert[
                "meaningful_change_score"
            ]
            is not None
        )
        else 0.0
    )

    created = []

    skipped = []

    for channel in channels:

        min_priority = (
            float(
                channel[
                    "min_priority_score"
                ]
            )
            if (
                channel[
                    "min_priority_score"
                ]
                is not None
            )
            else None
        )

        min_change = (
            float(
                channel[
                    "min_meaningful_change_score"
                ]
            )
            if (
                channel[
                    "min_meaningful_change_score"
                ]
                is not None
            )
            else None
        )

        if (
            min_priority is not None
            and priority_score < min_priority
        ):
            skipped.append(
                {
                    "channel_id": channel["id"],
                    "reason": (
                        "priority_below_channel_threshold"
                    ),
                }
            )

            continue

        if (
            min_change is not None
            and meaningful_change_score
            < min_change
        ):
            skipped.append(
                {
                    "channel_id": channel["id"],
                    "reason": (
                        "change_below_channel_threshold"
                    ),
                }
            )

            continue

        delivery_result = (
            create_alert_delivery(
                alert_id=alert_id,
                channel=channel[
                    "channel"
                ],
                destination=channel[
                    "destination"
                ],
            )
        )

        if delivery_result.get(
            "created"
        ):
            created.append(
                {
                    "channel_id": (
                        channel["id"]
                    ),
                    "channel_name": (
                        channel["name"]
                    ),
                    "delivery": (
                        delivery_result[
                            "delivery"
                        ]
                    ),
                }
            )

    return {
        "alert_id": alert_id,
        "created": len(created),
        "skipped": len(skipped),
        "deliveries": created,
        "skipped_channels": skipped,
    }

def embedding_to_string(
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


def build_ai_metadata(
    jev_result: dict,
    classification: dict,
) -> dict:
    return {
        "provider": "TypeSafe",
        "model": jev_result.get("model"),
        "answers": jev_result.get("answers"),
        "usage": jev_result.get("usage"),
        "tags": classification.get(
            "tags",
            [],
        ),
        "political_relevance": (
            classification.get(
                "political_relevance"
            )
        ),
        "category_scores": (
            classification.get(
                "category_scores",
                {},
            )
        ),
    }

def refresh_thread_identity(
    thread_id: int,
):
    """
    Regenera título e resumo editorial de um thread
    com base nas stories atualmente associadas.
    """

    # -----------------------------------------------------
    # LOAD THREAD
    # -----------------------------------------------------

    with engine.connect() as connection:
        thread = connection.execute(
            text("""
                SELECT
                    id,
                    title,
                    summary,
                    category

                FROM story_threads

                WHERE id = :thread_id
            """),
            {
                "thread_id": thread_id,
            },
        ).mappings().first()

    if not thread:
        raise ValueError(
            f"Thread {thread_id} não encontrado."
        )

    # -----------------------------------------------------
    # LOAD STORIES
    # -----------------------------------------------------

    with engine.connect() as connection:
        stories = connection.execute(
            text("""
                SELECT
                    s.id,
                    s.title,
                    s.summary,
                    s.category,
                    s.published_at,
                    s.discovered_at

                FROM story_thread_items i

                JOIN stories s
                    ON s.id = i.story_id

                WHERE i.thread_id = :thread_id

                ORDER BY
                    COALESCE(
                        s.published_at,
                        s.discovered_at
                    ) ASC,
                    s.id ASC
            """),
            {
                "thread_id": thread_id,
            },
        ).mappings().all()

    if not stories:
        raise ValueError(
            f"Thread {thread_id} não possui stories."
        )

    # -----------------------------------------------------
    # GENERATE IDENTITY
    # -----------------------------------------------------

    generated = generate_thread_identity(
        stories=[
            dict(story)
            for story in stories
        ],
    )

    # -----------------------------------------------------
    # SAVE
    # -----------------------------------------------------

    with engine.begin() as connection:
        connection.execute(
            text("""
                UPDATE story_threads

                SET
                    title = :title,
                    summary = :summary,
                    generator_metadata =
                        CAST(
                            :generator_metadata
                            AS JSONB
                        ),
                    updated_at = NOW()

                WHERE id = :thread_id
            """),
            {
                "thread_id": thread_id,
                "title": generated["title"],
                "summary": generated["summary"],

                "generator_metadata": json.dumps(
                    generated["metadata"],
                    ensure_ascii=False,
                ),
            },
        )

    return {
        "thread_id": thread_id,
        "story_count": len(stories),
        "title": generated["title"],
        "summary": generated["summary"],
        "generator": generated["metadata"],
    }

# =========================================================
# EMBEDDINGS
# =========================================================

def create_story_embedding(
    story_id: int,
    title: str,
    summary: str,
) -> bool:
    embedding = embed_story(
        title=title,
        summary=summary,
    )

    embedding_string = (
        embedding_to_string(
            embedding
        )
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
                    CAST(:embedding AS vector),
                    :model
                )
                ON CONFLICT (story_id)
                DO NOTHING
            """),
            {
                "story_id": story_id,
                "embedding": embedding_string,
                "model": EMBEDDING_MODEL_NAME,
            },
        )

    return True


# =========================================================
# THREAD CANDIDATE MATCHING
# =========================================================
def candidate_passes_thread_gate(
    candidate: dict,
) -> bool:
    same_thread = candidate.get(
        "same_thread_score",
        0.0,
    )

    direct_continuation = candidate.get(
        "direct_continuation_score",
        0.0,
    )

    shared_reference = candidate.get(
        "shared_specific_reference_score",
        0.0,
    )

    standard_match = (
        same_thread >= 0.60
        and (
            direct_continuation >= 0.55
            or shared_reference >= 0.70
        )
    )

    strong_reference_match = (
        shared_reference >= 0.85
        and same_thread >= 0.45
    )

    return (
        standard_match
        or strong_reference_match
    )

async def find_best_thread_candidate(
    story_id: int,
):
    # -----------------------------------------------------
    # CURRENT STORY
    # -----------------------------------------------------

    with engine.connect() as connection:
        story = connection.execute(
            text("""
                SELECT
                    id,
                    title,
                    summary,
                    category,
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

    if not story:
        return None

    # -----------------------------------------------------
    # EMBEDDING
    # -----------------------------------------------------

    embedding = embed_story(
        title=story["title"],
        summary=story["summary"],
    )

    embedding_string = (
        embedding_to_string(
            embedding
        )
    )

    # -----------------------------------------------------
    # TOP 5 PREVIOUS STORIES
    #
    # Only information that existed before current story.
    # Uses published_at when available, otherwise
    # discovered_at.
    # -----------------------------------------------------

    with engine.connect() as connection:
        rows = connection.execute(
            text("""
                SELECT
                    s.id,
                    s.title,
                    s.summary,
                    s.category,
                    s.source,
                    s.published_at,
                    s.discovered_at,

                    1 - (
                        e.embedding <=>
                        CAST(:embedding AS vector)
                    ) AS similarity

                FROM story_embeddings e

                JOIN stories s
                    ON s.id = e.story_id

                WHERE
                    s.id != :story_id

                    AND (
                        COALESCE(
                            s.published_at,
                            s.discovered_at
                        )
                        <
                        COALESCE(
                            :current_published_at,
                            :current_discovered_at
                        )

                        OR (

                            COALESCE(
                                s.published_at,
                                s.discovered_at
                            )
                            =
                            COALESCE(
                                :current_published_at,
                                :current_discovered_at
                            )

                            AND s.id < :story_id
                        )
                    )

                ORDER BY
                    e.embedding <=>
                    CAST(:embedding AS vector)

                LIMIT 5
            """),
            {
                "story_id": story_id,
                "embedding": embedding_string,
                "current_published_at": (
                    story["published_at"]
                ),
                "current_discovered_at": (
                    story["discovered_at"]
                ),
            },
        ).mappings().all()

    candidates = [
        {
            "id": row["id"],
            "title": row["title"],
            "summary": row["summary"],
            "category": row["category"],
            "source": row["source"],
            "published_at": (
                row["published_at"]
            ),
            "discovered_at": (
                row["discovered_at"]
            ),
            "vector_similarity": round(
                float(
                    row["similarity"]
                ),
                4,
            ),
        }
        for row in rows
    ]

    if not candidates:
        return None

    # -----------------------------------------------------
    # ONE JEV REQUEST FOR TOP 5
    # -----------------------------------------------------

    jev_result = (
        await compare_story_with_candidates(
            story=dict(story),
            candidates=candidates,
        )
    )

    evaluated = (
        interpret_thread_candidates(
            jev_result,
            candidates,
        )
    )

    if not evaluated:
        return None

    qualified_candidates = [
        candidate
        for candidate in evaluated
        if candidate_passes_thread_gate(
            candidate
        )
    ]

    # ---------------------------------------------------------
    # Choose best candidate only among candidates
    # that passed the 3-signal gate.
    # ---------------------------------------------------------

    best = None

    if qualified_candidates:
        qualified_candidates.sort(
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

        best = qualified_candidates[0]


    return {
        "story": dict(story),

        "candidate": best,

        "all_candidates": evaluated,

        "qualified_candidates": (
            qualified_candidates
        ),

        "jev": {
            "model": jev_result.get(
                "model"
            ),
            "usage": jev_result.get(
                "usage"
            ),
        },
    }

def save_thread_match_audit(
    story_id: int,
    match_result: dict,
    selected_candidate_id: int | None = None,
    resulting_thread_id: int | None = None,
):
    """
    Saves the complete candidate evaluation produced by
    find_best_thread_candidate().

    One evaluation produces one audit row per candidate.
    """

    evaluation_id = str(
        uuid4()
    )

    candidates = match_result.get(
        "all_candidates",
        [],
    )

    candidates = sorted(
        candidates,
        key=lambda candidate: (
            candidate.get(
                "vector_similarity",
                0.0,
            )
        ),
        reverse=True,
    )

    jev_metadata = match_result.get(
        "jev",
        {},
    )

    jev_model = jev_metadata.get(
        "model"
    )

    jev_usage = jev_metadata.get(
        "usage"
    )

    if not candidates:
        return {
            "evaluation_id": evaluation_id,
            "saved": 0,
        }

    rows = []

    for rank, candidate in enumerate(
        candidates,
        start=1,
    ):
        candidate_id = candidate.get(
            "story_id"
        )

        if candidate_id is None:
            candidate_id = candidate.get(
                "id"
            )

        if candidate_id is None:
            continue

        gate_passed = (
            candidate_passes_thread_gate(
                candidate
            )
        )

        selected = (
            selected_candidate_id
            is not None
            and candidate_id
            == selected_candidate_id
        )

        if selected:
            decision = "accepted"
        elif gate_passed:
            decision = "qualified_not_selected"
        else:
            decision = "rejected"

        rows.append(
            {
                "evaluation_id": (
                    evaluation_id
                ),
                "story_id": story_id,
                "candidate_story_id": (
                    candidate_id
                ),
                "candidate_rank": rank,

                "vector_similarity": (
                    candidate.get(
                        "vector_similarity"
                    )
                ),

                "same_thread_score": (
                    candidate.get(
                        "same_thread_score"
                    )
                ),

                "direct_continuation_score": (
                    candidate.get(
                        "direct_continuation_score"
                    )
                ),

                "shared_specific_reference_score": (
                    candidate.get(
                        "shared_specific_reference_score"
                    )
                ),

                "gate_passed": (
                    gate_passed
                ),

                "selected": selected,

                "decision": decision,

                "resulting_thread_id": (
                    resulting_thread_id
                    if selected
                    else None
                ),

                "jev_model": (
                    jev_model
                ),

                "jev_usage": (
                    json.dumps(
                        jev_usage,
                        ensure_ascii=False,
                    )
                    if jev_usage
                    is not None
                    else None
                ),
            }
        )

    if not rows:
        return {
            "evaluation_id": evaluation_id,
            "saved": 0,
        }

    with engine.begin() as connection:

        for row in rows:
            connection.execute(
                text("""
                    INSERT INTO thread_match_audits (
                        evaluation_id,
                        story_id,
                        candidate_story_id,
                        candidate_rank,
                        vector_similarity,
                        same_thread_score,
                        direct_continuation_score,
                        shared_specific_reference_score,
                        gate_passed,
                        selected,
                        decision,
                        resulting_thread_id,
                        jev_model,
                        jev_usage
                    )
                    VALUES (
                        CAST(
                            :evaluation_id
                            AS UUID
                        ),
                        :story_id,
                        :candidate_story_id,
                        :candidate_rank,
                        :vector_similarity,
                        :same_thread_score,
                        :direct_continuation_score,
                        :shared_specific_reference_score,
                        :gate_passed,
                        :selected,
                        :decision,
                        :resulting_thread_id,
                        :jev_model,
                        CAST(
                            :jev_usage
                            AS JSONB
                        )
                    )
                """),
                row,
            )

    return {
        "evaluation_id": (
            evaluation_id
        ),
        "saved": len(rows),
    }

def find_source_entity_candidate(
    story_id: int,
):
    """
    Finds another story that belongs to the exact same
    source entity.

    Example:
        source_entity_id = "senado:174024"

    This match is deterministic and does not require
    embeddings or JEV.
    """

    with engine.connect() as connection:

        current = connection.execute(
            text("""
                SELECT
                    id,
                    source_entity_id

                FROM stories

                WHERE id = :story_id

                LIMIT 1
            """),
            {
                "story_id": story_id,
            },
        ).mappings().first()

        if not current:
            return None

        source_entity_id = (
            current["source_entity_id"]
        )

        if not source_entity_id:
            return None

        candidate = connection.execute(
            text("""
                SELECT
                    id,
                    title,
                    source,
                    source_entity_id,
                    source_event_type,
                    published_at,
                    discovered_at

                FROM stories

                WHERE
                    id != :story_id

                    AND source_entity_id =
                        :source_entity_id

                ORDER BY
                    COALESCE(
                        published_at,
                        discovered_at
                    ) DESC,

                    id DESC

                LIMIT 1
            """),
            {
                "story_id": story_id,
                "source_entity_id": (
                    source_entity_id
                ),
            },
        ).mappings().first()

    if not candidate:
        return None

    return dict(candidate)

def assign_story_by_source_entity(
    story_id: int,
):
    """
    Tries to assign a story to a thread using the
    deterministic source_entity_id relationship.

    Returns None when deterministic matching is not
    possible, allowing the AI matcher to run as fallback.
    """

    candidate = (
        find_source_entity_candidate(
            story_id
        )
    )

    if not candidate:
        return None

    candidate_id = candidate["id"]

    # -----------------------------------------------------
    # CHECK CANDIDATE THREAD
    # -----------------------------------------------------

    with engine.connect() as connection:

        candidate_thread = connection.execute(
            text("""
                SELECT
                    thread_id

                FROM story_thread_items

                WHERE story_id = :candidate_id

                LIMIT 1
            """),
            {
                "candidate_id": (
                    candidate_id
                ),
            },
        ).mappings().first()

    # =====================================================
    # EXISTING THREAD
    # =====================================================

    if candidate_thread:

        thread_id = (
            candidate_thread[
                "thread_id"
            ]
        )

        with engine.begin() as connection:

            connection.execute(
                text("""
                    INSERT INTO story_thread_items (
                        thread_id,
                        story_id
                    )

                    VALUES (
                        :thread_id,
                        :story_id
                    )

                    ON CONFLICT DO NOTHING
                """),
                {
                    "thread_id": (
                        thread_id
                    ),
                    "story_id": (
                        story_id
                    ),
                },
            )

            connection.execute(
                text("""
                    UPDATE story_threads

                    SET updated_at = NOW()

                    WHERE id = :thread_id
                """),
                {
                    "thread_id": (
                        thread_id
                    ),
                },
            )

        try:
            thread_identity = (
                refresh_thread_identity(
                    thread_id
                )
            )

        except Exception as exc:

            print(
                "[THREAD IDENTITY ERROR] "
                f"thread={thread_id}: "
                f"{exc}"
            )

            thread_identity = {
                "status": "failed",
                "error": str(exc),
            }

        return {
            "linked": True,
            "created_thread": False,

            "story_id": story_id,
            "thread_id": thread_id,

            "candidate_story_id": (
                candidate_id
            ),

            "match_method": (
                "source_entity_id"
            ),

            "source_entity_id": (
                candidate[
                    "source_entity_id"
                ]
            ),

            "thread_identity": (
                thread_identity
            ),
        }

    # =====================================================
    # CANDIDATE HAS NO THREAD
    # CREATE NEW THREAD
    # =====================================================

    with engine.connect() as connection:

        current_story = (
            connection.execute(
                text("""
                    SELECT
                        id,
                        title,
                        category

                    FROM stories

                    WHERE id = :story_id

                    LIMIT 1
                """),
                {
                    "story_id": (
                        story_id
                    ),
                },
            ).mappings().first()
        )

    if not current_story:
        return None

    temporary_title = (
        "Thread automático - "
        f"{current_story['title']}"
    )

    with engine.begin() as connection:

        new_thread = connection.execute(
            text("""
                INSERT INTO story_threads (
                    title,
                    summary,
                    category,
                    created_at,
                    updated_at
                )

                VALUES (
                    :title,
                    NULL,
                    :category,
                    NOW(),
                    NOW()
                )

                RETURNING id
            """),
            {
                "title": (
                    temporary_title
                ),
                "category": (
                    current_story[
                        "category"
                    ]
                ),
            },
        ).mappings().first()

        thread_id = (
            new_thread["id"]
        )

        # Candidate
        connection.execute(
            text("""
                INSERT INTO story_thread_items (
                    thread_id,
                    story_id
                )

                VALUES (
                    :thread_id,
                    :candidate_id
                )

                ON CONFLICT DO NOTHING
            """),
            {
                "thread_id": (
                    thread_id
                ),
                "candidate_id": (
                    candidate_id
                ),
            },
        )

        # Current story
        connection.execute(
            text("""
                INSERT INTO story_thread_items (
                    thread_id,
                    story_id
                )

                VALUES (
                    :thread_id,
                    :story_id
                )

                ON CONFLICT DO NOTHING
            """),
            {
                "thread_id": (
                    thread_id
                ),
                "story_id": (
                    story_id
                ),
            },
        )

    try:
        thread_identity = (
            refresh_thread_identity(
                thread_id
            )
        )

    except Exception as exc:

        print(
            "[THREAD IDENTITY ERROR] "
            f"thread={thread_id}: "
            f"{exc}"
        )

        thread_identity = {
            "status": "failed",
            "error": str(exc),
        }

    return {
        "linked": True,
        "created_thread": True,

        "story_id": story_id,
        "thread_id": thread_id,

        "candidate_story_id": (
            candidate_id
        ),

        "match_method": (
            "source_entity_id"
        ),

        "source_entity_id": (
            candidate[
                "source_entity_id"
            ]
        ),

        "thread_identity": (
            thread_identity
        ),
    }        

def find_source_entity_candidate(
    story_id: int,
):
    """
    Finds a previous story belonging to the exact same
    source entity.

    Examples:
        senado:174024
        camara:2647298

    This match is deterministic and does not require
    embeddings or JEV.
    """

    with engine.connect() as connection:

        current = connection.execute(
            text("""
                SELECT
                    id,
                    source_entity_id

                FROM stories

                WHERE id = :story_id

                LIMIT 1
            """),
            {
                "story_id": story_id,
            },
        ).mappings().first()

        if not current:
            return None

        source_entity_id = (
            current["source_entity_id"]
        )

        if not source_entity_id:
            return None

        candidate = connection.execute(
            text("""
                SELECT
                    id,
                    title,
                    source,
                    source_entity_id,
                    source_event_type,
                    published_at,
                    discovered_at

                FROM stories

                WHERE
                    id < :story_id

                    AND source_entity_id =
                        :source_entity_id

                ORDER BY
                    id DESC

                LIMIT 1
            """),
            {
                "story_id": story_id,
                "source_entity_id": (
                    source_entity_id
                ),
            },
        ).mappings().first()

    if not candidate:
        return None

    return dict(candidate)


def assign_story_by_source_entity(
    story_id: int,
):
    """
    Assigns a story deterministically when another story
    with the same source_entity_id already exists.

    Returns None if no deterministic match exists.
    In that case auto_assign_story_to_thread() can continue
    with embeddings + JEV.
    """

    candidate = (
        find_source_entity_candidate(
            story_id
        )
    )

    if not candidate:
        return None

    candidate_id = (
        candidate["id"]
    )

    source_entity_id = (
        candidate["source_entity_id"]
    )

    # -----------------------------------------------------
    # DOES CANDIDATE ALREADY HAVE A THREAD?
    # -----------------------------------------------------

    with engine.connect() as connection:

        candidate_thread = connection.execute(
            text("""
                SELECT
                    thread_id

                FROM story_thread_items

                WHERE story_id = :candidate_id

                LIMIT 1
            """),
            {
                "candidate_id": candidate_id,
            },
        ).mappings().first()

    # =====================================================
    # CASE A:
    # EXISTING THREAD
    # =====================================================

    if candidate_thread:

        thread_id = (
            candidate_thread["thread_id"]
        )

        with engine.begin() as connection:

            connection.execute(
                text("""
                    INSERT INTO story_thread_items (
                        thread_id,
                        story_id
                    )

                    VALUES (
                        :thread_id,
                        :story_id
                    )

                    ON CONFLICT DO NOTHING
                """),
                {
                    "thread_id": thread_id,
                    "story_id": story_id,
                },
            )

            connection.execute(
                text("""
                    UPDATE story_threads

                    SET updated_at = NOW()

                    WHERE id = :thread_id
                """),
                {
                    "thread_id": thread_id,
                },
            )

        try:
            thread_identity = (
                refresh_thread_identity(
                    thread_id
                )
            )

        except Exception as exc:

            print(
                "[THREAD IDENTITY ERROR] "
                f"thread={thread_id}: "
                f"{exc}"
            )

            thread_identity = {
                "status": "failed",
                "error": str(exc),
            }

        return {
            "linked": True,
            "created_thread": False,

            "story_id": story_id,
            "thread_id": thread_id,

            "candidate_story_id": (
                candidate_id
            ),

            "match_method": (
                "source_entity_id"
            ),

            "source_entity_id": (
                source_entity_id
            ),

            "thread_identity": (
                thread_identity
            ),
        }

    # =====================================================
    # CASE B:
    # SAME ENTITY, BUT CANDIDATE HAS NO THREAD
    # =====================================================

    with engine.connect() as connection:

        current_story = connection.execute(
            text("""
                SELECT
                    id,
                    title,
                    category

                FROM stories

                WHERE id = :story_id

                LIMIT 1
            """),
            {
                "story_id": story_id,
            },
        ).mappings().first()

    if not current_story:
        return None

    temporary_title = (
        "Thread automático - "
        f"{current_story['title']}"
    )

    with engine.begin() as connection:

        new_thread = connection.execute(
            text("""
                INSERT INTO story_threads (
                    title,
                    summary,
                    category,
                    created_at,
                    updated_at
                )

                VALUES (
                    :title,
                    NULL,
                    :category,
                    NOW(),
                    NOW()
                )

                RETURNING id
            """),
            {
                "title": temporary_title,
                "category": (
                    current_story["category"]
                ),
            },
        ).mappings().first()

        thread_id = (
            new_thread["id"]
        )

        connection.execute(
            text("""
                INSERT INTO story_thread_items (
                    thread_id,
                    story_id
                )

                VALUES (
                    :thread_id,
                    :candidate_id
                )

                ON CONFLICT DO NOTHING
            """),
            {
                "thread_id": thread_id,
                "candidate_id": candidate_id,
            },
        )

        connection.execute(
            text("""
                INSERT INTO story_thread_items (
                    thread_id,
                    story_id
                )

                VALUES (
                    :thread_id,
                    :story_id
                )

                ON CONFLICT DO NOTHING
            """),
            {
                "thread_id": thread_id,
                "story_id": story_id,
            },
        )

    try:
        thread_identity = (
            refresh_thread_identity(
                thread_id
            )
        )

    except Exception as exc:

        print(
            "[THREAD IDENTITY ERROR] "
            f"thread={thread_id}: "
            f"{exc}"
        )

        thread_identity = {
            "status": "failed",
            "error": str(exc),
        }

    return {
        "linked": True,
        "created_thread": True,

        "story_id": story_id,
        "thread_id": thread_id,

        "candidate_story_id": (
            candidate_id
        ),

        "match_method": (
            "source_entity_id"
        ),

        "source_entity_id": (
            source_entity_id
        ),

        "thread_identity": (
            thread_identity
        ),
    }


# =========================================================
# AUTO THREAD
# =========================================================

async def auto_assign_story_to_thread(
    story_id: int,
):
    """
    Tries to associate a story with an existing thread.

    If the best qualified candidate already belongs to a thread,
    the current story is added to that thread.

    If the candidate does not yet belong to a thread,
    a new thread is created containing both stories.

    After a successful association, the thread title and summary
    are regenerated automatically.
    """

    # -----------------------------------------------------
    # IDEMPOTENCY:
    # STORY ALREADY BELONGS TO A THREAD
    # -----------------------------------------------------

    with engine.connect() as connection:
        existing_thread = connection.execute(
            text("""
                SELECT
                    thread_id

                FROM story_thread_items

                WHERE story_id = :story_id

                LIMIT 1
            """),
            {
                "story_id": story_id,
            },
        ).mappings().first()

    if existing_thread:
        return {
            "linked": True,
            "already_linked": True,
            "story_id": story_id,
            "thread_id": existing_thread[
                "thread_id"
            ],
            "reason": (
                "story_already_belongs_to_thread"
            ),
        }

    # -----------------------------------------------------
    # DETERMINISTIC SOURCE ENTITY MATCH
    # -----------------------------------------------------

    deterministic_result = (
        assign_story_by_source_entity(
            story_id
        )
    )

    if deterministic_result:
        return deterministic_result

    # -----------------------------------------------------
    # SEMANTIC FALLBACK:
    # EMBEDDINGS + JEV
    # -----------------------------------------------------

    # -----------------------------------------------------
    # FIND BEST CANDIDATE
    # -----------------------------------------------------

    result = await find_best_thread_candidate(
        story_id
    )

    if not result:
        return {
            "linked": False,
            "story_id": story_id,
            "reason": (
                "thread_candidate_search_failed"
            ),
        }

    candidate = result.get(
        "candidate"
    )

    all_candidates = result.get(
        "all_candidates",
        [],
    )

    qualified_candidates = result.get(
        "qualified_candidates",
        [],
    )

    # -----------------------------------------------------
    # NO QUALIFIED CANDIDATE
    # -----------------------------------------------------

    if not candidate:
        audit = save_thread_match_audit(
            story_id=story_id,
            match_result=result,
        )
        return {
            "linked": False,
            "story_id": story_id,
            "reason": (
                "no_candidate_passed_gate"
            ),

            "thresholds": {
                "standard_match": {
                    "same_thread": 0.60,
                    "direct_continuation": 0.55,
                    "shared_specific_reference": 0.70,
                },

                "strong_reference_match": {
                    "shared_specific_reference": 0.85,
                    "same_thread": 0.45,
                },
            },

            "candidates": all_candidates,
            "qualified_candidates": (
                qualified_candidates
            ),

            "jev": result.get(
                "jev",
                {},
            ),
            "audit": audit,
        }

    # -----------------------------------------------------
    # CANDIDATE DATA
    # -----------------------------------------------------

    candidate_id = candidate.get(
        "story_id"
    )

    if candidate_id is None:
        candidate_id = candidate.get(
            "id"
        )

    if candidate_id is None:
        return {
            "linked": False,
            "story_id": story_id,
            "reason": (
                "candidate_missing_story_id"
            ),
            "candidate": candidate,
        }

    # -----------------------------------------------------
    # CHECK IF CANDIDATE ALREADY HAS A THREAD
    # -----------------------------------------------------

    with engine.connect() as connection:
        candidate_thread = connection.execute(
            text("""
                SELECT
                    thread_id

                FROM story_thread_items

                WHERE story_id = :candidate_id

                LIMIT 1
            """),
            {
                "candidate_id": candidate_id,
            },
        ).mappings().first()

    # =====================================================
    # CASE A:
    # CANDIDATE ALREADY BELONGS TO A THREAD
    # =====================================================

    if candidate_thread:
        thread_id = candidate_thread[
            "thread_id"
        ]

        with engine.begin() as connection:

            connection.execute(
                text("""
                    INSERT INTO story_thread_items (
                        thread_id,
                        story_id
                    )
                    VALUES (
                        :thread_id,
                        :story_id
                    )

                    ON CONFLICT DO NOTHING
                """),
                {
                    "thread_id": thread_id,
                    "story_id": story_id,
                },
            )

            connection.execute(
                text("""
                    UPDATE story_threads

                    SET updated_at = NOW()

                    WHERE id = :thread_id
                """),
                {
                    "thread_id": thread_id,
                },
            )

        # -------------------------------------------------
        # REFRESH THREAD TITLE + SUMMARY
        # -------------------------------------------------

        try:
            thread_identity = (
                refresh_thread_identity(
                    thread_id
                )
            )

        except Exception as exc:
            print(
                f"[THREAD IDENTITY ERROR] "
                f"thread={thread_id}: "
                f"{exc}"
            )

            thread_identity = {
                "status": "failed",
                "error": str(exc),
            }

        audit = save_thread_match_audit(
            story_id=story_id,
            match_result=result,
            selected_candidate_id=(
                candidate_id
            ),
            resulting_thread_id=(
                thread_id
            ),
        )
        return {
            "linked": True,
            "created_thread": False,

            "story_id": story_id,
            "thread_id": thread_id,

            "candidate_story_id": (
                candidate_id
            ),

            "vector_similarity": (
                candidate.get(
                    "vector_similarity"
                )
            ),

            "same_thread_score": (
                candidate.get(
                    "same_thread_score"
                )
            ),

            "direct_continuation_score": (
                candidate.get(
                    "direct_continuation_score"
                )
            ),

            "shared_specific_reference_score": (
                candidate.get(
                    "shared_specific_reference_score"
                )
            ),

            "thread_identity": (
                thread_identity
            ),

            "jev": result.get(
                "jev",
                {},
            ),
            "audit": audit,
        }

    # =====================================================
    # CASE B:
    # CANDIDATE DOES NOT HAVE A THREAD
    # CREATE A NEW THREAD
    # =====================================================

    story = result.get(
        "story",
        {},
    )

    story_title = (
        story.get("title")
        or f"Story {story_id}"
    )

    story_category = story.get(
        "category"
    )

    # Temporary title.
    # It will immediately be replaced by
    # refresh_thread_identity().
    temporary_title = (
        f"Thread automático - "
        f"{story_title}"
    )

    with engine.begin() as connection:

        new_thread = connection.execute(
            text("""
                INSERT INTO story_threads (
                    title,
                    summary,
                    category,
                    created_at,
                    updated_at
                )
                VALUES (
                    :title,
                    NULL,
                    :category,
                    NOW(),
                    NOW()
                )

                RETURNING id
            """),
            {
                "title": temporary_title,
                "category": story_category,
            },
        ).mappings().first()

        thread_id = new_thread[
            "id"
        ]

        # Candidate first
        connection.execute(
            text("""
                INSERT INTO story_thread_items (
                    thread_id,
                    story_id
                )
                VALUES (
                    :thread_id,
                    :candidate_id
                )

                ON CONFLICT DO NOTHING
            """),
            {
                "thread_id": thread_id,
                "candidate_id": candidate_id,
            },
        )

        # Current story
        connection.execute(
            text("""
                INSERT INTO story_thread_items (
                    thread_id,
                    story_id
                )
                VALUES (
                    :thread_id,
                    :story_id
                )

                ON CONFLICT DO NOTHING
            """),
            {
                "thread_id": thread_id,
                "story_id": story_id,
            },
        )

    # -----------------------------------------------------
    # GENERATE REAL THREAD TITLE + SUMMARY
    # -----------------------------------------------------

    try:
        thread_identity = (
            refresh_thread_identity(
                thread_id
            )
        )

    except Exception as exc:
        print(
            f"[THREAD IDENTITY ERROR] "
            f"thread={thread_id}: "
            f"{exc}"
        )

        thread_identity = {
            "status": "failed",
            "error": str(exc),
        }

    audit = save_thread_match_audit(
        story_id=story_id,
        match_result=result,
        selected_candidate_id=(
            candidate_id
        ),
        resulting_thread_id=(
            thread_id
        ),
    )

    return {
        "linked": True,
        "created_thread": True,

        "story_id": story_id,
        "thread_id": thread_id,

        "candidate_story_id": (
            candidate_id
        ),

        "vector_similarity": (
            candidate.get(
                "vector_similarity"
            )
        ),

        "same_thread_score": (
            candidate.get(
                "same_thread_score"
            )
        ),

        "direct_continuation_score": (
            candidate.get(
                "direct_continuation_score"
            )
        ),

        "shared_specific_reference_score": (
            candidate.get(
                "shared_specific_reference_score"
            )
        ),

        "thread_identity": (
            thread_identity
        ),

        "jev": result.get(
            "jev",
            {},
        ),      
        "audit": audit,
    }

# =========================================================
# WHAT CHANGED
# =========================================================

async def run_what_changed(
    story_id: int,
):
    # -----------------------------------------------------
    # CURRENT STORY + THREAD
    # -----------------------------------------------------

    with engine.connect() as connection:
        current = connection.execute(
            text("""
                SELECT
                    s.id,
                    s.title,
                    s.summary,
                    s.published_at,
                    s.discovered_at,
                    i.thread_id

                FROM stories s

                JOIN story_thread_items i
                    ON i.story_id = s.id

                WHERE s.id = :story_id

                LIMIT 1
            """),
            {
                "story_id": story_id,
            },
        ).mappings().first()

    if not current:
        return {
            "success": False,
            "error": (
                "Story does not belong "
                "to a thread"
            ),
        }

    thread_id = current[
        "thread_id"
    ]

    # -----------------------------------------------------
    # PREVIOUS STORIES
    #
    # Temporal order:
    #
    # 1. published_at
    # 2. fallback discovered_at
    # 3. id as deterministic tie-breaker
    # -----------------------------------------------------

    with engine.connect() as connection:
        previous = connection.execute(
            text("""
                SELECT
                    s.id,
                    s.title,
                    s.summary,
                    s.published_at,
                    s.discovered_at

                FROM story_thread_items i

                JOIN stories s
                    ON s.id = i.story_id

                WHERE
                    i.thread_id = :thread_id

                    AND s.id != :story_id

                    AND (
                        COALESCE(
                            s.published_at,
                            s.discovered_at
                        )
                        <
                        COALESCE(
                            :current_published_at,
                            :current_discovered_at
                        )

                        OR (

                            COALESCE(
                                s.published_at,
                                s.discovered_at
                            )
                            =
                            COALESCE(
                                :current_published_at,
                                :current_discovered_at
                            )

                            AND s.id < :story_id
                        )
                    )

                ORDER BY
                    COALESCE(
                        s.published_at,
                        s.discovered_at
                    ) ASC,

                    s.id ASC
            """),
            {
                "thread_id": thread_id,
                "story_id": story_id,
                "current_published_at": (
                    current["published_at"]
                ),
                "current_discovered_at": (
                    current["discovered_at"]
                ),
            },
        ).mappings().all()

    # -----------------------------------------------------
    # FIRST STORY OF THREAD
    # -----------------------------------------------------

    if not previous:
        return {
            "story_id": story_id,
            "thread_id": thread_id,
            "has_history": False,
            "message": (
                "Esta é a primeira story "
                "do thread."
            ),
        }

    # -----------------------------------------------------
    # JEV CHANGE ANALYSIS
    # -----------------------------------------------------

    jev_result = (
        await analyze_story_changes(
            current_story=dict(current),
            previous_stories=[
                dict(row)
                for row in previous
            ],
        )
    )

    analysis = (
        interpret_story_changes(
            jev_result
        )
    )

    # -----------------------------------------------------
    # GENERATIVE WHAT CHANGED
    # -----------------------------------------------------

    change_summary = None
    generator_metadata = None

    try:
        generated = generate_change_summary(
            current_story=dict(current),

            previous_stories=[
                dict(row)
                for row in previous
            ],

            changes=analysis,
        )

        change_summary = (
            generated["summary"]
        )

        generator_metadata = (
            generated["metadata"]
        )

    except Exception as exc:
        print(
            f"[GENERATOR ERROR] "
            f"story={story_id}: "
            f"{exc}"
        )

        generator_metadata = {
            "provider": "OpenAI",
            "status": "failed",
            "error": str(exc),
        }

    # -----------------------------------------------------
    # METADATA
    # -----------------------------------------------------

    ai_metadata = {
        "provider": "TypeSafe",
        "model": jev_result.get(
            "model"
        ),
        "usage": jev_result.get(
            "usage"
        ),
        "answers": jev_result.get(
            "answers"
        ),
        "compared_story_ids": [
            row["id"]
            for row in previous
        ],
    }

    # -----------------------------------------------------
    # SAVE ANALYSIS
    # -----------------------------------------------------

    with engine.begin() as connection:
        connection.execute(
            text("""
                INSERT INTO story_changes (
                    story_id,
                    thread_id,
                    has_meaningful_change,
                    new_information,
                    new_actor,
                    new_measure,
                    status_change,
                    date_change,
                    quantitative_change,
                    contradiction,
                    ai_metadata,
                    change_summary,
                    generator_metadata
                )
                VALUES (
                    :story_id,
                    :thread_id,
                    :meaningful_change,
                    :new_information,
                    :new_actor,
                    :new_measure,
                    :status_change,
                    :date_change,
                    :quantitative_change,
                    :contradiction,
                    CAST(
                        :ai_metadata
                        AS JSONB
                    ),
                    :change_summary,
                    CAST(
                        :generator_metadata
                        AS JSONB
                    )
                )

                ON CONFLICT (story_id)
                DO UPDATE SET

                    thread_id =
                        EXCLUDED.thread_id,

                    has_meaningful_change =
                        EXCLUDED.has_meaningful_change,

                    new_information =
                        EXCLUDED.new_information,

                    new_actor =
                        EXCLUDED.new_actor,

                    new_measure =
                        EXCLUDED.new_measure,

                    status_change =
                        EXCLUDED.status_change,

                    date_change =
                        EXCLUDED.date_change,

                    quantitative_change =
                        EXCLUDED.quantitative_change,

                    contradiction =
                        EXCLUDED.contradiction,

                    ai_metadata =
                        EXCLUDED.ai_metadata,
                    
                    change_summary =
                        EXCLUDED.change_summary,

                    generator_metadata =
                        EXCLUDED.generator_metadata,

                    created_at = NOW()
            """),
            {
                "story_id": story_id,
                "thread_id": thread_id,

                "meaningful_change": (
                    analysis[
                        "meaningful_change"
                    ]
                ),

                "new_information": (
                    analysis[
                        "new_information"
                    ]
                ),

                "new_actor": (
                    analysis[
                        "new_actor"
                    ]
                ),

                "new_measure": (
                    analysis[
                        "new_measure"
                    ]
                ),

                "status_change": (
                    analysis[
                        "status_change"
                    ]
                ),

                "date_change": (
                    analysis[
                        "date_change"
                    ]
                ),

                "quantitative_change": (
                    analysis[
                        "quantitative_change"
                    ]
                ),

                "contradiction": (
                    analysis[
                        "contradiction"
                    ]
                ),

                "ai_metadata": (
                    json.dumps(
                        ai_metadata,
                        ensure_ascii=False,
                    )
                ),
                "change_summary": (
                    change_summary
                ),

                "generator_metadata": (
                    json.dumps(
                        generator_metadata,
                        ensure_ascii=False,
                    )
                ),
            },
        )

    return {
        "story_id": story_id,
        "thread_id": thread_id,
        "has_history": True,

        "compared_with": len(
            previous
        ),

        "compared_story_ids": [
            row["id"]
            for row in previous
        ],

        "changes": analysis,

        "change_summary": (
            change_summary
        ),

        "generator": (
            generator_metadata
        ),

        "jev": {
            "model": jev_result.get(
                "model"
            ),
            "usage": jev_result.get(
                "usage"
            ),
        },
    }

def create_story_alert(
    story_id: int,
    change_result: dict | None = None,
):
    """
    Evaluates whether a story should create a newsroom alert.

    Alert Engine V2 combines:
    - story priority
    - meaningful change
    - specific change dimensions

    If an alert is created:
    - its initial pending state is added to history
    - deliveries are automatically created for enabled
      notification channels that match their thresholds
    """

    # -----------------------------------------------------
    # LOAD STORY + THREAD
    # -----------------------------------------------------

    with engine.connect() as connection:
        story = connection.execute(
            text("""
                SELECT
                    s.id,
                    s.title,
                    s.summary,
                    s.priority,
                    s.priority_score,
                    s.category,
                    i.thread_id

                FROM stories s

                LEFT JOIN story_thread_items i
                    ON i.story_id = s.id

                WHERE s.id = :story_id

                LIMIT 1
            """),
            {
                "story_id": story_id,
            },
        ).mappings().first()

    if not story:
        return {
            "created": False,
            "reason": "story_not_found",
        }

    # -----------------------------------------------------
    # STORY PRIORITY
    # -----------------------------------------------------

    priority_score = (
        float(
            story["priority_score"]
        )
        if story["priority_score"] is not None
        else 0.0
    )

    # -----------------------------------------------------
    # CHANGE SCORES
    # -----------------------------------------------------

    meaningful_change = 0.0
    new_information = 0.0
    new_actor = 0.0
    new_measure = 0.0
    status_change = 0.0
    date_change = 0.0
    quantitative_change = 0.0
    contradiction = 0.0

    change_summary = None

    if change_result:

        changes = change_result.get(
            "changes",
            {},
        )

        meaningful_change = float(
            changes.get(
                "meaningful_change",
                0.0,
            )
            or 0.0
        )

        new_information = float(
            changes.get(
                "new_information",
                0.0,
            )
            or 0.0
        )

        new_actor = float(
            changes.get(
                "new_actor",
                0.0,
            )
            or 0.0
        )

        new_measure = float(
            changes.get(
                "new_measure",
                0.0,
            )
            or 0.0
        )

        status_change = float(
            changes.get(
                "status_change",
                0.0,
            )
            or 0.0
        )

        date_change = float(
            changes.get(
                "date_change",
                0.0,
            )
            or 0.0
        )

        quantitative_change = float(
            changes.get(
                "quantitative_change",
                0.0,
            )
            or 0.0
        )

        contradiction = float(
            changes.get(
                "contradiction",
                0.0,
            )
            or 0.0
        )

        change_summary = (
            change_result.get(
                "change_summary"
            )
        )

    # -----------------------------------------------------
    # ALERT RULES V2
    # -----------------------------------------------------

    high_priority = (
        priority_score >= 0.80
    )

    strong_change = (
        meaningful_change >= 0.70
        and (
            new_information >= 0.60
            or new_measure >= 0.60
            or status_change >= 0.60
            or contradiction >= 0.70
            or quantitative_change >= 0.70
        )
    )

    medium_attention = (
        priority_score >= 0.60
        and meaningful_change >= 0.60
    )

    # -----------------------------------------------------
    # NO ALERT
    # -----------------------------------------------------

    if (
        not high_priority
        and not strong_change
        and not medium_attention
    ):
        return {
            "created": False,
            "reason": "below_alert_threshold",

            "priority_score": (
                priority_score
            ),

            "meaningful_change_score": (
                meaningful_change
            ),

            "signals": {
                "new_information": (
                    new_information
                ),
                "new_actor": (
                    new_actor
                ),
                "new_measure": (
                    new_measure
                ),
                "status_change": (
                    status_change
                ),
                "date_change": (
                    date_change
                ),
                "quantitative_change": (
                    quantitative_change
                ),
                "contradiction": (
                    contradiction
                ),
            },
        }

    # -----------------------------------------------------
    # ALERT TYPE
    # -----------------------------------------------------

    if high_priority and strong_change:
        alert_type = (
            "high_priority_change"
        )

    elif strong_change:
        alert_type = (
            "breaking_change"
        )

    elif medium_attention:
        alert_type = (
            "attention"
        )

    else:
        alert_type = (
            "high_priority_story"
        )

    # -----------------------------------------------------
    # MESSAGE
    # -----------------------------------------------------

    if change_summary:
        message = change_summary
    else:
        message = (
            story["summary"]
            or story["title"]
        )

    alert_title = story["title"]

    # -----------------------------------------------------
    # ALERT DEDUPE
    # -----------------------------------------------------

    with engine.connect() as connection:
        existing = connection.execute(
            text("""
                SELECT
                    id,
                    alert_type,
                    status

                FROM newsroom_alerts

                WHERE
                    story_id = :story_id
                    AND alert_type = :alert_type

                LIMIT 1
            """),
            {
                "story_id": story_id,
                "alert_type": alert_type,
            },
        ).mappings().first()

    if existing:
        return {
            "created": False,
            "reason": "alert_already_exists",
            "alert_id": existing["id"],
            "alert_type": existing[
                "alert_type"
            ],
            "status": existing[
                "status"
            ],
        }

    # -----------------------------------------------------
    # METADATA
    # -----------------------------------------------------

    metadata = {
        "rule_version": "v2",

        "thresholds": {
            "high_priority": 0.80,

            "strong_change": {
                "meaningful_change": 0.70,
                "new_information": 0.60,
                "new_measure": 0.60,
                "status_change": 0.60,
                "contradiction": 0.70,
                "quantitative_change": 0.70,
            },

            "medium_attention": {
                "priority_score": 0.60,
                "meaningful_change": 0.60,
            },
        },

        "signals": {
            "priority_score": (
                priority_score
            ),

            "meaningful_change": (
                meaningful_change
            ),

            "new_information": (
                new_information
            ),

            "new_actor": (
                new_actor
            ),

            "new_measure": (
                new_measure
            ),

            "status_change": (
                status_change
            ),

            "date_change": (
                date_change
            ),

            "quantitative_change": (
                quantitative_change
            ),

            "contradiction": (
                contradiction
            ),
        },

        "category": (
            story["category"]
        ),

        "priority": (
            story["priority"]
        ),
    }

    # -----------------------------------------------------
    # SAVE ALERT + INITIAL HISTORY
    # -----------------------------------------------------

    with engine.begin() as connection:

        alert = connection.execute(
            text("""
                INSERT INTO newsroom_alerts (
                    story_id,
                    thread_id,
                    alert_type,
                    title,
                    message,
                    priority_score,
                    meaningful_change_score,
                    status,
                    metadata
                )
                VALUES (
                    :story_id,
                    :thread_id,
                    :alert_type,
                    :title,
                    :message,
                    :priority_score,
                    :meaningful_change_score,
                    'pending',
                    CAST(
                        :metadata
                        AS JSONB
                    )
                )

                RETURNING id
            """),
            {
                "story_id": story_id,

                "thread_id": (
                    story["thread_id"]
                ),

                "alert_type": (
                    alert_type
                ),

                "title": (
                    alert_title
                ),

                "message": message,

                "priority_score": (
                    priority_score
                ),

                "meaningful_change_score": (
                    meaningful_change
                ),

                "metadata": json.dumps(
                    metadata,
                    ensure_ascii=False,
                ),
            },
        ).mappings().first()

        # -------------------------------------------------
        # INITIAL STATUS HISTORY
        # -------------------------------------------------

        connection.execute(
            text("""
                INSERT INTO alert_status_history (
                    alert_id,
                    from_status,
                    to_status,
                    source
                )
                VALUES (
                    :alert_id,
                    NULL,
                    'pending',
                    'system'
                )
            """),
            {
                "alert_id": (
                    alert["id"]
                ),
            },
        )

    # -----------------------------------------------------
    # CREATE AUTOMATIC DELIVERIES
    #
    # This happens after the alert transaction has been
    # committed, because create_deliveries_for_alert()
    # opens its own database transactions.
    # -----------------------------------------------------

    try:
        delivery_setup = (
            create_deliveries_for_alert(
                alert["id"]
            )
        )

    except Exception as exc:
        print(
            f"[DELIVERY SETUP ERROR] "
            f"alert={alert['id']}: "
            f"{exc}"
        )

        delivery_setup = {
            "alert_id": alert["id"],
            "created": 0,
            "status": "failed",
            "error": str(exc),
        }

    # -----------------------------------------------------
    # RESULT
    # -----------------------------------------------------

    return {
        "created": True,

        "alert_id": (
            alert["id"]
        ),

        "alert_type": (
            alert_type
        ),

        "story_id": (
            story_id
        ),

        "thread_id": (
            story["thread_id"]
        ),

        "priority_score": (
            priority_score
        ),

        "meaningful_change_score": (
            meaningful_change
        ),

        "signals": {
            "new_information": (
                new_information
            ),

            "new_actor": (
                new_actor
            ),

            "new_measure": (
                new_measure
            ),

            "status_change": (
                status_change
            ),

            "date_change": (
                date_change
            ),

            "quantitative_change": (
                quantitative_change
            ),

            "contradiction": (
                contradiction
            ),
        },

        "message": (
            message
        ),

        "delivery_setup": (
            delivery_setup
        ),
    }

# =========================================================
# CÂMARA INGESTION
# =========================================================

async def run_camara_ingestion():
    try:
        items = await fetch_camara_stories()

        result = await ingest_source_stories(
            items,
            engine=engine,
            classify_story=classify_story,
            interpret_classification=(
                interpret_classification
            ),
            build_ai_metadata=(
                build_ai_metadata
            ),
            auto_assign_story_to_thread=(
                auto_assign_story_to_thread
            ),
            run_what_changed=(
                run_what_changed
            ),
            create_story_alert=(
                create_story_alert
            ),
        )

        return {
            "success": True,
            "source": "Câmara dos Deputados",
            **result,
        }

    except Exception as exc:
        print(
            "[CAMARA INGESTION ERROR]",
            str(exc),
        )

        return {
            "success": False,
            "source": "Câmara dos Deputados",
            "error": str(exc),
        }

# =========================================================
# SENADO INGESTION
# =========================================================

async def run_senado_ingestion():
    try:
        items = await fetch_senado_stories(
            days=1,
            limit=10,
        )

        result = await ingest_source_stories(
            items,
            engine=engine,
            classify_story=classify_story,
            interpret_classification=(
                interpret_classification
            ),
            build_ai_metadata=(
                build_ai_metadata
            ),
            auto_assign_story_to_thread=(
                auto_assign_story_to_thread
            ),
            run_what_changed=(
                run_what_changed
            ),
            create_story_alert=(
                create_story_alert
            ),
        )

        return {
            "success": True,
            "source": "Senado Federal",
            **result,
        }

    except Exception as exc:
        print(
            "[SENADO INGESTION ERROR]",
            str(exc),
        )

        return {
            "success": False,
            "source": "Senado Federal",
            "error": str(exc),
        }

# =========================================================
# SCHEDULER
# =========================================================

async def scheduled_camara_ingestion():
    try:
        result = (
            await run_camara_ingestion()
        )

        print(
            "[CÂMARA INGESTION]",
            result,
        )

    except Exception as exc:
        print(
            "[CÂMARA INGESTION ERROR]",
            str(exc),
        )

async def scheduled_senado_ingestion():
    try:
        result = (
            await run_senado_ingestion()
        )

        print(
            "[SENADO INGESTION]",
            result,
        )

    except Exception as exc:
        print(
            "[SENADO INGESTION ERROR]",
            str(exc),
        )

async def scheduled_delivery_processing():
    try:
        recovery = (
            recover_stuck_deliveries(
                stuck_minutes=5
            )
        )

        if recovery.get(
            "recovered",
            0,
        ) > 0:
            print(
                "[DELIVERY RECOVERY]",
                recovery,
            )

        result = (
            process_pending_deliveries(
                limit=20
            )
        )

        if result.get(
            "found",
            0,
        ) > 0:
            print(
                "[DELIVERY WORKER]",
                result,
            )

    except Exception as exc:
        print(
            "[DELIVERY WORKER ERROR]",
            str(exc),
        )

# =========================================================
# LIFESPAN
# =========================================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    # -----------------------------------------------------
    # CÂMARA INGESTION
    # -----------------------------------------------------

    scheduler.add_job(
        scheduled_camara_ingestion,
        "interval",
        minutes=CAMARA_POLL_MINUTES,
        id="camara_ingestion",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # -----------------------------------------------------
    # SENADO INGESTION
    # -----------------------------------------------------

    scheduler.add_job(
        scheduled_senado_ingestion,
        "interval",
        minutes=SENADO_POLL_MINUTES,
        id="senado_ingestion",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # -----------------------------------------------------
    # DELIVERY WORKER
    # -----------------------------------------------------

    scheduler.add_job(
        scheduled_delivery_processing,
        "interval",
        minutes=DELIVERY_POLL_MINUTES,
        id="delivery_worker",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # -----------------------------------------------------
    # START SCHEDULER
    # -----------------------------------------------------

    scheduler.start()

    print(
        "[SCHEDULER] Câmara ingestion ativa "
        f"a cada {CAMARA_POLL_MINUTES} minutos"
    )
    print(
        "[SCHEDULER] Senado ingestion ativa "
        f"a cada {SENADO_POLL_MINUTES} minutos"
    )
    print(
        "[SCHEDULER] Delivery worker ativo "
        f"a cada {DELIVERY_POLL_MINUTES} minuto(s)"
    )

    yield

    # -----------------------------------------------------
    # SHUTDOWN
    # -----------------------------------------------------

    scheduler.shutdown()

    print(
        "[SCHEDULER] encerrado"
    )

# =========================================================
# APP
# =========================================================

app = FastAPI(
    title="Newsroom AI API",
    version="0.3.0",
    lifespan=lifespan,
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# ROOT
# =========================================================

@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "Newsroom AI",
        "version": "0.3.0",
    }


# =========================================================
# STORIES
# =========================================================

@app.get("/stories")
def get_stories():
    with engine.connect() as connection:
        rows = connection.execute(
            text("""
                SELECT
                    id,
                    title,
                    source,
                    source_type,
                    time,
                    priority,
                    category,
                    priority_score,
                    category_score,
                    summary,
                    external_id,
                    url,
                    published_at,
                    discovered_at,
                    status,
                    ai_metadata
                FROM stories
                WHERE status = 'new'
                ORDER BY
                    discovered_at DESC,
                    published_at DESC
            """)
        ).mappings().all()

    return [
        dict(row)
        for row in rows
    ]


@app.get("/stories/all")
def get_all_stories():
    with engine.connect() as connection:
        rows = connection.execute(
            text("""
                SELECT
                    id,
                    title,
                    source,
                    source_type,
                    time,
                    priority,
                    category,
                    priority_score,
                    category_score,
                    summary,
                    external_id,
                    url,
                    published_at,
                    discovered_at,
                    status,
                    ai_metadata
                FROM stories
                ORDER BY
                    discovered_at DESC,
                    published_at DESC
            """)
        ).mappings().all()

    return [
        dict(row)
        for row in rows
    ]


# =========================================================
# SIMILAR STORIES
# =========================================================

@app.get(
    "/stories/{story_id}/similar"
)
def get_similar_stories(
    story_id: int,
    limit: int = Query(
        default=5,
        ge=1,
        le=20,
    ),
    min_similarity: float = Query(
        default=0.50,
        ge=0.0,
        le=1.0,
    ),
):
    with engine.connect() as connection:
        story = connection.execute(
            text("""
                SELECT
                    id,
                    title,
                    summary
                FROM stories
                WHERE id = :story_id
                LIMIT 1
            """),
            {
                "story_id": story_id,
            },
        ).mappings().first()

    if not story:
        return {
            "success": False,
            "error": "Story not found",
        }

    embedding = embed_story(
        title=story["title"],
        summary=story["summary"],
    )

    embedding_string = (
        embedding_to_string(
            embedding
        )
    )

    with engine.connect() as connection:
        rows = connection.execute(
            text("""
                SELECT
                    s.id,
                    s.title,
                    s.source,
                    s.priority,
                    s.category,
                    s.summary,
                    s.url,
                    s.published_at,
                    s.discovered_at,

                    1 - (
                        e.embedding <=>
                        CAST(
                            :query_embedding
                            AS vector
                        )
                    ) AS similarity

                FROM story_embeddings e

                JOIN stories s
                    ON s.id = e.story_id

                WHERE
                    s.id != :story_id

                    AND (
                        1 - (
                            e.embedding <=>
                            CAST(
                                :query_embedding
                                AS vector
                            )
                        )
                    ) >= :min_similarity

                ORDER BY
                    e.embedding <=>
                    CAST(
                        :query_embedding
                        AS vector
                    )

                LIMIT :limit
            """),
            {
                "story_id": story_id,
                "query_embedding": (
                    embedding_string
                ),
                "min_similarity": (
                    min_similarity
                ),
                "limit": limit,
            },
        ).mappings().all()

    return {
        "story_id": story_id,
        "story_title": story["title"],
        "min_similarity": (
            min_similarity
        ),
        "count": len(rows),
        "results": [
            {
                **dict(row),
                "similarity": round(
                    float(
                        row["similarity"]
                    ),
                    4,
                ),
            }
            for row in rows
        ],
    }


# =========================================================
# THREAD CANDIDATES
# =========================================================

@app.get(
    "/stories/{story_id}/thread-candidates"
)
async def get_thread_candidates(
    story_id: int,
):
    match = await find_best_thread_candidate(
        story_id
    )

    if not match:
        return {
            "story_id": story_id,
            "candidates": [],
        }

    story = match["story"]

    return {
        "story": {
            "id": story["id"],
            "title": story["title"],
            "category": (
                story["category"]
            ),
        },
        "candidates": (
            match["all_candidates"]
        ),
        "jev": match["jev"],
    }


# =========================================================
# AUTO THREAD
# =========================================================

@app.post(
    "/stories/{story_id}/auto-thread"
)
async def auto_thread_story(
    story_id: int,
):
    return (
        await auto_assign_story_to_thread(
            story_id
        )
    )


# =========================================================
# WHAT CHANGED
# =========================================================

@app.post(
    "/stories/{story_id}/what-changed"
)
async def analyze_what_changed(
    story_id: int,
):
    return await run_what_changed(
        story_id
    )


# =========================================================
# GET SAVED WHAT-CHANGED
# =========================================================

@app.get(
    "/stories/{story_id}/changes"
)
def get_story_changes(
    story_id: int,
):
    with engine.connect() as connection:
        row = connection.execute(
            text("""
                SELECT
                    story_id,
                    thread_id,
                    has_meaningful_change,
                    new_information,
                    new_actor,
                    new_measure,
                    status_change,
                    date_change,
                    quantitative_change,
                    contradiction,
                    ai_metadata,
                    created_at,
                    change_summary,
                    generator_metadata

                FROM story_changes

                WHERE story_id = :story_id
            """),
            {
                "story_id": story_id,
            },
        ).mappings().first()

    if not row:
        return {
            "story_id": story_id,
            "changes": None,
        }

    return dict(row)

# =========================================================
# STORY -> THREAD
# =========================================================

@app.get(
    "/stories/{story_id}/thread"
)
def get_story_thread(
    story_id: int,
):
    with engine.connect() as connection:
        row = connection.execute(
            text("""
                SELECT
                    t.id,
                    t.title,
                    t.summary,
                    t.category,
                    t.created_at,
                    t.updated_at

                FROM story_thread_items i

                JOIN story_threads t
                    ON t.id = i.thread_id

                WHERE i.story_id = :story_id
            """),
            {
                "story_id": story_id,
            },
        ).mappings().first()

    if not row:
        return {
            "thread": None,
        }

    return {
        "thread": dict(row),
    }


# =========================================================
# STORY DETAIL
# =========================================================

@app.get("/stories/{story_id}")
def get_story(
    story_id: int,
):
    with engine.connect() as connection:
        row = connection.execute(
            text("""
                SELECT
                    id,
                    title,
                    source,
                    source_type,
                    time,
                    priority,
                    category,
                    priority_score,
                    category_score,
                    summary,
                    external_id,
                    url,
                    published_at,
                    discovered_at,
                    status,
                    ai_metadata
                FROM stories
                WHERE id = :story_id
                LIMIT 1
            """),
            {
                "story_id": story_id,
            },
        ).mappings().first()

    if not row:
        return {
            "success": False,
            "error": "Story not found",
        }

    return dict(row)


# =========================================================
# STATUS
# =========================================================

@app.patch(
    "/stories/{story_id}/status"
)
def update_story_status(
    story_id: int,
    payload: StoryStatusUpdate,
):
    allowed_statuses = {
        "new",
        "reviewed",
        "important",
        "ignored",
    }

    if (
        payload.status
        not in allowed_statuses
    ):
        return {
            "success": False,
            "error": "Invalid status",
            "allowed_statuses": sorted(
                allowed_statuses
            ),
        }

    with engine.begin() as connection:
        updated = connection.execute(
            text("""
                UPDATE stories
                SET status = :status
                WHERE id = :story_id
                RETURNING
                    id,
                    status
            """),
            {
                "story_id": story_id,
                "status": payload.status,
            },
        ).mappings().first()

    if not updated:
        return {
            "success": False,
            "error": "Story not found",
        }

    return {
        "success": True,
        "story_id": updated["id"],
        "status": updated["status"],
    }


# =========================================================
# THREADS
# =========================================================

@app.post("/threads")
def create_thread(
    payload: ThreadCreate,
):
    with engine.begin() as connection:
        thread = connection.execute(
            text("""
                INSERT INTO story_threads (
                    title,
                    summary,
                    category
                )
                VALUES (
                    :title,
                    :summary,
                    :category
                )
                RETURNING
                    id,
                    title,
                    summary,
                    category,
                    created_at,
                    updated_at
            """),
            {
                "title": payload.title,
                "summary": payload.summary,
                "category": payload.category,
            },
        ).mappings().first()

    return dict(thread)


@app.get("/threads")
def get_threads():
    with engine.connect() as connection:
        rows = connection.execute(
            text("""
                SELECT
                    t.id,
                    t.title,
                    t.summary,
                    t.category,
                    t.created_at,
                    t.updated_at,

                    COUNT(
                        i.story_id
                    ) AS story_count

                FROM story_threads t

                LEFT JOIN story_thread_items i
                    ON i.thread_id = t.id

                GROUP BY
                    t.id,
                    t.title,
                    t.summary,
                    t.category,
                    t.created_at,
                    t.updated_at

                ORDER BY
                    t.updated_at DESC
            """)
        ).mappings().all()

    return [
        dict(row)
        for row in rows
    ]


@app.post(
    "/threads/{thread_id}/stories/{story_id}"
)
def add_story_to_thread(
    thread_id: int,
    story_id: int,
):
    with engine.begin() as connection:
        thread_exists = (
            connection.execute(
                text("""
                    SELECT 1
                    FROM story_threads
                    WHERE id = :thread_id
                """),
                {
                    "thread_id": (
                        thread_id
                    ),
                },
            ).first()
        )

        if not thread_exists:
            return {
                "success": False,
                "error": (
                    "Thread not found"
                ),
            }

        story_exists = (
            connection.execute(
                text("""
                    SELECT 1
                    FROM stories
                    WHERE id = :story_id
                """),
                {
                    "story_id": (
                        story_id
                    ),
                },
            ).first()
        )

        if not story_exists:
            return {
                "success": False,
                "error": (
                    "Story not found"
                ),
            }

        already_linked = (
            connection.execute(
                text("""
                    SELECT thread_id
                    FROM story_thread_items
                    WHERE story_id = :story_id
                """),
                {
                    "story_id": (
                        story_id
                    ),
                },
            ).mappings().first()
        )

        if already_linked:
            return {
                "success": False,
                "error": (
                    "Story already belongs "
                    "to a thread"
                ),
                "thread_id": (
                    already_linked[
                        "thread_id"
                    ]
                ),
            }

        connection.execute(
            text("""
                INSERT INTO story_thread_items (
                    thread_id,
                    story_id
                )
                VALUES (
                    :thread_id,
                    :story_id
                )
            """),
            {
                "thread_id": thread_id,
                "story_id": story_id,
            },
        )

        connection.execute(
            text("""
                UPDATE story_threads
                SET updated_at = NOW()
                WHERE id = :thread_id
            """),
            {
                "thread_id": thread_id,
            },
        )

    return {
        "success": True,
        "thread_id": thread_id,
        "story_id": story_id,
    }


@app.get("/threads/{thread_id}")
def get_thread(thread_id: int):
    with engine.connect() as connection:

        thread = connection.execute(
            text("""
                SELECT
                    id,
                    title,
                    summary,
                    category,
                    created_at,
                    updated_at

                FROM story_threads

                WHERE id = :thread_id
            """),
            {
                "thread_id": thread_id,
            },
        ).mappings().first()

        if not thread:
            raise HTTPException(
                status_code=404,
                detail="Thread not found",
            )

        stories = connection.execute(
            text("""
                SELECT
                    s.id,
                    s.title,
                    s.source,
                    s.summary,
                    s.url,
                    s.category,
                    s.priority,
                    s.priority_score,
                    s.category_score,
                    s.published_at,
                    s.discovered_at,
                    s.status,

                    c.has_meaningful_change,
                    c.new_information,
                    c.new_actor,
                    c.new_measure,
                    c.status_change,
                    c.date_change,
                    c.quantitative_change,
                    c.contradiction,
                    c.change_summary,
                    c.ai_metadata AS change_ai_metadata,
                    c.generator_metadata,
                    c.created_at AS change_created_at

                FROM story_thread_items i

                JOIN stories s
                    ON s.id = i.story_id

                LEFT JOIN story_changes c
                    ON c.story_id = s.id

                WHERE i.thread_id = :thread_id

                ORDER BY
                    COALESCE(
                        s.published_at,
                        s.discovered_at
                    ) ASC,
                    s.id ASC
            """),
            {
                "thread_id": thread_id,
            },
        ).mappings().all()

    return {
        "thread": dict(thread),
        "stories": [
            dict(story)
            for story in stories
        ],
        "story_count": len(stories),
    }


# =========================================================
# CÂMARA
# =========================================================

@app.get(
    "/sources/camara/propositions"
)
async def get_camara_propositions():
    propositions = (
        await fetch_recent_propositions()
    )

    return [
        {
            "id": item.get("id"),
            "type": item.get(
                "siglaTipo"
            ),
            "number": item.get(
                "numero"
            ),
            "year": item.get(
                "ano"
            ),
            "summary": item.get(
                "ementa"
            ),
            "url": item.get(
                "uri"
            ),
        }
        for item in propositions
    ]


@app.post("/ingest/camara")
async def ingest_camara():
    return (
        await run_camara_ingestion()
    )


# =========================================================
# JEV
# =========================================================

@app.get("/jev/models")
async def jev_models():
    return await get_models()


@app.get("/jev/test")
async def test_jev():
    title = "PL 5501/2026"

    summary = (
        "Altera a Lei nº 14.852, "
        "de 3 de maio de 2024, "
        "para estabelecer incentivos fiscais "
        "à formação de recursos humanos "
        "para a Indústria de Jogos Eletrônicos."
    )

    result = await classify_story(
        title=title,
        summary=summary,
    )

    classification = (
        interpret_classification(
            result
        )
    )

    return {
        "raw": result,
        "classification": (
            classification
        ),
    }


# =========================================================
# AI BACKFILL
# =========================================================

@app.post("/ai/backfill")
async def ai_backfill():
    with engine.connect() as connection:
        stories = connection.execute(
            text("""
                SELECT
                    id,
                    title,
                    summary
                FROM stories
                WHERE ai_metadata IS NULL
                ORDER BY id
            """)
        ).mappings().all()

    updated = 0
    failed = 0
    errors = []

    for story in stories:
        try:
            jev_result = (
                await classify_story(
                    title=story["title"],
                    summary=story[
                        "summary"
                    ],
                )
            )

            classification = (
                interpret_classification(
                    jev_result
                )
            )

            ai_metadata = (
                build_ai_metadata(
                    jev_result,
                    classification,
                )
            )

            with engine.begin() as connection:
                connection.execute(
                    text("""
                        UPDATE stories
                        SET
                            priority =
                                :priority,

                            category =
                                :category,

                            priority_score =
                                :priority_score,

                            category_score =
                                :category_score,

                            ai_metadata =
                                CAST(
                                    :ai_metadata
                                    AS JSONB
                                )

                        WHERE
                            id = :story_id
                    """),
                    {
                        "story_id": (
                            story["id"]
                        ),
                        "priority": (
                            classification[
                                "priority"
                            ]
                        ),
                        "category": (
                            classification[
                                "category"
                            ]
                        ),
                        "priority_score": (
                            classification[
                                "priority_score"
                            ]
                        ),
                        "category_score": (
                            classification[
                                "category_score"
                            ]
                        ),
                        "ai_metadata": (
                            json.dumps(
                                ai_metadata,
                                ensure_ascii=False,
                            )
                        ),
                    },
                )

            updated += 1

        except Exception as exc:
            failed += 1

            errors.append(
                {
                    "story_id": (
                        story["id"]
                    ),
                    "error": str(exc),
                }
            )

    return {
        "found": len(stories),
        "updated": updated,
        "failed": failed,
        "errors": errors,
    }


# =========================================================
# AI RECLASSIFY SOURCE
# =========================================================

@app.post("/ai/reclassify-source")
async def ai_reclassify_source(
    source: str = Query(...),
):
    """
    Reclassifies every story for one source using the current
    JEV classification pipeline. Existing saved What Changed
    scores are reused when the Alert Engine is reevaluated.
    """

    with engine.connect() as connection:
        stories = connection.execute(
            text("""
                SELECT
                    s.id,
                    s.title,
                    s.summary,
                    c.story_id AS change_story_id,
                    c.has_meaningful_change,
                    c.new_information,
                    c.new_actor,
                    c.new_measure,
                    c.status_change,
                    c.date_change,
                    c.quantitative_change,
                    c.contradiction,
                    c.change_summary
                FROM stories s
                LEFT JOIN story_changes c
                    ON c.story_id = s.id
                WHERE s.source = :source
                ORDER BY s.id ASC
            """),
            {
                "source": source,
            },
        ).mappings().all()

    updated = 0
    failed = 0
    alerts_created = 0
    results = []

    for story in stories:
        try:
            jev_result = await classify_story(
                title=(story["title"] or ""),
                summary=(story["summary"] or ""),
            )

            classification = interpret_classification(
                jev_result
            )

            ai_metadata = build_ai_metadata(
                jev_result,
                classification,
            )

            with engine.begin() as connection:
                connection.execute(
                    text("""
                        UPDATE stories
                        SET
                            priority = :priority,
                            category = :category,
                            priority_score = :priority_score,
                            category_score = :category_score,
                            ai_metadata = CAST(
                                :ai_metadata AS JSONB
                            )
                        WHERE id = :story_id
                    """),
                    {
                        "story_id": story["id"],
                        "priority": classification["priority"],
                        "category": classification["category"],
                        "priority_score": classification["priority_score"],
                        "category_score": classification["category_score"],
                        "ai_metadata": json.dumps(
                            ai_metadata,
                            ensure_ascii=False,
                        ),
                    },
                )

            change_result = None

            if story["change_story_id"] is not None:
                change_result = {
                    "story_id": story["id"],
                    "has_history": True,
                    "changes": {
                        "meaningful_change": float(story["has_meaningful_change"] or 0.0),
                        "new_information": float(story["new_information"] or 0.0),
                        "new_actor": float(story["new_actor"] or 0.0),
                        "new_measure": float(story["new_measure"] or 0.0),
                        "status_change": float(story["status_change"] or 0.0),
                        "date_change": float(story["date_change"] or 0.0),
                        "quantitative_change": float(story["quantitative_change"] or 0.0),
                        "contradiction": float(story["contradiction"] or 0.0),
                    },
                    "change_summary": story["change_summary"],
                }

            alert_result = create_story_alert(
                story["id"],
                change_result=change_result,
            )

            if alert_result.get("created"):
                alerts_created += 1

            updated += 1

            results.append(
                {
                    "story_id": story["id"],
                    "priority": classification["priority"],
                    "priority_score": classification["priority_score"],
                    "category": classification["category"],
                    "category_score": classification["category_score"],
                    "alert": alert_result,
                }
            )

        except Exception as exc:
            failed += 1

            print(
                "[AI RECLASSIFY SOURCE ERROR]",
                story["id"],
                str(exc),
            )

            results.append(
                {
                    "story_id": story["id"],
                    "error": str(exc),
                }
            )

    return {
        "source": source,
        "found": len(stories),
        "updated": updated,
        "failed": failed,
        "alerts_created": alerts_created,
        "results": results,
    }


# =========================================================
# EMBEDDINGS BACKFILL
# =========================================================

@app.post(
    "/embeddings/backfill"
)
def embeddings_backfill():
    with engine.connect() as connection:
        stories = connection.execute(
            text("""
                SELECT
                    s.id,
                    s.title,
                    s.summary

                FROM stories s

                LEFT JOIN story_embeddings e
                    ON e.story_id = s.id

                WHERE
                    e.story_id IS NULL

                ORDER BY
                    s.id
            """)
        ).mappings().all()

    inserted = 0
    failed = 0
    errors = []

    for story in stories:
        try:
            create_story_embedding(
                story_id=story["id"],
                title=story["title"],
                summary=story["summary"],
            )

            inserted += 1

        except Exception as exc:
            failed += 1

            errors.append(
                {
                    "story_id": (
                        story["id"]
                    ),
                    "error": str(exc),
                }
            )

    return {
        "found": len(stories),
        "inserted": inserted,
        "failed": failed,
        "errors": errors,
        "model": EMBEDDING_MODEL_NAME,
    }
    
@app.post(
    "/stories/{story_id}/what-changed"
)
async def analyze_what_changed(
    story_id: int,
):
    # -----------------------------------------
    # CURRENT STORY + THREAD
    # -----------------------------------------

    with engine.connect() as connection:
        current = connection.execute(
            text("""
                SELECT
                    s.id,
                    s.title,
                    s.summary,
                    s.published_at,
                    s.discovered_at,
                    i.thread_id     

                FROM stories s

                JOIN story_thread_items i
                    ON i.story_id = s.id

                WHERE s.id = :story_id
            """),
            {
                "story_id": story_id,
            },
        ).mappings().first()

    if not current:
        return {
            "success": False,
            "error": (
                "Story does not belong "
                "to a thread"
            ),
        }

    thread_id = current[
        "thread_id"
    ]

    # -----------------------------------------
    # PREVIOUS STORIES ONLY
    # -----------------------------------------

    with engine.connect() as connection:
        previous = connection.execute(
            text("""
                SELECT
                    s.id,
                    s.title,
                    s.summary,
                    s.published_at,
                    s.discovered_at

                FROM story_thread_items i

                JOIN stories s
                    ON s.id = i.story_id

                WHERE
                    i.thread_id = :thread_id

                    AND s.id != :story_id

                    AND (
                        s.published_at < :current_published_at

                        OR (
                            s.published_at = :current_published_at
                            AND s.id < :story_id
                        )
                    )

                ORDER BY
                    s.published_at ASC,
                    s.id ASC
            """),
            {
                "thread_id": thread_id,
                "story_id": story_id,
                "current_published_at": (
                    current["published_at"]
                ),
            },
        ).mappings().all()

    if not previous:
        return {
            "story_id": story_id,
            "thread_id": thread_id,
            "has_history": False,
            "message": (
                "Esta é a primeira story "
                "do thread."
            ),
        }

    # -----------------------------------------
    # JEV
    # -----------------------------------------

    jev_result = (
        await analyze_story_changes(
            current_story=dict(current),
            previous_stories=[
                dict(row)
                for row in previous
            ],
        )
    )

    analysis = (
        interpret_story_changes(
            jev_result
        )
    )

    # -----------------------------------------
    # SAVE
    # -----------------------------------------

    ai_metadata = {
        "provider": "TypeSafe",
        "model": jev_result.get(
            "model"
        ),
        "usage": jev_result.get(
            "usage"
        ),
        "answers": jev_result.get(
            "answers"
        ),
    }

    with engine.begin() as connection:
        connection.execute(
            text("""
                INSERT INTO story_changes (
                    story_id,
                    thread_id,
                    has_meaningful_change,
                    new_information,
                    new_actor,
                    new_measure,
                    status_change,
                    date_change,
                    quantitative_change,
                    contradiction,
                    ai_metadata
                )
                VALUES (
                    :story_id,
                    :thread_id,
                    :meaningful_change,
                    :new_information,
                    :new_actor,
                    :new_measure,
                    :status_change,
                    :date_change,
                    :quantitative_change,
                    :contradiction,
                    CAST(
                        :ai_metadata
                        AS JSONB
                    )
                )

                ON CONFLICT (story_id)
                DO UPDATE SET
                    thread_id =
                        EXCLUDED.thread_id,

                    has_meaningful_change =
                        EXCLUDED.has_meaningful_change,

                    new_information =
                        EXCLUDED.new_information,

                    new_actor =
                        EXCLUDED.new_actor,

                    new_measure =
                        EXCLUDED.new_measure,

                    status_change =
                        EXCLUDED.status_change,

                    date_change =
                        EXCLUDED.date_change,

                    quantitative_change =
                        EXCLUDED.quantitative_change,

                    contradiction =
                        EXCLUDED.contradiction,

                    ai_metadata =
                        EXCLUDED.ai_metadata,

                    created_at = NOW()
            """),
            {
                "story_id": story_id,
                "thread_id": thread_id,

                "meaningful_change": (
                    analysis[
                        "meaningful_change"
                    ]
                ),

                "new_information": (
                    analysis[
                        "new_information"
                    ]
                ),

                "new_actor": (
                    analysis[
                        "new_actor"
                    ]
                ),

                "new_measure": (
                    analysis[
                        "new_measure"
                    ]
                ),

                "status_change": (
                    analysis[
                        "status_change"
                    ]
                ),

                "date_change": (
                    analysis[
                        "date_change"
                    ]
                ),

                "quantitative_change": (
                    analysis[
                        "quantitative_change"
                    ]
                ),

                "contradiction": (
                    analysis[
                        "contradiction"
                    ]
                ),

                "ai_metadata": json.dumps(
                    ai_metadata,
                    ensure_ascii=False,
                ),
            },
        )

    return {
        "story_id": story_id,
        "thread_id": thread_id,
        "compared_with": len(
            previous
        ),
        "changes": analysis,
        "jev": {
            "model": jev_result.get(
                "model"
            ),
            "usage": jev_result.get(
                "usage"
            ),
        },
    }

@app.post("/threads/auto-backfill")
async def auto_thread_backfill():
    with engine.connect() as connection:
        stories = connection.execute(
            text("""
                SELECT
                    s.id,
                    s.title,
                    s.published_at,
                    s.discovered_at

                FROM stories s

                LEFT JOIN story_thread_items i
                    ON i.story_id = s.id

                WHERE i.story_id IS NULL

                ORDER BY
                    COALESCE(
                        s.published_at,
                        s.discovered_at
                    ) ASC,
                    s.id ASC
            """)
        ).mappings().all()

    processed = 0
    linked = 0
    not_linked = 0
    failed = 0

    results = []

    for story in stories:
        story_id = story["id"]

        try:
            result = (
                await auto_assign_story_to_thread(
                    story_id
                )
            )

            processed += 1

            if result.get("linked"):
                linked += 1
            else:
                not_linked += 1

            results.append(
                {
                    "story_id": story_id,
                    "title": story["title"],
                    "result": result,
                }
            )

        except Exception as exc:
            failed += 1

            results.append(
                {
                    "story_id": story_id,
                    "title": story["title"],
                    "error": str(exc),
                }
            )

    return {
        "found": len(stories),
        "processed": processed,
        "linked": linked,
        "not_linked": not_linked,
        "failed": failed,
        "results": results,
    }

@app.get("/analytics/similarity")
def similarity_analytics():
    with engine.connect() as connection:

        # -------------------------------------------------
        # ALL PAIRS
        # -------------------------------------------------

        stats = connection.execute(
            text("""
                WITH pairs AS (
                    SELECT
                        a.story_id AS story_a,
                        b.story_id AS story_b,

                        1 - (
                            a.embedding <=>
                            b.embedding
                        ) AS similarity

                    FROM story_embeddings a

                    JOIN story_embeddings b
                        ON a.story_id < b.story_id
                )

                SELECT
                    COUNT(*) AS pair_count,

                    MIN(similarity) AS min_similarity,

                    percentile_cont(0.10)
                        WITHIN GROUP (
                            ORDER BY similarity
                        ) AS p10,

                    percentile_cont(0.25)
                        WITHIN GROUP (
                            ORDER BY similarity
                        ) AS p25,

                    percentile_cont(0.50)
                        WITHIN GROUP (
                            ORDER BY similarity
                        ) AS median,

                    percentile_cont(0.75)
                        WITHIN GROUP (
                            ORDER BY similarity
                        ) AS p75,

                    percentile_cont(0.90)
                        WITHIN GROUP (
                            ORDER BY similarity
                        ) AS p90,

                    percentile_cont(0.95)
                        WITHIN GROUP (
                            ORDER BY similarity
                        ) AS p95,

                    MAX(similarity) AS max_similarity,

                    AVG(similarity) AS avg_similarity

                FROM pairs
            """)
        ).mappings().first()

        # -------------------------------------------------
        # TOP 20 MOST SIMILAR PAIRS
        # -------------------------------------------------

        top_pairs = connection.execute(
            text("""
                SELECT
                    a.story_id AS story_a_id,
                    sa.title AS story_a_title,

                    b.story_id AS story_b_id,
                    sb.title AS story_b_title,

                    1 - (
                        a.embedding <=>
                        b.embedding
                    ) AS similarity

                FROM story_embeddings a

                JOIN story_embeddings b
                    ON a.story_id < b.story_id

                JOIN stories sa
                    ON sa.id = a.story_id

                JOIN stories sb
                    ON sb.id = b.story_id

                ORDER BY
                    a.embedding <=>
                    b.embedding

                LIMIT 20
            """)
        ).mappings().all()

        # -------------------------------------------------
        # NEAREST NEIGHBOR FOR EACH STORY
        # -------------------------------------------------

        nearest = connection.execute(
            text("""
                SELECT
                    a.story_id,

                    sa.title AS story_title,

                    nearest.story_id
                        AS nearest_story_id,

                    sb.title
                        AS nearest_story_title,

                    nearest.similarity

                FROM story_embeddings a

                JOIN stories sa
                    ON sa.id = a.story_id

                CROSS JOIN LATERAL (
                    SELECT
                        b.story_id,

                        1 - (
                            a.embedding <=>
                            b.embedding
                        ) AS similarity

                    FROM story_embeddings b

                    WHERE
                        b.story_id != a.story_id

                    ORDER BY
                        a.embedding <=>
                        b.embedding

                    LIMIT 1
                ) nearest

                JOIN stories sb
                    ON sb.id = nearest.story_id

                ORDER BY
                    nearest.similarity DESC
            """)
        ).mappings().all()

    def clean_number(value):
        if value is None:
            return None

        return round(
            float(value),
            4,
        )

    return {
        "distribution": {
            "pair_count": (
                stats["pair_count"]
            ),

            "min": clean_number(
                stats["min_similarity"]
            ),

            "p10": clean_number(
                stats["p10"]
            ),

            "p25": clean_number(
                stats["p25"]
            ),

            "median": clean_number(
                stats["median"]
            ),

            "p75": clean_number(
                stats["p75"]
            ),

            "p90": clean_number(
                stats["p90"]
            ),

            "p95": clean_number(
                stats["p95"]
            ),

            "max": clean_number(
                stats["max_similarity"]
            ),

            "average": clean_number(
                stats["avg_similarity"]
            ),
        },

        "top_pairs": [
            {
                **dict(row),
                "similarity": clean_number(
                    row["similarity"]
                ),
            }
            for row in top_pairs
        ],

        "nearest_neighbors": [
            {
                **dict(row),
                "similarity": clean_number(
                    row["similarity"]
                ),
            }
            for row in nearest
        ],
    }

@app.post("/changes/auto-backfill")
async def auto_backfill_changes():
    with engine.connect() as connection:
        rows = connection.execute(
            text("""
                SELECT
                    s.id,
                    s.title,
                    i.thread_id

                FROM story_thread_items i

                JOIN stories s
                    ON s.id = i.story_id

                LEFT JOIN story_changes c
                    ON c.story_id = s.id

                WHERE
                    (
                        c.story_id IS NULL
                        OR c.change_summary IS NULL
                    )

                    AND EXISTS (
                        SELECT 1

                        FROM story_thread_items previous_i

                        JOIN stories previous_s
                            ON previous_s.id =
                                previous_i.story_id

                        WHERE
                            previous_i.thread_id =
                                i.thread_id

                            AND (
                                COALESCE(
                                    previous_s.published_at,
                                    previous_s.discovered_at
                                )
                                <
                                COALESCE(
                                    s.published_at,
                                    s.discovered_at
                                )

                                OR (
                                    COALESCE(
                                        previous_s.published_at,
                                        previous_s.discovered_at
                                    )
                                    =
                                    COALESCE(
                                        s.published_at,
                                        s.discovered_at
                                    )

                                    AND previous_s.id < s.id
                                )
                            )
                    )

                ORDER BY
                    i.thread_id,
                    COALESCE(
                        s.published_at,
                        s.discovered_at
                    ) ASC,
                    s.id ASC
            """)
        ).mappings().all()

    results = []

    generated = 0
    no_history = 0
    failed = 0

    for row in rows:
        story_id = row["id"]

        try:
            result = await run_what_changed(
                story_id
            )

            if result.get(
                "has_history"
            ):
                generated += 1
            else:
                no_history += 1

            results.append(
                {
                    "story_id": story_id,
                    "title": row["title"],
                    "thread_id": row["thread_id"],
                    "result": result,
                }
            )

        except Exception as exc:
            failed += 1

            print(
                f"[CHANGES BACKFILL ERROR] "
                f"story={story_id}: "
                f"{exc}"
            )

            results.append(
                {
                    "story_id": story_id,
                    "title": row["title"],
                    "thread_id": row["thread_id"],
                    "error": str(exc),
                }
            )

    return {
        "found": len(rows),
        "processed": len(results),
        "generated": generated,
        "no_history": no_history,
        "failed": failed,
        "results": results,
    }

@app.post(
    "/threads/{thread_id}/refresh-identity"
)
def refresh_thread_identity_endpoint(
    thread_id: int,
):
    try:
        return refresh_thread_identity(
            thread_id
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    except Exception as exc:
        print(
            f"[THREAD IDENTITY ERROR] "
            f"thread={thread_id}: {exc}"
        )

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )    

@app.post("/stories/{story_id}/auto-process")
async def auto_process_story(
    story_id: int,
):
    """
    Reprocesses a story through the automatic newsroom pipeline:

    1. Ensures embedding exists
    2. Attempts automatic thread assignment
    3. Runs What Changed if the story is linked to a thread

    Useful for testing, debugging and manual reprocessing.
    """

    result = {
        "story_id": story_id,
        "embedding": None,
        "threading": None,
        "what_changed": None,
        "errors": [],
    }

    # -----------------------------------------------------
    # LOAD STORY
    # -----------------------------------------------------

    with engine.connect() as connection:
        story = connection.execute(
            text("""
                SELECT
                    id,
                    title,
                    summary,
                    category,
                    published_at,
                    discovered_at

                FROM stories

                WHERE id = :story_id
            """),
            {
                "story_id": story_id,
            },
        ).mappings().first()

    if not story:
        raise HTTPException(
            status_code=404,
            detail="Story not found",
        )

    # -----------------------------------------------------
    # EMBEDDING
    # -----------------------------------------------------

    try:
        with engine.connect() as connection:
            existing_embedding = (
                connection.execute(
                    text("""
                        SELECT
                            story_id,
                            model

                        FROM story_embeddings

                        WHERE story_id = :story_id
                    """),
                    {
                        "story_id": story_id,
                    },
                )
                .mappings()
                .first()
            )

        if existing_embedding:
            result["embedding"] = {
                "status": "already_exists",
                "model": existing_embedding[
                    "model"
                ],
            }

        else:
            vector = embed_story(
                story["title"],
                story["summary"],
            )

            with engine.begin() as connection:
                connection.execute(
                    text("""
                        INSERT INTO story_embeddings (
                            story_id,
                            embedding,
                            model,
                            created_at
                        )
                        VALUES (
                            :story_id,
                            :embedding,
                            :model,
                            NOW()
                        )

                        ON CONFLICT (story_id)
                        DO UPDATE SET
                            embedding =
                                EXCLUDED.embedding,
                            model =
                                EXCLUDED.model,
                            created_at =
                                NOW()
                    """),
                    {
                        "story_id": story_id,
                        "embedding": vector,
                        "model": EMBEDDING_MODEL_NAME,
                    },
                )

            result["embedding"] = {
                "status": "created",
                "model": EMBEDDING_MODEL_NAME,
            }

    except Exception as exc:
        print(
            f"[AUTO PROCESS EMBEDDING ERROR] "
            f"story={story_id}: "
            f"{exc}"
        )

        result["errors"].append(
            {
                "step": "embedding",
                "error": str(exc),
            }
        )

    # -----------------------------------------------------
    # THREADING
    # -----------------------------------------------------

    try:
        thread_result = (
            await auto_assign_story_to_thread(
                story_id
            )
        )

        result["threading"] = (
            thread_result
        )

    except Exception as exc:
        print(
            f"[AUTO PROCESS THREADING ERROR] "
            f"story={story_id}: "
            f"{exc}"
        )

        result["errors"].append(
            {
                "step": "threading",
                "error": str(exc),
            }
        )

        return result

    # -----------------------------------------------------
    # WHAT CHANGED
    # -----------------------------------------------------

    try:
        if (
            thread_result
            and thread_result.get(
                "linked"
            )
        ):
            changes_result = (
                await run_what_changed(
                    story_id
                )
            )

            result["what_changed"] = (
                changes_result
            )

        else:
            result["what_changed"] = {
                "status": "skipped",
                "reason": (
                    "story_not_linked_to_thread"
                ),
            }

    except Exception as exc:
        print(
            f"[AUTO PROCESS WHAT CHANGED ERROR] "
            f"story={story_id}: "
            f"{exc}"
        )

        result["errors"].append(
            {
                "step": "what_changed",
                "error": str(exc),
            }
        )

    # -----------------------------------------------------
    # FINAL STATUS
    # -----------------------------------------------------

    result["success"] = (
        len(result["errors"]) == 0
    )

    return result

@app.get(
    "/stories/{story_id}/thread-audit"
)
def get_story_thread_audit(
    story_id: int,
):
    with engine.connect() as connection:
        rows = connection.execute(
            text("""
                SELECT
                    a.id,
                    a.evaluation_id,
                    a.story_id,

                    s.title
                        AS story_title,

                    a.candidate_story_id,

                    candidate.title
                        AS candidate_title,

                    a.candidate_rank,

                    a.vector_similarity,
                    a.same_thread_score,
                    a.direct_continuation_score,
                    a.shared_specific_reference_score,

                    a.gate_passed,
                    a.selected,
                    a.decision,

                    a.resulting_thread_id,

                    t.title
                        AS resulting_thread_title,

                    a.jev_model,
                    a.jev_usage,
                    a.created_at

                FROM thread_match_audits a

                JOIN stories s
                    ON s.id = a.story_id

                JOIN stories candidate
                    ON candidate.id =
                        a.candidate_story_id

                LEFT JOIN story_threads t
                    ON t.id =
                        a.resulting_thread_id

                WHERE
                    a.story_id = :story_id

                ORDER BY
                    a.created_at DESC,
                    a.evaluation_id,
                    a.candidate_rank ASC
            """),
            {
                "story_id": story_id,
            },
        ).mappings().all()

    return {
        "story_id": story_id,
        "count": len(rows),
        "results": [
            dict(row)
            for row in rows
        ],
    }

@app.post(
    "/stories/{story_id}/evaluate-alert"
)
def evaluate_story_alert(
    story_id: int,
):
    with engine.connect() as connection:
        change = connection.execute(
            text("""
                SELECT
                    has_meaningful_change,
                    new_information,
                    new_actor,
                    new_measure,
                    status_change,
                    date_change,
                    quantitative_change,
                    contradiction,
                    change_summary

                FROM story_changes

                WHERE story_id = :story_id
            """),
            {
                "story_id": story_id,
            },
        ).mappings().first()

    change_result = None

    if change:
        change_result = {
            "changes": {
                "meaningful_change": (
                    change[
                        "has_meaningful_change"
                    ]
                ),

                "new_information": (
                    change[
                        "new_information"
                    ]
                ),

                "new_actor": (
                    change[
                        "new_actor"
                    ]
                ),

                "new_measure": (
                    change[
                        "new_measure"
                    ]
                ),

                "status_change": (
                    change[
                        "status_change"
                    ]
                ),

                "date_change": (
                    change[
                        "date_change"
                    ]
                ),

                "quantitative_change": (
                    change[
                        "quantitative_change"
                    ]
                ),

                "contradiction": (
                    change[
                        "contradiction"
                    ]
                ),
            },

            "change_summary": (
                change[
                    "change_summary"
                ]
            ),
        }

    return create_story_alert(
        story_id=story_id,
        change_result=change_result,
    )



@app.patch(
    "/alerts/{alert_id}/status"
)
def update_alert_status(
    alert_id: int,
    payload: AlertStatusUpdate,
):
    allowed_statuses = {
        "pending",
        "acknowledged",
        "dismissed",
        "delivered",
    }

    if payload.status not in allowed_statuses:
        return {
            "success": False,
            "error": "Invalid alert status",
            "allowed_statuses": sorted(
                allowed_statuses
            ),
        }

    with engine.begin() as connection:

        # -------------------------------------------------
        # CURRENT STATE
        # -------------------------------------------------

        current = connection.execute(
            text("""
                SELECT
                    id,
                    status

                FROM newsroom_alerts

                WHERE id = :alert_id

                FOR UPDATE
            """),
            {
                "alert_id": alert_id,
            },
        ).mappings().first()

        if not current:
            return {
                "success": False,
                "error": "Alert not found",
            }

        old_status = current["status"]
        new_status = payload.status

        # -------------------------------------------------
        # IDEMPOTENCY
        # -------------------------------------------------

        if old_status == new_status:
            return {
                "success": True,
                "changed": False,
                "alert_id": alert_id,
                "status": old_status,
                "reason": "status_already_set",
            }

        # -------------------------------------------------
        # UPDATE ALERT
        # -------------------------------------------------

        updated = connection.execute(
            text("""
                UPDATE newsroom_alerts

                SET
                    status = :new_status,

                    acknowledged_at = CASE
                        WHEN :set_acknowledged
                        THEN NOW()
                        ELSE acknowledged_at
                    END,

                    dismissed_at = CASE
                        WHEN :set_dismissed
                        THEN NOW()
                        ELSE dismissed_at
                    END,

                    delivered_at = CASE
                        WHEN :set_delivered
                        THEN NOW()
                        ELSE delivered_at
                    END,

                    updated_at = NOW()

                WHERE id = :alert_id

                RETURNING
                    id,
                    story_id,
                    thread_id,
                    alert_type,
                    status,
                    acknowledged_at,
                    dismissed_at,
                    delivered_at,
                    updated_at
            """),
            {
                "alert_id": alert_id,
                "new_status": new_status,

                "set_acknowledged": (
                    new_status
                    == "acknowledged"
                ),

                "set_dismissed": (
                    new_status
                    == "dismissed"
                ),

                "set_delivered": (
                    new_status
                    == "delivered"
                ),
            },
        ).mappings().first()

        # -------------------------------------------------
        # SAVE HISTORY
        # -------------------------------------------------

        connection.execute(
            text("""
                INSERT INTO alert_status_history (
                    alert_id,
                    from_status,
                    to_status,
                    source
                )
                VALUES (
                    :alert_id,
                    :from_status,
                    :to_status,
                    'manual'
                )
            """),
            {
                "alert_id": alert_id,
                "from_status": old_status,
                "to_status": new_status,
            },
        )

    return {
        "success": True,
        "changed": True,
        "from_status": old_status,
        **dict(updated),
    }

@app.get("/alerts")
def get_alerts(
    status: str | None = None,
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
    ),
):
    with engine.connect() as connection:

        if status:
            rows = connection.execute(
                text("""
                    SELECT
                        a.id,
                        a.story_id,
                        s.title AS story_title,

                        a.thread_id,
                        t.title AS thread_title,

                        a.alert_type,
                        a.title,
                        a.message,

                        a.priority_score,
                        a.meaningful_change_score,

                        a.status,
                        a.metadata,

                        a.created_at,
                        a.delivered_at

                    FROM newsroom_alerts a

                    JOIN stories s
                        ON s.id = a.story_id

                    LEFT JOIN story_threads t
                        ON t.id = a.thread_id

                    WHERE a.status = :status

                    ORDER BY
                        a.created_at DESC

                    LIMIT :limit
                """),
                {
                    "status": status,
                    "limit": limit,
                },
            ).mappings().all()

        else:
            rows = connection.execute(
                text("""
                    SELECT
                        a.id,
                        a.story_id,
                        s.title AS story_title,

                        a.thread_id,
                        t.title AS thread_title,

                        a.alert_type,
                        a.title,
                        a.message,

                        a.priority_score,
                        a.meaningful_change_score,

                        a.status,
                        a.metadata,

                        a.created_at,
                        a.delivered_at

                    FROM newsroom_alerts a

                    JOIN stories s
                        ON s.id = a.story_id

                    LEFT JOIN story_threads t
                        ON t.id = a.thread_id

                    ORDER BY
                        a.created_at DESC

                    LIMIT :limit
                """),
                {
                    "limit": limit,
                },
            ).mappings().all()

    return {
        "count": len(rows),
        "status": status,
        "results": [
            dict(row)
            for row in rows
        ],
    }

@app.get("/alerts/stats")
def get_alert_stats():
    with engine.connect() as connection:
        rows = connection.execute(
            text("""
                SELECT
                    status,
                    COUNT(*) AS count

                FROM newsroom_alerts

                GROUP BY status
            """)
        ).mappings().all()

    stats = {
        "pending": 0,
        "acknowledged": 0,
        "dismissed": 0,
        "delivered": 0,
    }

    for row in rows:
        stats[row["status"]] = (
            row["count"]
        )

    stats["total"] = sum(
        stats.values()
    )

    return stats

@app.get(
    "/alerts/{alert_id}/history"
)
def get_alert_history(
    alert_id: int,
):
    with engine.connect() as connection:

        alert = connection.execute(
            text("""
                SELECT
                    id,
                    story_id,
                    thread_id,
                    alert_type,
                    status,
                    created_at,
                    acknowledged_at,
                    dismissed_at,
                    delivered_at,
                    updated_at

                FROM newsroom_alerts

                WHERE id = :alert_id
            """),
            {
                "alert_id": alert_id,
            },
        ).mappings().first()

        if not alert:
            raise HTTPException(
                status_code=404,
                detail="Alert not found",
            )

        history = connection.execute(
            text("""
                SELECT
                    id,
                    from_status,
                    to_status,
                    source,
                    changed_at

                FROM alert_status_history

                WHERE alert_id = :alert_id

                ORDER BY
                    changed_at ASC,
                    id ASC
            """),
            {
                "alert_id": alert_id,
            },
        ).mappings().all()

    return {
        "alert": dict(alert),

        "history": [
            dict(row)
            for row in history
        ],
    }

@app.post(
    "/alerts/{alert_id}/deliveries"
)
def create_delivery(
    alert_id: int,
    payload: AlertDeliveryCreate,
):
    return create_alert_delivery(
        alert_id=alert_id,
        channel=payload.channel,
        destination=payload.destination,
    )

@app.get(
    "/alerts/{alert_id}/deliveries"
)
def get_alert_deliveries(
    alert_id: int,
):
    with engine.connect() as connection:

        rows = connection.execute(
            text("""
                SELECT
                    id,
                    alert_id,
                    channel,
                    destination,
                    status,
                    attempt_count,
                    external_id,
                    last_error,
                    created_at,
                    updated_at,
                    sent_at

                FROM alert_deliveries

                WHERE alert_id = :alert_id

                ORDER BY
                    created_at DESC,
                    id DESC
            """),
            {
                "alert_id": alert_id,
            },
        ).mappings().all()

    return {
        "alert_id": alert_id,
        "count": len(rows),
        "results": [
            dict(row)
            for row in rows
        ],
    }

@app.post(
    "/deliveries/{delivery_id}/process"
)
def process_delivery_endpoint(
    delivery_id: int,
):
    return process_delivery(
        delivery_id
    )

@app.post(
    "/deliveries/process-pending"
)
def process_pending_deliveries_endpoint(
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
):
    return process_pending_deliveries(
        limit=limit
    )

@app.get("/notification-channels")
def get_notification_channels():
    with engine.connect() as connection:
        rows = connection.execute(
            text("""
                SELECT
                    id,
                    name,
                    channel,
                    destination,
                    enabled,
                    min_priority_score,
                    min_meaningful_change_score,
                    created_at,
                    updated_at

                FROM notification_channels

                ORDER BY id ASC
            """)
        ).mappings().all()

    return {
        "count": len(rows),
        "results": [
            dict(row)
            for row in rows
        ],
    }

@app.post("/notification-channels")
def create_notification_channel(
    payload: NotificationChannelCreate,
):
    allowed_channels = {
        "telegram",
        "email",
        "webhook",
    }

    if payload.channel not in allowed_channels:
        return {
            "created": False,
            "reason": "invalid_channel",
            "allowed_channels": sorted(
                allowed_channels
            ),
        }

    with engine.begin() as connection:
        channel = connection.execute(
            text("""
                INSERT INTO notification_channels (
                    name,
                    channel,
                    destination,
                    enabled,
                    min_priority_score,
                    min_meaningful_change_score
                )
                VALUES (
                    :name,
                    :channel,
                    :destination,
                    :enabled,
                    :min_priority_score,
                    :min_meaningful_change_score
                )

                RETURNING
                    id,
                    name,
                    channel,
                    destination,
                    enabled,
                    min_priority_score,
                    min_meaningful_change_score,
                    created_at
            """),
            {
                "name": payload.name,
                "channel": payload.channel,
                "destination": (
                    payload.destination
                ),
                "enabled": payload.enabled,
                "min_priority_score": (
                    payload.min_priority_score
                ),
                "min_meaningful_change_score": (
                    payload.min_meaningful_change_score
                ),
            },
        ).mappings().first()

    return {
        "created": True,
        "channel": dict(
            channel
        ),
    }

@app.post(
    "/alerts/{alert_id}/setup-deliveries"
)
def setup_alert_deliveries(
    alert_id: int,
):
    return create_deliveries_for_alert(
        alert_id
    )

@app.patch(
    "/notification-channels/{channel_id}"
)
def update_notification_channel(
    channel_id: int,
    payload: NotificationChannelUpdate,
):
    with engine.begin() as connection:

        current = connection.execute(
            text("""
                SELECT
                    id,
                    name,
                    channel,
                    destination,
                    enabled,
                    min_priority_score,
                    min_meaningful_change_score

                FROM notification_channels

                WHERE id = :channel_id
            """),
            {
                "channel_id": channel_id,
            },
        ).mappings().first()

        if not current:
            raise HTTPException(
                status_code=404,
                detail="Notification channel not found",
            )

        fields_set = (
            payload.model_fields_set
        )

        # -------------------------------------------------
        # NAME
        # -------------------------------------------------

        if "name" in fields_set:
            name = payload.name
        else:
            name = current["name"]

        # -------------------------------------------------
        # DESTINATION
        # -------------------------------------------------

        if "destination" in fields_set:
            destination = (
                payload.destination
            )
        else:
            destination = (
                current["destination"]
            )

        # -------------------------------------------------
        # ENABLED
        # -------------------------------------------------

        if "enabled" in fields_set:
            enabled = (
                payload.enabled
            )
        else:
            enabled = (
                current["enabled"]
            )

        # -------------------------------------------------
        # MIN PRIORITY
        #
        # Important:
        # explicit null means remove threshold.
        # -------------------------------------------------

        if (
            "min_priority_score"
            in fields_set
        ):
            min_priority_score = (
                payload.min_priority_score
            )
        else:
            min_priority_score = (
                current[
                    "min_priority_score"
                ]
            )

        # -------------------------------------------------
        # MIN MEANINGFUL CHANGE
        # -------------------------------------------------

        if (
            "min_meaningful_change_score"
            in fields_set
        ):
            min_meaningful_change_score = (
                payload.min_meaningful_change_score
            )
        else:
            min_meaningful_change_score = (
                current[
                    "min_meaningful_change_score"
                ]
            )

        # -------------------------------------------------
        # BASIC VALIDATION
        # -------------------------------------------------

        if (
            name is None
            or not name.strip()
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Channel name cannot be empty"
                ),
            )

        if (
            destination is None
            or not destination.strip()
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Destination cannot be empty"
                ),
            )

        if (
            min_priority_score
            is not None
            and (
                min_priority_score < 0
                or min_priority_score > 1
            )
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "min_priority_score "
                    "must be between 0 and 1"
                ),
            )

        if (
            min_meaningful_change_score
            is not None
            and (
                min_meaningful_change_score < 0
                or min_meaningful_change_score > 1
            )
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "min_meaningful_change_score "
                    "must be between 0 and 1"
                ),
            )

        # -------------------------------------------------
        # UPDATE
        # -------------------------------------------------

        updated = connection.execute(
            text("""
                UPDATE notification_channels

                SET
                    name = :name,
                    destination = :destination,
                    enabled = :enabled,
                    min_priority_score =
                        :min_priority_score,
                    min_meaningful_change_score =
                        :min_meaningful_change_score,
                    updated_at = NOW()

                WHERE id = :channel_id

                RETURNING
                    id,
                    name,
                    channel,
                    destination,
                    enabled,
                    min_priority_score,
                    min_meaningful_change_score,
                    created_at,
                    updated_at
            """),
            {
                "channel_id": (
                    channel_id
                ),

                "name": (
                    name.strip()
                ),

                "destination": (
                    destination.strip()
                ),

                "enabled": enabled,

                "min_priority_score": (
                    min_priority_score
                ),

                "min_meaningful_change_score": (
                    min_meaningful_change_score
                ),
            },
        ).mappings().first()

    return {
        "success": True,
        "channel": dict(
            updated
        ),
    }

@app.patch(
    "/notification-channels/{channel_id}/toggle"
)
def toggle_notification_channel(
    channel_id: int,
):
    with engine.begin() as connection:

        updated = connection.execute(
            text("""
                UPDATE notification_channels

                SET
                    enabled = NOT enabled,
                    updated_at = NOW()

                WHERE id = :channel_id

                RETURNING
                    id,
                    name,
                    channel,
                    destination,
                    enabled,
                    min_priority_score,
                    min_meaningful_change_score,
                    updated_at
            """),
            {
                "channel_id": channel_id,
            },
        ).mappings().first()

    if not updated:
        raise HTTPException(
            status_code=404,
            detail="Notification channel not found",
        )

    return {
        "success": True,
        "channel": dict(updated),
    }

@app.delete(
    "/notification-channels/{channel_id}"
)
def delete_notification_channel(
    channel_id: int,
):
    with engine.begin() as connection:

        deleted = connection.execute(
            text("""
                DELETE FROM notification_channels

                WHERE id = :channel_id

                RETURNING
                    id,
                    name,
                    channel,
                    destination
            """),
            {
                "channel_id": channel_id,
            },
        ).mappings().first()

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Notification channel not found",
        )

    return {
        "success": True,
        "deleted": dict(deleted),
    }

@app.get("/deliveries/stats")
def get_delivery_stats():
    with engine.connect() as connection:
        rows = connection.execute(
            text("""
                SELECT
                    status,
                    COUNT(*) AS count

                FROM alert_deliveries

                GROUP BY status
            """)
        ).mappings().all()

    stats = {
        "pending": 0,
        "sending": 0,
        "sent": 0,
        "failed": 0,
    }

    for row in rows:
        stats[row["status"]] = row["count"]

    with engine.connect() as connection:
        retrying = connection.execute(
            text("""
                SELECT COUNT(*)

                FROM alert_deliveries

                WHERE
                    status = 'failed'
                    AND attempt_count < max_attempts
                    AND next_attempt_at IS NOT NULL
            """)
        ).scalar_one()

        permanently_failed = connection.execute(
            text("""
                SELECT COUNT(*)

                FROM alert_deliveries

                WHERE
                    status = 'failed'
                    AND (
                        attempt_count >= max_attempts
                        OR next_attempt_at IS NULL
                    )
            """)
        ).scalar_one()

    return {
        **stats,
        "retrying": retrying,
        "permanently_failed": permanently_failed,
        "total": sum(
            stats.values()
        ),
    }

@app.get("/deliveries")
def get_deliveries(
    status: str | None = None,
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
    ),
):
    with engine.connect() as connection:

        if status:
            rows = connection.execute(
                text("""
                    SELECT
                        d.id,
                        d.alert_id,
                        d.channel,
                        d.destination,
                        d.status,
                        d.attempt_count,
                        d.max_attempts,
                        d.next_attempt_at,
                        d.last_attempt_at,
                        d.external_id,
                        d.last_error,
                        d.created_at,
                        d.updated_at,
                        d.sent_at,

                        a.title AS alert_title,
                        a.alert_type

                    FROM alert_deliveries d

                    JOIN newsroom_alerts a
                        ON a.id = d.alert_id

                    WHERE d.status = :status

                    ORDER BY
                        d.created_at DESC

                    LIMIT :limit
                """),
                {
                    "status": status,
                    "limit": limit,
                },
            ).mappings().all()

        else:
            rows = connection.execute(
                text("""
                    SELECT
                        d.id,
                        d.alert_id,
                        d.channel,
                        d.destination,
                        d.status,
                        d.attempt_count,
                        d.max_attempts,
                        d.next_attempt_at,
                        d.last_attempt_at,
                        d.external_id,
                        d.last_error,
                        d.created_at,
                        d.updated_at,
                        d.sent_at,

                        a.title AS alert_title,
                        a.alert_type

                    FROM alert_deliveries d

                    JOIN newsroom_alerts a
                        ON a.id = d.alert_id

                    ORDER BY
                        d.created_at DESC

                    LIMIT :limit
                """),
                {
                    "limit": limit,
                },
            ).mappings().all()

    return {
        "count": len(rows),
        "status": status,
        "results": [
            dict(row)
            for row in rows
        ],
    }

@app.post(
    "/deliveries/{delivery_id}/retry"
)
def retry_delivery(
    delivery_id: int,
):
    with engine.begin() as connection:

        delivery = connection.execute(
            text("""
                SELECT
                    id,
                    status,
                    attempt_count,
                    max_attempts

                FROM alert_deliveries

                WHERE id = :delivery_id
            """),
            {
                "delivery_id": delivery_id,
            },
        ).mappings().first()

        if not delivery:
            raise HTTPException(
                status_code=404,
                detail="Delivery not found",
            )

        if delivery["status"] == "sent":
            return {
                "success": False,
                "reason": "delivery_already_sent",
            }

        updated = connection.execute(
            text("""
                UPDATE alert_deliveries

                SET
                    status = 'pending',
                    attempt_count = 0,
                    next_attempt_at = NOW(),
                    last_error = NULL,
                    updated_at = NOW()

                WHERE id = :delivery_id

                RETURNING
                    id,
                    alert_id,
                    channel,
                    destination,
                    status,
                    attempt_count,
                    max_attempts,
                    next_attempt_at
            """),
            {
                "delivery_id": delivery_id,
            },
        ).mappings().first()

    return {
        "success": True,
        "delivery": dict(
            updated
        ),
    }

@app.get("/health/operations")
def operations_health():
    return get_operations_health()

@app.get("/test/senado")
async def test_senado():
    stories = (
        await fetch_senado_stories(
            days=1,
            limit=10,
        )
    )

    return {
        "count": len(
            stories
        ),
        "results": stories,
    }

@app.post("/ingest/senado")
async def ingest_senado():
    return await run_senado_ingestion()

@app.post("/monitoring-profiles")
def create_monitoring_profile(
    payload: MonitoringProfileCreate,
):
    with engine.begin() as connection:

        row = connection.execute(
            text("""
                INSERT INTO monitoring_profiles (
                    name,
                    description,
                    min_relevance_score,
                    min_urgency_score,
                    alert_on_status_change,
                    alert_on_new_measure,
                    alert_on_date_change,
                    alert_on_contradiction
                )

                VALUES (
                    :name,
                    :description,
                    :min_relevance_score,
                    :min_urgency_score,
                    :alert_on_status_change,
                    :alert_on_new_measure,
                    :alert_on_date_change,
                    :alert_on_contradiction
                )

                RETURNING *
            """),
            payload.model_dump(),
        ).mappings().first()

    return dict(row)


@app.get("/monitoring-profiles")
def get_monitoring_profiles():

    with engine.connect() as connection:

        rows = connection.execute(
            text("""
                SELECT *
                FROM monitoring_profiles
                ORDER BY id ASC
            """)
        ).mappings().all()

    return [
        dict(row)
        for row in rows
    ]


@app.post(
    "/monitoring-profiles/{profile_id}/topics"
)
def add_monitoring_topic(
    profile_id: int,
    payload: MonitoringTopicCreate,
):
    clean_topic = " ".join(
        payload.topic.strip().split()
    )

    if not clean_topic:
        raise HTTPException(
            status_code=400,
            detail="Topic cannot be empty",
        )

    with engine.connect() as connection:
        profile = connection.execute(
            text("""
                SELECT id
                FROM monitoring_profiles
                WHERE id = :profile_id
                LIMIT 1
            """),
            {
                "profile_id": profile_id,
            },
        ).first()

    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Monitoring profile not found",
        )

    expansion = expand_topic_with_ai(
        clean_topic
    )

    with engine.begin() as connection:
        row = connection.execute(
            text("""
                INSERT INTO monitoring_topics (
                    profile_id,
                    topic,
                    semantic_description,
                    direct_terms,
                    domain_terms,
                    expanded_terms,
                    weight,
                    urgency_boost
                )
                VALUES (
                    :profile_id,
                    :topic,
                    :semantic_description,
                    CAST(:direct_terms AS JSONB),
                    CAST(:domain_terms AS JSONB),
                    CAST(:expanded_terms AS JSONB),
                    1.0,
                    0.0
                )
                RETURNING *
            """),
            {
                "profile_id": profile_id,
                "topic": clean_topic,
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
                    list(
                        dict.fromkeys(
                            expansion[
                                "direct_terms"
                            ]
                            + expansion[
                                "domain_terms"
                            ]
                        )
                    ),
                    ensure_ascii=False,
                ),
            },
        ).mappings().first()

    return {
        **dict(row),
        "expansion_generator": (
            expansion["generator"]
        ),
    }


@app.post(
    "/monitoring-topics/{topic_id}/expand"
)
def regenerate_monitoring_topic_expansion(
    topic_id: int,
):
    return expand_and_save_topic(
        engine=engine,
        topic_id=topic_id,
    )


@app.post(
    "/monitoring-profiles/{profile_id}/expand-topics"
)
def regenerate_monitoring_profile_topics(
    profile_id: int,
):
    return expand_profile_topics(
        engine=engine,
        profile_id=profile_id,
    )


@app.delete(
    "/monitoring-topics/{topic_id}"
)
def delete_monitoring_topic(
    topic_id: int,
):
    with engine.begin() as connection:

        deleted = connection.execute(
            text("""
                DELETE FROM monitoring_topics
                WHERE id = :topic_id
                RETURNING id
            """),
            {
                "topic_id": topic_id,
            },
        ).mappings().first()

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Monitoring topic not found",
        )

    return {
        "success": True,
        "topic_id": topic_id,
    }


@app.post(
    "/monitoring-profiles/{profile_id}/evaluate/{story_id}"
)
def evaluate_monitoring_profile(
    profile_id: int,
    story_id: int,
):
    return evaluate_story_for_profile(
        engine=engine,
        story_id=story_id,
        profile_id=profile_id,
    )


@app.post(
    "/monitoring/evaluate/{story_id}"
)
def evaluate_story_monitoring(
    story_id: int,
):
    return evaluate_story_for_all_profiles(
        engine=engine,
        story_id=story_id,
    )

@app.post(
    "/monitoring-profiles/{profile_id}/backfill"
)
def backfill_monitoring_profile_endpoint(
    profile_id: int,
    days: int = Query(
        default=30,
        ge=1,
        le=365,
    ),
    limit: int = Query(
        default=1000,
        ge=1,
        le=5000,
    ),
):
    return backfill_monitoring_profile(
        engine=engine,
        profile_id=profile_id,
        days=days,
        limit=limit,
    )


@app.get(
    "/monitoring-topics/{topic_id}/calibration"
)
def topic_calibration_report(
    topic_id: int,
    limit: int = 30,
):
    return get_topic_calibration_report(
        engine=engine,
        topic_id=topic_id,
        limit=limit,
    )

@app.get("/monitoring-alerts")
def monitoring_alerts(
    profile_id: int | None = None,
    status: str | None = None,
    limit: int = 50,
):
    return get_monitoring_alerts(
        engine=engine,
        profile_id=profile_id,
        status=status,
        limit=limit,
    )

@app.get(
    "/monitoring-profiles/{profile_id}/digest"
)
def monitoring_digest(
    profile_id: int,
    hours: int = 24,
    limit: int = 50,
):
    return get_monitoring_digest(
        engine=engine,
        profile_id=profile_id,
        hours=hours,
        limit=limit,
    )

@app.get(
    "/monitoring-profiles/{profile_id}/briefing"
)
def monitoring_briefing(
    profile_id: int,
    hours: int = 24,
    limit: int = 50,
):
    return get_monitoring_briefing(
        engine=engine,
        profile_id=profile_id,
        hours=hours,
        limit=limit,
    )

@app.get("/monitoring-profiles/{profile_id}")
def monitoring_profile_detail(
    profile_id: int,
):
    return get_monitoring_profile(
        engine=engine,
        profile_id=profile_id,
    )


@app.patch("/monitoring-profiles/{profile_id}")
def monitoring_profile_update(
    profile_id: int,
    payload: MonitoringProfileUpdate,
):
    return update_monitoring_profile(
        engine=engine,
        profile_id=profile_id,
        values=payload.model_dump(
            exclude_unset=True
        ),
    )


@app.delete("/monitoring-profiles/{profile_id}")
def monitoring_profile_delete(
    profile_id: int,
):
    return delete_monitoring_profile(
        engine=engine,
        profile_id=profile_id,
    )


@app.patch("/monitoring-topics/{topic_id}")
def monitoring_topic_update(
    topic_id: int,
    payload: MonitoringTopicUpdate,
):
    return update_monitoring_topic(
        engine=engine,
        topic_id=topic_id,
        values=payload.model_dump(
            exclude_unset=True
        ),
    )


@app.get(
    "/monitoring-profiles/{profile_id}/matches"
)
def monitoring_profile_matches(
    profile_id: int,
    limit: int = 50,
):
    return get_monitoring_profile_matches(
        engine=engine,
        profile_id=profile_id,
        limit=limit,
    )