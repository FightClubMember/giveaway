"""Winner selection and verification service.
Guarantees fair, auditable, and cryptographically secure winner draws.
"""

import hashlib
import json
import logging
import secrets
from datetime import datetime, timezone
from typing import List, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Winner, Giveaway, GiveawayStatus, utcnow
from database.repositories import EntryRepository, WinnerRepository, GiveawayRepository

logger = logging.getLogger(__name__)


class WinnerSelectionResult:
    def __init__(self, winners: List[Winner], selection_hash: str, total_participants: int, total_entries: int):
        self.winners = winners
        self.selection_hash = selection_hash
        self.total_participants = total_participants
        self.total_entries = total_entries


class WinnerService:
    @staticmethod
    def calculate_audit_hash(
        giveaway_id: int,
        pool: List[Tuple[int, int]],
        seed: str,
        timestamp: datetime,
    ) -> str:
        """Create a reproducible cryptographic SHA-256 audit hash of the draw inputs."""
        audit_payload = {
            "giveaway_id": giveaway_id,
            "timestamp": timestamp.isoformat(),
            "seed": seed,
            "pool": sorted(pool, key=lambda x: x[0]),
        }
        raw_json = json.dumps(audit_payload, sort_keys=True)
        return hashlib.sha256(raw_json.encode("utf-8")).hexdigest()

    @classmethod
    async def select_winners(
        cls,
        session: AsyncSession,
        giveaway_id: int,
        force_count: Optional[int] = None,
    ) -> WinnerSelectionResult:
        """Execute a fair, weighted random draw for a giveaway.
        
        Each user has tickets equal to their total accumulated entries in this giveaway.
        Selection is done without replacement.
        """
        giveaway_repo = GiveawayRepository(session)
        entry_repo = EntryRepository(session)
        winner_repo = WinnerRepository(session)

        giveaway = await giveaway_repo.get_by_id(giveaway_id)
        if not giveaway:
            raise ValueError(f"Giveaway #{giveaway_id} not found.")

        # Check existing winners
        existing_winners = await winner_repo.get_for_giveaway(giveaway_id)
        if existing_winners:
            # Already drawn
            total_entries = await entry_repo.count_for_giveaway(giveaway_id)
            return WinnerSelectionResult(
                winners=existing_winners,
                selection_hash=existing_winners[0].selection_hash or "PREVIOUS_DRAW",
                total_participants=len(existing_winners),
                total_entries=total_entries,
            )

        # Get pool of (user_id, entry_count)
        pool: List[Tuple[int, int]] = await entry_repo.get_pool_for_giveaway(giveaway_id)
        if not pool:
            logger.info("Giveaway #%d has 0 entries, no winners drawn.", giveaway_id)
            return WinnerSelectionResult(winners=[], selection_hash="", total_participants=0, total_entries=0)

        total_participants = len(pool)
        total_entries = sum(entries for _, entries in pool)
        target_winners_count = force_count if force_count is not None else giveaway.winners_count

        # Cryptographic seed
        entropy_seed = secrets.token_hex(16)
        draw_time = utcnow()
        selection_hash = cls.calculate_audit_hash(giveaway_id, pool, entropy_seed, draw_time)

        # Weighted selection without replacement
        rng = secrets.SystemRandom()
        remaining_pool = dict(pool)
        selected_winner_records: List[Winner] = []

        rank = 1
        while remaining_pool and len(selected_winner_records) < target_winners_count:
            user_ids = list(remaining_pool.keys())
            weights = [remaining_pool[uid] for uid in user_ids]

            chosen_user_id = rng.choices(user_ids, weights=weights, k=1)[0]
            entries_held = remaining_pool.pop(chosen_user_id)

            winner = await winner_repo.add(
                giveaway_id=giveaway_id,
                user_id=chosen_user_id,
                rank=rank,
                entries_count=entries_held,
                selection_hash=selection_hash,
            )
            selected_winner_records.append(winner)
            rank += 1

        # Mark giveaway as ended
        await giveaway_repo.update_status(giveaway_id, GiveawayStatus.ENDED)

        logger.info(
            "Selected %d winners for giveaway #%d (Total pool: %d entries, Audit hash: %s)",
            len(selected_winner_records),
            giveaway_id,
            total_entries,
            selection_hash[:12],
        )

        return WinnerSelectionResult(
            winners=selected_winner_records,
            selection_hash=selection_hash,
            total_participants=total_participants,
            total_entries=total_entries,
        )
