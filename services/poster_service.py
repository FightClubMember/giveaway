"""Visual Giveaway Poster and Banner Generator using Pillow.
Creates ultra-premium, high-definition promotional posters and welcome cards.
"""

import io
import math
import logging
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# Search paths for high quality bold and regular fonts
FONT_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"


def _get_font(size: int, bold: bool = True) -> ImageFont.ImageFont:
    """Load the best available TrueType font with graceful fallback."""
    candidates = []
    if bold:
        candidates.extend([
            FONT_DIR / "arialbd.ttf",
            Path("C:/Windows/Fonts/arialbd.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
            Path("/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"),
            FONT_DIR / "arial.ttf",
            Path("C:/Windows/Fonts/arial.ttf"),
        ])
    else:
        candidates.extend([
            FONT_DIR / "arial.ttf",
            Path("C:/Windows/Fonts/arial.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/freefont/FreeSans.ttf"),
        ])

    for p in candidates:
        if p.exists():
            try:
                return ImageFont.truetype(str(p), size)
            except Exception:
                continue

    # Fallback to Pillow default with requested size if supported
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


class PosterService:
    @staticmethod
    def generate_giveaway_poster(
        title: str,
        prize: str,
        winners_count: int,
        time_left: str = "Active",
    ) -> io.BytesIO:
        """Render a high-resolution 1200x675 graphical promotional poster with luxury cyber styling."""
        width = 1200
        height = 675

        # Base dark canvas with rich cyber midnight gradient
        img = Image.new("RGB", (width, height), color=(10, 14, 26))
        draw = ImageDraw.Draw(img)

        # Smooth vertical dark gradient
        for y in range(height):
            ratio = y / height
            r = int(10 + ratio * 15)
            g = int(14 + ratio * 20)
            b = int(28 + ratio * 40)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # Ambient radial glow circles in background (electric violet & cyan)
        # Left ambient glow
        for radius in range(220, 0, -20):
            alpha = int(25 * (1 - radius / 220))
            draw.ellipse(
                [(150 - radius, 120 - radius), (150 + radius, 120 + radius)],
                fill=(35 + alpha, 25 + alpha, 65 + alpha * 2),
            )
        # Right ambient glow
        for radius in range(240, 0, -20):
            alpha = int(25 * (1 - radius / 240))
            draw.ellipse(
                [(width - 180 - radius, height - 140 - radius), (width - 180 + radius, height - 140 + radius)],
                fill=(20 + alpha, 45 + alpha * 2, 70 + alpha * 2),
            )

        # Outer Glass Card with glowing neon border
        pad = 32
        draw.rounded_rectangle(
            [(pad, pad), (width - pad, height - pad)],
            radius=28,
            fill=(17, 22, 38),
            outline=(99, 102, 241),  # Indigo neon
            width=3,
        )

        # Top Header Pill Badge
        badge_w = 460
        badge_h = 44
        badge_x1 = (width - badge_w) // 2
        badge_y1 = pad + 24
        draw.rounded_rectangle(
            [(badge_x1, badge_y1), (badge_x1 + badge_w, badge_y1 + badge_h)],
            radius=22,
            fill=(30, 38, 70),
            outline=(129, 140, 248),
            width=2,
        )
        font_header_badge = _get_font(20, bold=True)
        draw.text(
            (width // 2, badge_y1 + badge_h // 2),
            "✦ JOHN'S GIVEAWAY HUB • EXCLUSIVE DROP ✦",
            fill=(199, 210, 254),
            font=font_header_badge,
            anchor="mm",
        )

        # Main Title (Adaptive font size)
        clean_title = title.strip()
        if len(clean_title) > 36:
            clean_title = clean_title[:33] + "..."
        font_size = 48 if len(clean_title) <= 24 else 38
        font_title = _get_font(font_size, bold=True)
        draw.text((width // 2, 160), clean_title.upper(), fill=(255, 255, 255), font=font_title, anchor="mm")

        # Golden Grand Prize Showcase Container
        box_pad_x = 75
        box_y1 = 215
        box_y2 = 385
        draw.rounded_rectangle(
            [(box_pad_x, box_y1), (width - box_pad_x, box_y2)],
            radius=20,
            fill=(26, 31, 54),
            outline=(245, 158, 11),  # Golden neon amber
            width=3,
        )

        # Gold inner header badge
        prize_badge_w = 260
        prize_badge_h = 36
        pb_x1 = (width - prize_badge_w) // 2
        pb_y1 = box_y1 + 18
        draw.rounded_rectangle(
            [(pb_x1, pb_y1), (pb_x1 + prize_badge_w, pb_y1 + prize_badge_h)],
            radius=18,
            fill=(69, 39, 10),
            outline=(251, 191, 36),
            width=2,
        )
        font_prize_tag = _get_font(18, bold=True)
        draw.text(
            (width // 2, pb_y1 + prize_badge_h // 2),
            "★ GRAND PRIZE REWARD ★",
            fill=(252, 211, 77),
            font=font_prize_tag,
            anchor="mm",
        )

        # Prize text (big, bold, glowing gold/white)
        clean_prize = prize.strip()
        if len(clean_prize) > 35:
            clean_prize = clean_prize[:32] + "..."
        prize_font_size = 56 if len(clean_prize) <= 20 else 44
        font_prize = _get_font(prize_font_size, bold=True)
        draw.text((width // 2, box_y1 + 105), clean_prize, fill=(255, 255, 255), font=font_prize, anchor="mm")

        # Stat Badges (3 horizontal cards)
        badge_y = 420
        badge_card_h = 80
        badge_w_each = 320
        gap = 25
        total_w = 3 * badge_w_each + 2 * gap
        start_x = (width - total_w) // 2

        font_stat_val = _get_font(24, bold=True)
        font_stat_lbl = _get_font(16, bold=False)

        # Stat 1: Winners
        x1 = start_x
        draw.rounded_rectangle(
            [(x1, badge_y), (x1 + badge_w_each, badge_y + badge_card_h)],
            radius=16,
            fill=(23, 29, 50),
            outline=(59, 130, 246),
            width=2,
        )
        draw.text((x1 + badge_w_each // 2, badge_y + 28), f"🏆 {winners_count} WINNER(S)", fill=(147, 197, 253), font=font_stat_val, anchor="mm")
        draw.text((x1 + badge_w_each // 2, badge_y + 56), "Random Fair Draw", fill=(148, 163, 184), font=font_stat_lbl, anchor="mm")

        # Stat 2: Time / Duration
        x2 = x1 + badge_w_each + gap
        draw.rounded_rectangle(
            [(x2, badge_y), (x2 + badge_w_each, badge_y + badge_card_h)],
            radius=16,
            fill=(23, 29, 50),
            outline=(16, 185, 129),
            width=2,
        )
        draw.text((x2 + badge_w_each // 2, badge_y + 28), f"⏳ {time_left}", fill=(110, 231, 183), font=font_stat_val, anchor="mm")
        draw.text((x2 + badge_w_each // 2, badge_y + 56), "Remaining Window", fill=(148, 163, 184), font=font_stat_lbl, anchor="mm")

        # Stat 3: Verified Fair
        x3 = x2 + badge_w_each + gap
        draw.rounded_rectangle(
            [(x3, badge_y), (x3 + badge_w_each, badge_y + badge_card_h)],
            radius=16,
            fill=(23, 29, 50),
            outline=(168, 85, 247),
            width=2,
        )
        draw.text((x3 + badge_w_each // 2, badge_y + 28), "🔐 100% VERIFIED", fill=(216, 180, 254), font=font_stat_val, anchor="mm")
        draw.text((x3 + badge_w_each // 2, badge_y + 56), "Cryptographic Audit", fill=(148, 163, 184), font=font_stat_lbl, anchor="mm")

        # Bottom Call To Action Banner
        cta_y = 560
        cta_w = 680
        cta_h = 52
        cta_x1 = (width - cta_w) // 2
        draw.rounded_rectangle(
            [(cta_x1, cta_y), (cta_x1 + cta_w, cta_y + cta_h)],
            radius=26,
            fill=(79, 70, 229),
            outline=(165, 180, 252),
            width=2,
        )
        font_cta = _get_font(22, bold=True)
        draw.text(
            (width // 2, cta_y + cta_h // 2),
            "👉 TAP 'JOIN GIVEAWAY' TO CLAIM YOUR FREE TICKET!",
            fill=(255, 255, 255),
            font=font_cta,
            anchor="mm",
        )

        buffer = io.BytesIO()
        img.save(buffer, format="PNG", optimize=True)
        buffer.seek(0)
        return buffer

    @staticmethod
    def generate_welcome_poster(
        user_name: str,
        bot_title: str = "JOHN'S GIVEAWAY HUB",
    ) -> io.BytesIO:
        """Render a high-resolution 1200x675 welcome greeting banner."""
        width = 1200
        height = 675

        img = Image.new("RGB", (width, height), color=(10, 14, 26))
        draw = ImageDraw.Draw(img)

        # Deep royal midnight gradient
        for y in range(height):
            ratio = y / height
            r = int(12 + ratio * 16)
            g = int(16 + ratio * 18)
            b = int(32 + ratio * 45)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # Ambient glows
        for radius in range(250, 0, -25):
            alpha = int(30 * (1 - radius / 250))
            draw.ellipse(
                [(width // 2 - radius, 160 - radius), (width // 2 + radius, 160 + radius)],
                fill=(30 + alpha, 25 + alpha, 60 + alpha * 2),
            )

        # Outer Glass Card with border
        pad = 32
        draw.rounded_rectangle(
            [(pad, pad), (width - pad, height - pad)],
            radius=28,
            fill=(17, 22, 38),
            outline=(99, 102, 241),
            width=3,
        )

        # Top Header Pill Badge
        badge_w = 420
        badge_h = 44
        badge_x1 = (width - badge_w) // 2
        badge_y1 = pad + 24
        draw.rounded_rectangle(
            [(badge_x1, badge_y1), (badge_x1 + badge_w, badge_y1 + badge_h)],
            radius=22,
            fill=(30, 38, 70),
            outline=(129, 140, 248),
            width=2,
        )
        font_header_badge = _get_font(20, bold=True)
        draw.text(
            (width // 2, badge_y1 + badge_h // 2),
            "✦ OFFICIAL TELEGRAM GIVEAWAYS ✦",
            fill=(199, 210, 254),
            font=font_header_badge,
            anchor="mm",
        )

        # Main Hub Title
        font_hub = _get_font(48, bold=True)
        draw.text((width // 2, 160), bot_title.upper(), fill=(255, 255, 255), font=font_hub, anchor="mm")

        # User Greeting Box
        clean_user = user_name.strip() if user_name else "Bhai"
        if len(clean_user) > 24:
            clean_user = clean_user[:21] + "..."
        user_box_w = 600
        user_box_h = 60
        ub_x1 = (width - user_box_w) // 2
        ub_y1 = 215
        draw.rounded_rectangle(
            [(ub_x1, ub_y1), (ub_x1 + user_box_w, ub_y1 + user_box_h)],
            radius=30,
            fill=(26, 31, 54),
            outline=(245, 158, 11),  # Golden outline
            width=2,
        )
        font_greeting = _get_font(26, bold=True)
        draw.text(
            (width // 2, ub_y1 + user_box_h // 2),
            f"👋 Welcome, {clean_user}! You're In The Right Place 🔥",
            fill=(251, 191, 36),
            font=font_greeting,
            anchor="mm",
        )

        # 4 Feature Pills Grid (2x2)
        features = [
            ("💰 Free UPI Cash & Crypto", "Direct transfers to verified winners", (59, 130, 246)),
            ("⭐ Telegram Premium Passes", "Instant monthly / yearly gifts", (168, 85, 247)),
            ("🎟 Instant Redeem Vouchers", "Google Play, Steam, BGMI & Amazon", (16, 185, 129)),
            ("🎰 100% Fair Random Draws", "SHA-256 transparent audit proofs", (236, 72, 153)),
        ]

        card_w = 510
        card_h = 75
        col1_x = 75
        col2_x = width - 75 - card_w
        row1_y = 310
        row2_y = 410

        coords = [(col1_x, row1_y), (col2_x, row1_y), (col1_x, row2_y), (col2_x, row2_y)]
        font_feat_title = _get_font(22, bold=True)
        font_feat_desc = _get_font(16, bold=False)

        for (title_f, desc_f, color_accent), (cx, cy) in zip(features, coords):
            draw.rounded_rectangle(
                [(cx, cy), (cx + card_w, cy + card_h)],
                radius=16,
                fill=(23, 29, 50),
                outline=color_accent,
                width=2,
            )
            draw.text((cx + 25, cy + 24), title_f, fill=(255, 255, 255), font=font_feat_title, anchor="lm")
            draw.text((cx + 25, cy + 52), desc_f, fill=(148, 163, 184), font=font_feat_desc, anchor="lm")

        # Bottom CTA Prompt
        cta_y = 540
        cta_w = 720
        cta_h = 56
        cta_x1 = (width - cta_w) // 2
        draw.rounded_rectangle(
            [(cta_x1, cta_y), (cta_x1 + cta_w, cta_y + cta_h)],
            radius=28,
            fill=(79, 70, 229),
            outline=(165, 180, 252),
            width=2,
        )
        font_cta = _get_font(22, bold=True)
        draw.text(
            (width // 2, cta_y + cta_h // 2),
            "🚀 SELECT AN OPTION BELOW & START WINNING!",
            fill=(255, 255, 255),
            font=font_cta,
            anchor="mm",
        )

        buffer = io.BytesIO()
        img.save(buffer, format="PNG", optimize=True)
        buffer.seek(0)
        return buffer
