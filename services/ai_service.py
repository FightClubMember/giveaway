"""Groq AI intelligence service for John's Giveaway Bot.
Powers intelligent Q&A for users, marketing copy generation for admins, and analytics insights.
"""

import logging
from typing import Optional, Dict, Any
from config import settings

logger = logging.getLogger(__name__)


class GroqAIService:
    _client = None

    @classmethod
    def get_client(cls):
        if cls._client is None and settings.GROQ_API_KEY:
            try:
                from groq import AsyncGroq
                cls._client = AsyncGroq(api_key=settings.GROQ_API_KEY)
            except Exception as e:
                logger.warning("Could not initialize Groq client: %s", e)
                cls._client = None
        return cls._client

    @classmethod
    async def answer_user_query(cls, user_name: str, query: str, context: Optional[str] = None) -> str:
        """Answer user questions about John's Giveaway Bot, prizes, entry rules, and referrals."""
        client = cls.get_client()
        system_prompt = (
            "You are John Bhai (John's AI Concierge) for John's Giveaway Bot. "
            "You speak in hardcore friendly, super casual, energetic Hinglish "
            "(mix of Hindi and English, like: 'Arre bhai!', 'Bindaas sun bro...', 'Ekdum mast scene hai!'). "
            "Help Telegram users understand how giveaways work, how to get extra lottery tickets via referrals, "
            "daily bonus tickets, fair computer lucky draws, and prize claims via UPI/Crypto. "
            "Always be super warm, brotherly, motivating, and keep answers short, crisp with clean emojis and HTML tags."
        )
        user_prompt = f"Bhai '{user_name}' pooch raha hai: {query}"
        if context:
            user_prompt += f"\n\nActive giveaways ki jaankari:\n{context}"

        if client:
            try:
                response = await client.chat.completions.create(
                    model=settings.GROQ_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.7,
                    max_tokens=400,
                )
                return response.choices[0].message.content or "Bhai abhi AI ka reply generate nahi ho paya, 1 min baad poochna!"
            except Exception as e:
                logger.warning("Groq AI API error: %s", e)

        # Smart fallback if Groq API key is not yet configured (Casual, hardcore friendly Hinglish)
        query_lower = query.lower()
        if "referral" in query_lower or "invite" in query_lower or "dost" in query_lower:
            return (
                "👥 <b>Bhai Dost Bulao (Referral System) Samajh:</b>\n\n"
                "Neeche <b>👥 Dost Bulao (Refer)</b> pe tap karo, apna unique link dosto ko share karo WhatsApp ya Telegram pe. "
                "Jaise hi tumhara dost join karke giveaway enter karega, tumhe turant <b>+1 Extra Ticket</b> mil jayegi! "
                "Jitne zyada dost bulaoge, jeetne ka chance utna 10x badhega bhai! 🚀"
            )
        elif "winner" in query_lower or "draw" in query_lower or "fair" in query_lower or "jeet" in query_lower:
            return (
                "🏆 <b>Lucky Draw Kaise Hota Hai? 100% Fair Scene:</b>\n\n"
                "Bhai yahan koi cheating nahi hoti! Saare winners computer algorithm (SHA-256 random cryptographic code) se chune jaate hain. "
                "Har ek entry tumhari lottery ticket jaisi hai — jitni zyada tickets tumhare paas hongi, computer draw me tumhara naam nikalne ka chance utna tagda hoga!"
            )
        elif "claim" in query_lower or "prize" in query_lower or "paisa" in query_lower:
            return (
                "🎁 <b>Prize Kaise Milega?</b>\n\n"
                "Jab bhi tum jeetoge, bot tumhe turant private message bhejega ek <b>CLAIM PRIZE</b> button ke sath! "
                "Wahan apni UPI ID, Crypto address ya details daal dena, aur John Bhai ke team se prize direct tumhare paas bhej diya jayega! Ekdum fast."
            )
        elif "daily" in query_lower or "streak" in query_lower or "roz" in query_lower:
            return (
                "🔥 <b>Daily Free Ticket Ka Scene:</b>\n\n"
                "Roz bas ek baar bot me aao aur <b>🔥 Daily Free Ticket</b> pe tap karo! "
                "Bina kisi channel join kiye ya kisi mehnat ke +1 ticket free me mil jayegi. Consistency me hi jeet hai bhai!"
            )
        else:
            return (
                "🤖 <b>Arre Bhai! John Bhai Ka AI Concierge Hazir Hai:</b>\n\n"
                "Ye hai tumhara <b>John's Giveaway Hub</b>! Yahan tum:\n"
                "• 1 click me giveaways me enter kar sakte ho\n"
                "• Dosto ko invite karke extra tickets loot sakte ho\n"
                "• Roz free daily ticket claim kar sakte ho\n"
                "• Real Cash, UPI, aur Telegram Premium jeet sakte ho!\n\n"
                "<i>Bindaas neeche buttons dabao aur shuru ho jao bhai!</i>"
            )

    @classmethod
    async def generate_giveaway_copy(
        cls,
        title: str,
        prize: str,
        winners_count: int,
        duration: str,
    ) -> str:
        """Generate high-converting promotional announcement text for admins."""
        client = cls.get_client()
        system_prompt = (
            "You are an expert viral copywriter for Telegram community growth. "
            "Write an irresistible, high-converting giveaway announcement card for Telegram. "
            "Use clean line dividers (━━━━━━━━━━━━━━), punchy emojis, bullet points, and high-urgency call to actions. "
            "Highlight the prize, winners, and referral multiplier."
        )
        user_prompt = (
            f"Write a viral announcement for:\n"
            f"Giveaway: {title}\n"
            f"Prize: {prize}\n"
            f"Winners: {winners_count}\n"
            f"Duration: {duration}\n"
            f"Brand: John's Giveaway Bot"
        )

        if client:
            try:
                response = await client.chat.completions.create(
                    model=settings.GROQ_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.7,
                    max_tokens=350,
                )
                return response.choices[0].message.content or ""
            except Exception as e:
                logger.warning("Groq AI copy generation error: %s", e)

        # High-converting template fallback
        return (
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚡ <b>MEGA GIVEAWAY ALERT</b> ⚡\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🎁 <b>{title.upper()}</b>\n"
            f"💰 <b>Prize:</b> {prize}\n"
            f"🏆 <b>Total Winners:</b> {winners_count}\n"
            f"⏳ <b>Ends In:</b> {duration}\n\n"
            "🔥 <b>How to Enter in 30 Seconds:</b>\n"
            "1️⃣ Tap [JOIN GIVEAWAY] below\n"
            "2️⃣ Join our official channels\n"
            "3️⃣ Verify your membership to secure your entry!\n\n"
            "👥 <b>PRO TIP:</b> Invite friends with your referral link to earn +1 extra ticket per friend!\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "🛡 <i>Powered by John's Giveaway Bot • 100% Fair & Verified</i>"
        )

    @classmethod
    async def analyze_user_odds(
        cls,
        user_name: str,
        user_entries: int,
        total_entries: int,
        winners_count: int,
        giveaway_title: str,
    ) -> str:
        """Calculate and explain mathematically verified winning odds with actionable growth tips."""
        client = cls.get_client()
        if total_entries <= 0:
            percentage = 100.0
        else:
            # Hypergeometric/probabilistic approximate odds:
            # 1 - ( (total_entries - user_entries) / total_entries ) ^ winners_count
            prob_not_winning = (max(0, total_entries - user_entries) / max(1, total_entries)) ** max(1, winners_count)
            percentage = min(100.0, max(0.0, (1.0 - prob_not_winning) * 100.0))

        system_prompt = (
            "You are John's AI Concierge. Give the user an encouraging, analytical, and punchy breakdown "
            "of their winning odds in a Telegram giveaway. Mention how extra referrals and daily check-ins "
            "can boost their chances. Keep it short (3-4 bullet points) with emojis."
        )
        user_prompt = (
            f"User: {user_name}\n"
            f"Giveaway: {giveaway_title}\n"
            f"User Entries: {user_entries}\n"
            f"Total Pool Entries: {total_entries}\n"
            f"Winners to be picked: {winners_count}\n"
            f"Calculated Probability: {percentage:.1f}%\n"
        )

        if client:
            try:
                response = await client.chat.completions.create(
                    model=settings.GROQ_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.6,
                    max_tokens=250,
                )
                return response.choices[0].message.content or ""
            except Exception as e:
                logger.warning("Groq AI odds analysis error: %s", e)

        # Smart deterministic calculation fallback
        return (
            f"📊 <b>ODDS ANALYSIS FOR {giveaway_title.upper()}:</b>\n\n"
            f"• 🎟 Your Tickets: <b>{user_entries}</b> / {total_entries}\n"
            f"• 🎯 Winning Probability: <b>~{percentage:.1f}%</b>\n"
            f"• 💡 <b>Pro Strategy:</b> Each referral adds +1 entry directly to your odds! "
            f"Inviting just 3 friends increases your chance noticeably.\n"
            f"• ⚡ Don't forget to claim your <b>🔥 Daily Bonus</b> every 24h!"
        )

    @classmethod
    async def generate_giveaway_ideas(cls, niche: str = "general") -> str:
        """Generate high-performing giveaway concept ideas for channel admins."""
        client = cls.get_client()
        system_prompt = (
            "You are an expert Telegram growth strategist. Recommend 3 viral giveaway ideas "
            "with attractive prizes, catchy titles, and suggested tasks to maximize viral sharing."
        )
        if client:
            try:
                response = await client.chat.completions.create(
                    model=settings.GROQ_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Giveaway niche: {niche}"},
                    ],
                    temperature=0.8,
                    max_tokens=300,
                )
                return response.choices[0].message.content or ""
            except Exception as e:
                logger.warning("Groq AI idea generation error: %s", e)

        return (
            "💡 <b>TOP GIVEAWAY CONCEPTS FOR CHANNEL GROWTH:</b>\n\n"
            "1️⃣ <b>₹1,000 / $25 UPI or Crypto Fast Drop</b> (Duration: 48h, 3 Winners)\n"
            "   <i>Instant community engagement with high referral virality.</i>\n\n"
            "2️⃣ <b>Telegram Premium 3-Month Subscriptions</b> (Duration: 5 Days, 5 Winners)\n"
            "   <i>Zero shipping hassle, universally desired by Telegram members.</i>\n\n"
            "3️⃣ <b>Gaming / Gadget Mega Pass (AirPods / PS5 Voucher)</b> (Duration: 7 Days, 1 Winner)\n"
            "   <i>Massive growth campaign suitable for community milestone celebrations.</i>"
        )
