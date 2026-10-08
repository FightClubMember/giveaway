"""Database repository implementations for all database interactions.
Follows clean architecture and proper async query patterns.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy import select, update, delete, func, desc, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    User,
    Giveaway,
    GiveawayRequirement,
    Participant,
    Entry,
    Referral,
    Winner,
    WinnerClaim,
    AdminLog,
    Broadcast,
    PromoCode,
    PromoCodeRedemption,
    GiveawayStatus,
    EntryType,
    ClaimStatus,
    utcnow,
)


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: int) -> Optional[User]:
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create(
        self,
        user_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        referrer_id: Optional[int] = None,
    ) -> Tuple[User, bool]:
        user = await self.get_by_id(user_id)
        if user:
            # Update profile fields if changed
            changed = False
            if user.username != username:
                user.username = username
                changed = True
            if user.first_name != first_name:
                user.first_name = first_name
                changed = True
            if user.last_name != last_name:
                user.last_name = last_name
                changed = True
            if changed:
                user.updated_at = utcnow()
                await self.session.flush()
            return user, False

        # Do not allow self-referral
        valid_referrer_id = referrer_id if (referrer_id and referrer_id != user_id) else None

        user = User(
            id=user_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            referrer_id=valid_referrer_id,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        self.session.add(user)
        await self.session.flush()

        # If has a valid referrer, register the referral record
        if valid_referrer_id:
            # Check referrer exists
            ref_stmt = select(User).where(User.id == valid_referrer_id)
            ref_result = await self.session.execute(ref_stmt)
            if ref_result.scalar_one_or_none():
                referral = Referral(
                    referrer_id=valid_referrer_id,
                    referred_id=user_id,
                    is_valid=False,
                    created_at=utcnow(),
                )
                self.session.add(referral)
                await self.session.flush()

        return user, True

    async def set_banned(self, user_id: int, is_banned: bool, reason: Optional[str] = None) -> bool:
        stmt = update(User).where(User.id == user_id).values(is_banned=is_banned, ban_reason=reason, updated_at=utcnow())
        res = await self.session.execute(stmt)
        return res.rowcount > 0

    async def get_banned_users(self, limit: int = 50) -> List[User]:
        stmt = select(User).where(User.is_banned.is_(True)).order_by(desc(User.updated_at)).limit(limit)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def update_daily_bonus(self, user_id: int) -> bool:
        stmt = update(User).where(User.id == user_id).values(last_daily_bonus_at=utcnow())
        res = await self.session.execute(stmt)
        return res.rowcount > 0

    async def count_users(self) -> int:
        stmt = select(func.count(User.id))
        res = await self.session.execute(stmt)
        return res.scalar() or 0

    async def count_banned_users(self) -> int:
        stmt = select(func.count(User.id)).where(User.is_banned.is_(True))
        res = await self.session.execute(stmt)
        return res.scalar() or 0

    async def get_all_active_user_ids(self) -> List[int]:
        stmt = select(User.id).where(User.is_banned.is_(False))
        res = await self.session.execute(stmt)
        return list(res.scalars().all())


class GiveawayRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        title: str,
        description: str,
        prize: str,
        winners_count: int,
        end_time: datetime,
        referral_bonus: int = 1,
        max_entries_per_user: int = 100,
        image_url: Optional[str] = None,
        rules: Optional[str] = None,
        created_by: Optional[int] = None,
        auto_draw: bool = True,
        claim_type: str = "manual",
        secret_reward: Optional[str] = None,
        custom_claim_prompt: Optional[str] = None,
    ) -> Giveaway:
        giveaway = Giveaway(
            title=title,
            description=description,
            prize=prize,
            winners_count=winners_count,
            status=GiveawayStatus.ACTIVE.value,
            start_time=utcnow(),
            end_time=end_time,
            referral_bonus=referral_bonus,
            max_entries_per_user=max_entries_per_user,
            image_url=image_url,
            rules=rules,
            auto_draw=auto_draw,
            created_by=created_by,
            claim_type=claim_type,
            secret_reward=secret_reward,
            custom_claim_prompt=custom_claim_prompt,
            created_at=utcnow(),
        )
        self.session.add(giveaway)
        await self.session.flush()
        return giveaway

    async def update_reward_settings(
        self,
        giveaway_id: int,
        claim_type: str,
        secret_reward: Optional[str] = None,
        custom_claim_prompt: Optional[str] = None,
    ) -> bool:
        stmt = (
            update(Giveaway)
            .where(Giveaway.id == giveaway_id)
            .values(
                claim_type=claim_type,
                secret_reward=secret_reward,
                custom_claim_prompt=custom_claim_prompt,
            )
        )
        res = await self.session.execute(stmt)
        return res.rowcount > 0

    async def get_by_id(self, giveaway_id: int) -> Optional[Giveaway]:
        stmt = select(Giveaway).where(Giveaway.id == giveaway_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_active_giveaways(self, offset: int = 0, limit: int = 10) -> List[Giveaway]:
        stmt = (
            select(Giveaway)
            .where(Giveaway.status == GiveawayStatus.ACTIVE.value)
            .order_by(Giveaway.end_time.asc())
            .offset(offset)
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def count_active(self) -> int:
        stmt = select(func.count(Giveaway.id)).where(Giveaway.status == GiveawayStatus.ACTIVE.value)
        res = await self.session.execute(stmt)
        return res.scalar() or 0

    async def get_ended_giveaways(self, offset: int = 0, limit: int = 10) -> List[Giveaway]:
        stmt = (
            select(Giveaway)
            .where(Giveaway.status == GiveawayStatus.ENDED.value)
            .order_by(desc(Giveaway.ended_at))
            .offset(offset)
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def count_ended(self) -> int:
        stmt = select(func.count(Giveaway.id)).where(Giveaway.status == GiveawayStatus.ENDED.value)
        res = await self.session.execute(stmt)
        return res.scalar() or 0

    async def get_due_active_giveaways(self) -> List[Giveaway]:
        now = utcnow()
        stmt = (
            select(Giveaway)
            .where(
                and_(
                    Giveaway.status == GiveawayStatus.ACTIVE.value,
                    Giveaway.end_time <= now,
                    Giveaway.auto_draw.is_(True),
                )
            )
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def update_status(self, giveaway_id: int, status: GiveawayStatus) -> bool:
        values: Dict[str, Any] = {"status": status.value}
        if status == GiveawayStatus.ENDED:
            values["ended_at"] = utcnow()
        stmt = update(Giveaway).where(Giveaway.id == giveaway_id).values(**values)
        res = await self.session.execute(stmt)
        return res.rowcount > 0

    async def delete_giveaway(self, giveaway_id: int) -> bool:
        stmt = delete(Giveaway).where(Giveaway.id == giveaway_id)
        res = await self.session.execute(stmt)
        return res.rowcount > 0


class RequirementRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(
        self,
        chat_id: str,
        title: str,
        username: Optional[str] = None,
        invite_link: Optional[str] = None,
        giveaway_id: Optional[int] = None,
        is_mandatory: bool = True,
    ) -> GiveawayRequirement:
        req = GiveawayRequirement(
            chat_id=chat_id,
            title=title,
            username=username,
            invite_link=invite_link,
            giveaway_id=giveaway_id,
            is_mandatory=is_mandatory,
            created_at=utcnow(),
        )
        self.session.add(req)
        await self.session.flush()
        return req

    async def get_for_giveaway(self, giveaway_id: int) -> List[GiveawayRequirement]:
        stmt = (
            select(GiveawayRequirement)
            .where(or_(GiveawayRequirement.giveaway_id == giveaway_id, GiveawayRequirement.giveaway_id.is_(None)))
            .order_by(GiveawayRequirement.id.asc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_global_requirements(self) -> List[GiveawayRequirement]:
        stmt = (
            select(GiveawayRequirement)
            .where(GiveawayRequirement.giveaway_id.is_(None))
            .order_by(GiveawayRequirement.id.asc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def remove(self, requirement_id: int) -> bool:
        stmt = delete(GiveawayRequirement).where(GiveawayRequirement.id == requirement_id)
        res = await self.session.execute(stmt)
        return res.rowcount > 0


class ParticipantRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, giveaway_id: int, user_id: int) -> Participant:
        participant = Participant(
            giveaway_id=giveaway_id,
            user_id=user_id,
            is_verified=True,
            joined_at=utcnow(),
        )
        self.session.add(participant)
        await self.session.flush()
        return participant

    async def is_participant(self, giveaway_id: int, user_id: int) -> bool:
        stmt = select(Participant.id).where(
            and_(Participant.giveaway_id == giveaway_id, Participant.user_id == user_id)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none() is not None

    async def count_for_giveaway(self, giveaway_id: int) -> int:
        stmt = select(func.count(Participant.id)).where(Participant.giveaway_id == giveaway_id)
        res = await self.session.execute(stmt)
        return res.scalar() or 0

    async def get_user_participated_giveaway_ids(self, user_id: int) -> List[int]:
        stmt = select(Participant.giveaway_id).where(Participant.user_id == user_id)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_all_for_giveaway(self, giveaway_id: int) -> List[Participant]:
        stmt = select(Participant).where(Participant.giveaway_id == giveaway_id)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())


class EntryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(
        self,
        giveaway_id: int,
        user_id: int,
        entry_type: EntryType,
        amount: int = 1,
        reference_id: Optional[str] = None,
    ) -> Entry:
        entry = Entry(
            giveaway_id=giveaway_id,
            user_id=user_id,
            entry_type=entry_type.value,
            amount=amount,
            reference_id=reference_id,
            created_at=utcnow(),
        )
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def get_user_entries_for_giveaway(self, giveaway_id: int, user_id: int) -> int:
        stmt = select(func.sum(Entry.amount)).where(
            and_(Entry.giveaway_id == giveaway_id, Entry.user_id == user_id)
        )
        res = await self.session.execute(stmt)
        return res.scalar() or 0

    async def get_user_entries_breakdown(self, giveaway_id: int, user_id: int) -> Dict[str, int]:
        stmt = (
            select(Entry.entry_type, func.sum(Entry.amount))
            .where(and_(Entry.giveaway_id == giveaway_id, Entry.user_id == user_id))
            .group_by(Entry.entry_type)
        )
        res = await self.session.execute(stmt)
        breakdown = {t.value: 0 for t in EntryType}
        for etype, total in res.all():
            breakdown[etype] = total or 0
        return breakdown

    async def get_user_all_entries_breakdown(self, user_id: int) -> Dict[str, int]:
        stmt = (
            select(Entry.entry_type, func.sum(Entry.amount))
            .where(Entry.user_id == user_id)
            .group_by(Entry.entry_type)
        )
        res = await self.session.execute(stmt)
        breakdown = {t.value: 0 for t in EntryType}
        for etype, total in res.all():
            breakdown[etype] = total or 0
        return breakdown

    async def count_for_giveaway(self, giveaway_id: int) -> int:
        stmt = select(func.sum(Entry.amount)).where(Entry.giveaway_id == giveaway_id)
        res = await self.session.execute(stmt)
        return res.scalar() or 0

    async def count_total_all_entries(self) -> int:
        stmt = select(func.sum(Entry.amount))
        res = await self.session.execute(stmt)
        return res.scalar() or 0

    async def get_pool_for_giveaway(self, giveaway_id: int) -> List[Tuple[int, int]]:
        """Returns list of (user_id, entry_count) for fair weighted random draw."""
        stmt = (
            select(Entry.user_id, func.sum(Entry.amount))
            .where(Entry.giveaway_id == giveaway_id)
            .group_by(Entry.user_id)
        )
        res = await self.session.execute(stmt)
        return [(uid, int(count or 1)) for uid, count in res.all()]


class ReferralRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_referred_id(self, referred_id: int) -> Optional[Referral]:
        stmt = select(Referral).where(Referral.referred_id == referred_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def mark_valid(self, referred_id: int) -> Optional[Referral]:
        ref = await self.get_by_referred_id(referred_id)
        if ref and not ref.is_valid:
            ref.is_valid = True
            ref.rewarded_at = utcnow()
            await self.session.flush()
            return ref
        return None

    async def count_valid_for_user(self, user_id: int) -> int:
        stmt = select(func.count(Referral.id)).where(
            and_(Referral.referrer_id == user_id, Referral.is_valid.is_(True))
        )
        res = await self.session.execute(stmt)
        return res.scalar() or 0

    async def count_total_for_user(self, user_id: int) -> int:
        stmt = select(func.count(Referral.id)).where(Referral.referrer_id == user_id)
        res = await self.session.execute(stmt)
        return res.scalar() or 0

    async def count_all_valid(self) -> int:
        stmt = select(func.count(Referral.id)).where(Referral.is_valid.is_(True))
        res = await self.session.execute(stmt)
        return res.scalar() or 0


class WinnerRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(
        self,
        giveaway_id: int,
        user_id: int,
        rank: int,
        entries_count: int,
        selection_hash: Optional[str] = None,
    ) -> Winner:
        winner = Winner(
            giveaway_id=giveaway_id,
            user_id=user_id,
            rank=rank,
            entries_count=entries_count,
            selection_hash=selection_hash,
            selected_at=utcnow(),
        )
        self.session.add(winner)
        await self.session.flush()
        return winner

    async def get_for_giveaway(self, giveaway_id: int) -> List[Winner]:
        stmt = (
            select(Winner)
            .where(Winner.giveaway_id == giveaway_id)
            .order_by(Winner.rank.asc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_by_giveaway_and_user(self, giveaway_id: int, user_id: int) -> Optional[Winner]:
        stmt = select(Winner).where(
            and_(Winner.giveaway_id == giveaway_id, Winner.user_id == user_id)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_user_wins(self, user_id: int) -> List[Winner]:
        stmt = select(Winner).where(Winner.user_id == user_id).order_by(desc(Winner.selected_at))
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def count_user_wins(self, user_id: int) -> int:
        stmt = select(func.count(Winner.id)).where(Winner.user_id == user_id)
        res = await self.session.execute(stmt)
        return res.scalar() or 0

    async def count_total_winners(self) -> int:
        stmt = select(func.count(Winner.id))
        res = await self.session.execute(stmt)
        return res.scalar() or 0


class WinnerClaimRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        winner_id: int,
        giveaway_id: int,
        user_id: int,
        claim_data: str,
        expires_at: datetime,
    ) -> WinnerClaim:
        claim = WinnerClaim(
            winner_id=winner_id,
            giveaway_id=giveaway_id,
            user_id=user_id,
            claim_data=claim_data,
            status=ClaimStatus.PENDING.value,
            expires_at=expires_at,
            claimed_at=utcnow(),
        )
        self.session.add(claim)
        await self.session.flush()
        return claim

    async def get_by_winner_id(self, winner_id: int) -> Optional[WinnerClaim]:
        stmt = select(WinnerClaim).where(WinnerClaim.winner_id == winner_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_id(self, claim_id: int) -> Optional[WinnerClaim]:
        stmt = select(WinnerClaim).where(WinnerClaim.id == claim_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_pending_claims(self, limit: int = 50) -> List[WinnerClaim]:
        stmt = (
            select(WinnerClaim)
            .where(WinnerClaim.status == ClaimStatus.PENDING.value)
            .order_by(WinnerClaim.claimed_at.asc())
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def update_status(
        self,
        claim_id: int,
        status: ClaimStatus,
        notes: Optional[str] = None,
        reviewed_by: Optional[int] = None,
    ) -> bool:
        values: Dict[str, Any] = {
            "status": status.value,
            "reviewed_at": utcnow(),
        }
        if notes is not None:
            values["admin_notes"] = notes
        if reviewed_by is not None:
            values["reviewed_by"] = reviewed_by

        stmt = update(WinnerClaim).where(WinnerClaim.id == claim_id).values(**values)
        res = await self.session.execute(stmt)
        return res.rowcount > 0


class AdminLogRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def log(self, admin_id: int, action: str, details: str) -> AdminLog:
        log_entry = AdminLog(
            admin_id=admin_id,
            action=action,
            details=details,
            created_at=utcnow(),
        )
        self.session.add(log_entry)
        await self.session.flush()
        return log_entry

    async def get_recent(self, limit: int = 20) -> List[AdminLog]:
        stmt = select(AdminLog).order_by(desc(AdminLog.created_at)).limit(limit)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())


class BroadcastRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, admin_id: int, message_text: str, total_targets: int) -> Broadcast:
        broadcast = Broadcast(
            admin_id=admin_id,
            message_text=message_text,
            total_targets=total_targets,
            sent_count=0,
            failed_count=0,
            status="in_progress",
            created_at=utcnow(),
        )
        self.session.add(broadcast)
        await self.session.flush()
        return broadcast

    async def finish(self, broadcast_id: int, sent_count: int, failed_count: int) -> bool:
        stmt = (
            update(Broadcast)
            .where(Broadcast.id == broadcast_id)
            .values(
                sent_count=sent_count,
                failed_count=failed_count,
                status="completed",
                completed_at=utcnow(),
            )
        )
        res = await self.session.execute(stmt)
        return res.rowcount > 0


class PromoRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        code: str,
        entries_amount: int = 5,
        max_uses: int = 100,
        giveaway_id: Optional[int] = None,
        created_by: Optional[int] = None,
    ) -> PromoCode:
        promo = PromoCode(
            code=code.upper().strip(),
            giveaway_id=giveaway_id,
            entries_amount=entries_amount,
            max_uses=max_uses,
            uses_count=0,
            created_by=created_by,
            created_at=utcnow(),
        )
        self.session.add(promo)
        await self.session.flush()
        return promo

    async def get_by_code(self, code: str) -> Optional[PromoCode]:
        stmt = select(PromoCode).where(PromoCode.code == code.upper().strip())
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def is_redeemed_by_user(self, code_id: int, user_id: int) -> bool:
        stmt = select(PromoCodeRedemption.id).where(
            and_(PromoCodeRedemption.code_id == code_id, PromoCodeRedemption.user_id == user_id)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none() is not None

    async def redeem(self, code_id: int, user_id: int) -> bool:
        redemption = PromoCodeRedemption(
            code_id=code_id,
            user_id=user_id,
            redeemed_at=utcnow(),
        )
        self.session.add(redemption)
        stmt = update(PromoCode).where(PromoCode.id == code_id).values(uses_count=PromoCode.uses_count + 1)
        await self.session.execute(stmt)
        await self.session.flush()
        return True

    async def get_all(self, limit: int = 20) -> List[PromoCode]:
        stmt = select(PromoCode).order_by(desc(PromoCode.created_at)).limit(limit)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())


class LeaderboardRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_top_referrers(self, limit: int = 10) -> List[Tuple[User, int]]:
        stmt = (
            select(User, func.count(Referral.id).label("ref_count"))
            .join(Referral, Referral.referrer_id == User.id)
            .where(Referral.is_valid.is_(True))
            .group_by(User.id)
            .order_by(desc("ref_count"))
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return [(u, count) for u, count in res.all()]

    async def get_top_ticket_holders(self, limit: int = 10) -> List[Tuple[User, int]]:
        stmt = (
            select(User, func.sum(Entry.amount).label("ticket_sum"))
            .join(Entry, Entry.user_id == User.id)
            .group_by(User.id)
            .order_by(desc("ticket_sum"))
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return [(u, int(tsum or 0)) for u, tsum in res.all()]
