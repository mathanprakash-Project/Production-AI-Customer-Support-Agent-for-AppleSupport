"""
Database initialization and default seeding script.
Creates tables and ensures seed accounts and initial sample threads exist.
"""

import logging
from sqlalchemy import select, text
from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import engine, async_session_factory
from app.models.user import User
from app.models.ticket import Ticket
from app.models.thread import Thread
from app.models.knowledge_base import KnowledgeEntry
from app.models.system_config import SystemConfig
from app.models.memory import ConversationSession, ConversationTurn, UserMemory, ContextMemory
from app.llm.embeddings import get_embedding_service

logger = logging.getLogger(__name__)


async def init_db(target_engine=None, target_factory=None):
    """Create all tables and seed default users and reference threads."""
    active_engine = target_engine or engine
    active_factory = target_factory or async_session_factory

    logger.info("Initializing database tables...")
    async with active_engine.begin() as conn:
        # Enable pgvector extension if on PostgreSQL
        if conn.dialect.name == "postgresql":
            try:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                logger.info("pgvector extension enabled.")
            except Exception as e:
                logger.warning(f"Could not enable pgvector extension: {e}")
        
        await conn.run_sync(Base.metadata.create_all)

        # Idempotent column migrations for existing PostgreSQL databases
        if conn.dialect.name == "postgresql":
            migration_statements = [
                # tickets
                "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS tweet_author VARCHAR(100);",
                "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS intent VARCHAR(50);",
                "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS confidence FLOAT DEFAULT 0.0;",
                "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS sentiment_score FLOAT DEFAULT 0.0;",
                "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS is_escalated BOOLEAN DEFAULT FALSE;",
                "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS escalation_reason VARCHAR(255);",
                "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS pii_detected BOOLEAN DEFAULT FALSE;",
                "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS pii_redacted_text TEXT;",
                "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS classification_time_ms INTEGER;",
                "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS retrieval_time_ms INTEGER;",
                "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS drafting_time_ms INTEGER;",
                "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS total_pipeline_time_ms INTEGER;",
                "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS processed_at TIMESTAMP WITH TIME ZONE;",
                "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMP WITH TIME ZONE;",
                # drafts
                "ALTER TABLE drafts ADD COLUMN IF NOT EXISTS safety_passed BOOLEAN DEFAULT TRUE;",
                "ALTER TABLE drafts ADD COLUMN IF NOT EXISTS safety_flags JSON DEFAULT '[]'::json;",
                "ALTER TABLE drafts ADD COLUMN IF NOT EXISTS response_type VARCHAR(20) DEFAULT 'tweet';",
                "ALTER TABLE drafts ADD COLUMN IF NOT EXISTS char_count INTEGER;",
                # feedback
                "ALTER TABLE feedback ADD COLUMN IF NOT EXISTS final_response_text TEXT;",
                "ALTER TABLE feedback ADD COLUMN IF NOT EXISTS edit_distance_ratio FLOAT;",
                "ALTER TABLE feedback ADD COLUMN IF NOT EXISTS review_time_seconds INTEGER;",
            ]
            for stmt in migration_statements:
                try:
                    await conn.execute(text(stmt))
                except Exception as ex:
                    logger.warning(f"Migration error ({stmt}): {ex}")

    async with active_factory() as session:
        # Check if users already seeded
        result = await session.execute(select(User).limit(1))
        if not result.scalars().first():
            logger.info("Seeding default admin and agent accounts...")
            admin = User(
                email="admin@tweetsupport.local",
                password_hash=get_password_hash("admin123"),
                full_name="Operations Admin",
                role="admin",
            )
            agent = User(
                email="agent@tweetsupport.local",
                password_hash=get_password_hash("agent123"),
                full_name="Tier-1 Support Agent",
                role="agent",
            )
            session.add_all([admin, agent])
            await session.commit()

        # Ensure Mathanprakash is established as the sole Manager account
        mgr_check = await session.execute(
            select(User).where(User.email == "mathanprakashselvam@gmail.com")
        )
        existing_mgr = mgr_check.scalars().first()
        if not existing_mgr:
            logger.info("Seeding sole executive manager account Mathanprakash (mathanprakashselvam@gmail.com)...")
            mgr = User(
                email="mathanprakashselvam@gmail.com",
                password_hash=get_password_hash("Tweetsupportadmin123"),
                full_name="Mathanprakash",
                role="manager",
            )
            session.add(mgr)
            await session.commit()
            logger.info("Executive manager Mathanprakash seeded successfully.")
        else:
            if existing_mgr.role != "manager" or existing_mgr.full_name != "Mathanprakash":
                existing_mgr.role = "manager"
                existing_mgr.full_name = "Mathanprakash"
                await session.commit()

        # Seed reference historical AppleSupport threads idempotently
        embedder = get_embedding_service()
        sample_threads = [
            (
                "seed-101",
                "My iPhone 13 won't charge with any cable. Port seems clean but completely dead.",
                "We'd love to help get your iPhone charging again. Try restarting your phone and testing with an Apple-certified Lightning cable and wall outlet. If it persists, inspect port carefully under light.",
                "charging_issues",
            ),
            (
                "seed-102",
                "Battery draining super fast after the latest iOS update! 100% to 20% in 2 hours.",
                "We can help with your battery. Immediately after an iOS update, background re-indexing can temporarily impact battery. Check Settings > Battery to see which apps are consuming power.",
                "battery_performance",
            ),
            (
                "seed-103",
                "I am locked out of my Apple ID and cannot remember security questions or password.",
                "We understand how important account access is. You can safely reset your password and begin account recovery at https://iforgot.apple.com from any trusted browser.",
                "apple_id_account",
            ),
            (
                "seed-104",
                "iOS 17 update keeps failing with 'An error occurred downloading iOS'. Plenty of storage.",
                "Let's get this resolved. Delete the downloaded update file from Settings > General > iPhone Storage, restart your device, and try downloading again over a strong Wi-Fi network.",
                "ios_update_bugs",
            ),
            (
                "seed-105",
                "Left AirPod has no sound at all. Right one works fine.",
                "We're here to help with your AirPods. Place both in the charging case, close the lid for 30 seconds, then hold the setup button on the back for 15 seconds to reset.",
                "audio_speaker_mic",
            ),
            (
                "seed-106",
                "Accidentally cracked my iPhone screen while running. Can I get a free replacement?",
                "Accidental physical damage is not covered under Apple's standard limited warranty. You can check repair options and AppleCare+ incident fees at support.apple.com/repair.",
                "hardware_damage",
            ),
            (
                "seed-107",
                "Unauthorized charge of $9.99 from Apple.com/bill on my credit card statement!",
                "We take billing inquiries seriously. You can view all active subscriptions and purchase history at reportaproblem.apple.com to identify or request a refund for the charge.",
                "purchase_refund_billing",
            ),
            (
                "seed-108",
                "my EarPods i lost i need to find give me a idea for it",
                "You can locate your lost EarPods or AirPods using the Find My app on your iPhone or at icloud.com/find. Select your EarPods under Devices to view their location or play a sound.",
                "lost_device_find_my",
            ),
            (
                "seed-109",
                "My iPhone touch screen is not working or responding to touch at all.",
                "If your iPhone touch screen is unresponsive, please try a force restart (press Volume Up, Volume Down, then hold the Side button until the Apple logo appears). If the issue persists, visit https://support.apple.com to book a service appointment.",
                "display_screen",
            ),
            (
                "seed-110",
                "Apps keep crashing or won't download from App Store on my iPhone.",
                "To resolve app issues, force restart your device, ensure you are connected to Wi-Fi, and check the App Store for updates. Note that iOS only supports apps installed from the official Apple App Store.",
                "app_crashes",
            ),
        ]

        for tid, cust, brand, intent in sample_threads:
            th_res = await session.execute(select(Thread).where(Thread.tweet_id == tid))
            if not th_res.scalars().first():
                vec = embedder.embed_text(cust)
                session.add(
                    Thread(
                        tweet_id=tid,
                        customer_message=cust,
                        brand_reply=brand,
                        text_clean=brand,
                        author_type="customer",
                        is_dm_request=False,
                        intent_label=intent,
                        embedding=vec,
                    )
                )

        for tid, cust, brand, intent in sample_threads:
            kb_res = await session.execute(select(KnowledgeEntry).where(KnowledgeEntry.customer_message == cust))
            if not kb_res.scalars().first():
                vec = embedder.embed_text(cust)
                session.add(
                    KnowledgeEntry(
                        source_type="seed_dataset",
                        customer_message=cust,
                        resolution_text=brand,
                        intent=intent,
                        embedding=vec,
                        times_retrieved=1,
                        times_helpful=1,
                        helpfulness_ratio=1.0,
                        is_active=True,
                    )
                )

        # Seed default system configuration
        cfg_check = await session.execute(select(SystemConfig).limit(1))
        if not cfg_check.scalars().first():
            logger.info("Seeding default system configuration...")
            default_configs = [
                SystemConfig(
                    key="escalation_thresholds",
                    value={"min_intent_confidence": 0.65, "min_draft_confidence": 0.65},
                    description="Minimum confidence score thresholds before triggering automated escalation.",
                ),
                SystemConfig(
                    key="rag_weights",
                    value={"vector_weight": 0.7, "helpfulness_weight": 0.3},
                    description="Linear combination weights for pgvector similarity vs agent helpfulness ratio.",
                ),
                SystemConfig(
                    key="brand_rules",
                    value={"max_tweet_chars": 280, "max_dm_chars": 500, "tone": "empathetic"},
                    description="Brand voice guidelines for response drafting.",
                ),
            ]
            session.add_all(default_configs)

            # Seed an initial open ticket for the demo inbox
            demo_ticket = Ticket(
                customer_text="Hey @AppleSupport, my iPhone 14 stopped charging overnight. It vibrates once when plugged in but doesn't take charge.",
                tweet_author="@ios_user99",
                source_tweet_id="demo-tweet-001",
                status="open",
            )
            session.add(demo_ticket)
            await session.commit()
            logger.info("Seed threads, knowledge base, system config, and demo ticket created successfully.")


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    asyncio.run(init_db())

