"""Visual Giveaway Poster and Banner Generator using Pillow.
Creates high-definition promotional posters for Telegram announcements.
"""

import io
import logging
from typing import Optional
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


class PosterService:
    @staticmethod
    def generate_giveaway_poster(
        title: str,
        prize: str,
        winners_count: int,
        time_left: str = "Active",
    ) -> io.BytesIO:
        """Render a high-resolution 1000x560 graphical promotional poster."""
        width = 1000
        height = 560

        # Create canvas with rich gradient dark background
        img = Image.new("RGB", (width, height), color=(15, 18, 28))
        draw = ImageDraw.Draw(img)

        # Draw subtle top and bottom highlight banners
        for y in range(height):
            # Gradient factor
            r = int(15 + (y / height) * 12)
            g = int(22 + (y / height) * 15)
            b = int(45 + (y / height) * 35)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # Glowing decorative frame
        draw.rounded_rectangle(
            [(25, 25), (width - 25, height - 25)],
            radius=24,
            outline=(79, 70, 229),
            width=3,
        )

        # Inner subtle card
        draw.rounded_rectangle(
            [(50, 50), (width - 50, height - 50)],
            radius=18,
            fill=(22, 27, 46),
            outline=(99, 102, 241),
            width=1,
        )

        # Default standard fonts with fallbacks
        try:
            font_brand = ImageFont.truetype("arialbd.ttf", 26)
            font_title = ImageFont.truetype("arialbd.ttf", 46)
            font_prize = ImageFont.truetype("arialbd.ttf", 52)
            font_details = ImageFont.truetype("arial.ttf", 28)
            font_badge = ImageFont.truetype("arialbd.ttf", 24)
        except Exception:
            font_brand = ImageFont.load_default()
            font_title = font_brand
            font_prize = font_brand
            font_details = font_brand
            font_badge = font_brand

        # Brand header
        brand_text = "✦ JOHN'S GIVEAWAY BOT • OFFICIAL GIVEAWAY ✦"
        draw.text((width // 2, 85), brand_text, fill=(165, 180, 252), font=font_brand, anchor="mm")

        # Giveaway Title (truncated if long)
        display_title = title if len(title) <= 32 else title[:29] + "..."
        draw.text((width // 2, 160), display_title.upper(), fill=(255, 255, 255), font=font_title, anchor="mm")

        # Prize Card Accent Box
        box_top = 220
        box_bottom = 350
        draw.rounded_rectangle(
            [(100, box_top), (width - 100, box_bottom)],
            radius=16,
            fill=(30, 41, 79),
            outline=(245, 158, 11),  # Golden border
            width=2,
        )

        draw.text((width // 2, 255), "GRAND PRIZE", fill=(251, 191, 36), font=font_brand, anchor="mm")
        display_prize = prize if len(prize) <= 28 else prize[:25] + "..."
        draw.text((width // 2, 305), display_prize, fill=(255, 255, 255), font=font_prize, anchor="mm")

        # Stat Badges Bottom Row
        # Badge 1: Winners Count
        draw.rounded_rectangle([(100, 380), (370, 445)], radius=12, fill=(39, 39, 68))
        draw.text((235, 412), f"🏆 {winners_count} Winner(s)", fill=(226, 232, 240), font=font_badge, anchor="mm")

        # Badge 2: Status / Time Left
        draw.rounded_rectangle([(390, 380), (660, 445)], radius=12, fill=(39, 39, 68))
        draw.text((525, 412), f"⏳ {time_left}", fill=(52, 211, 153), font=font_badge, anchor="mm")

        # Badge 3: 100% Verified Fairness
        draw.rounded_rectangle([(680, 380), (900, 445)], radius=12, fill=(39, 39, 68))
        draw.text((790, 412), "🔐 100% Fair Draw", fill=(192, 132, 252), font=font_badge, anchor="mm")

        # Footer call to action
        draw.text((width // 2, 490), "👉 Tap 'Join Giveaway' in Telegram to enter now!", fill=(148, 163, 184), font=font_details, anchor="mm")

        buffer = io.BytesIO()
        img.save(buffer, format="PNG", optimize=True)
        buffer.seek(0)
        return buffer
