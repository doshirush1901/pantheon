#!/usr/bin/env python3
"""
GROWTH SIGNAL — The Hormone That Accelerates Every System
==========================================================

Biological parallel:
    Growth hormone (somatotropin) doesn't teach a child to walk or talk.
    It accelerates the development of bones, muscles, brain connections,
    and immune function simultaneously. One signal, every system grows.

Ira parallel:
    When Ira digests an email, this module fires a single growth signal
    that fans out to every holistic body system:

    - Musculoskeletal: records the ingestion action (builds learning muscle)
    - Endocrine: rewards Clio for successful extraction (dopamine)
    - Sensory: records the email as a perception (cross-channel awareness)
    - Voice: tracks that email-derived knowledge exists (format adaptation)

    One call. Every system stimulated. Compounding growth.

Usage:
    from openclaw.agents.ira.src.holistic.growth_signal import signal_email_digested

    signal_email_digested(
        email_id="abc123",
        items_extracted=4,
        channel="email",
        contact_id="hans@packright.de",
    )
"""

import logging
from typing import Optional

logger = logging.getLogger("ira.growth_signal")


def signal_email_digested(
    email_id: str,
    items_extracted: int,
    channel: str = "email",
    contact_id: str = "",
    subject: str = "",
):
    """
    Fire a growth signal after an email is digested into knowledge.

    This is the growth hormone — one call that stimulates every body system.
    All calls are wrapped in try/except so a failure in one system never
    blocks the others.
    """
    context = {
        "email_id": email_id,
        "items_extracted": items_extracted,
        "source": "email_nutrient_extractor",
    }

    # 1. MUSCULOSKELETAL: Record the ingestion action
    try:
        from openclaw.agents.ira.src.holistic.musculoskeletal_system import get_musculoskeletal_system
        ms = get_musculoskeletal_system()
        rid = ms.record_action("knowledge_ingested", context={
            **context, "action_detail": f"email digested: {items_extracted} items",
        })
        if items_extracted > 0:
            ms.record_action_outcome(rid, "success")
        logger.debug(f"[GROWTH] Musculoskeletal: recorded email ingestion action")
    except Exception as e:
        logger.debug(f"[GROWTH] Musculoskeletal signal failed: {e}")

    # 2. ENDOCRINE: Reward Clio for successful extraction
    try:
        from openclaw.agents.ira.src.holistic.endocrine_system import get_endocrine_system
        endo = get_endocrine_system()
        if items_extracted > 0:
            endo.signal_success("clio", context=context, specialty="email_extraction")
        else:
            endo.signal_failure("clio", context=context, specialty="email_extraction")
        logger.debug(f"[GROWTH] Endocrine: {'rewarded' if items_extracted > 0 else 'penalized'} clio")
    except Exception as e:
        logger.debug(f"[GROWTH] Endocrine signal failed: {e}")

    # 3. SENSORY: Record the email as a perception
    try:
        from openclaw.agents.ira.src.holistic.sensory_system import get_sensory_integrator
        sensory = get_sensory_integrator()
        sensory.record_perception(
            channel="email",
            contact_id=contact_id or "unknown",
            content_summary=f"Email digested ({items_extracted} knowledge items): {subject[:80]}" if subject
                           else f"Email digested: {items_extracted} knowledge items",
            metadata=context,
        )
        logger.debug(f"[GROWTH] Sensory: recorded email perception for {contact_id}")
    except Exception as e:
        logger.debug(f"[GROWTH] Sensory signal failed: {e}")

    # 4. VOICE: Track email-derived knowledge volume
    try:
        from openclaw.agents.ira.src.holistic.voice_system import get_voice_system
        voice = get_voice_system()
        state = voice._state
        email_stats = state.setdefault("email_knowledge", {"total_items": 0, "total_emails": 0})
        email_stats["total_items"] = email_stats.get("total_items", 0) + items_extracted
        email_stats["total_emails"] = email_stats.get("total_emails", 0) + 1
        logger.debug(f"[GROWTH] Voice: tracked email knowledge volume")
    except Exception as e:
        logger.debug(f"[GROWTH] Voice signal failed: {e}")

    logger.info(
        f"[GROWTH] Email growth signal fired: {items_extracted} items, "
        f"contact={contact_id or 'unknown'}, email_id={email_id}"
    )


def signal_bulk_ingestion(
    source: str,
    items_total: int,
    emails_processed: int,
):
    """
    Fire a growth signal after a bulk ingestion completes (e.g. mailbox backfill).
    This is a mega-dose of growth hormone.
    """
    # Musculoskeletal: record the bulk action
    try:
        from openclaw.agents.ira.src.holistic.musculoskeletal_system import get_musculoskeletal_system
        ms = get_musculoskeletal_system()
        rid = ms.record_action("knowledge_ingested", context={
            "source": source,
            "items_total": items_total,
            "emails_processed": emails_processed,
            "action_detail": f"bulk ingestion: {items_total} items from {emails_processed} emails",
        })
        ms.record_action_outcome(rid, "success")
    except Exception:
        pass

    # Endocrine: big reward for Clio
    try:
        from openclaw.agents.ira.src.holistic.endocrine_system import get_endocrine_system
        endo = get_endocrine_system()
        for _ in range(min(items_total // 100, 5)):
            endo.signal_success("clio", specialty="email_extraction")
    except Exception:
        pass

    logger.info(
        f"[GROWTH] Bulk ingestion signal: {items_total} items from {emails_processed} emails ({source})"
    )
