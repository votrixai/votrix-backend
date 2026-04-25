"""
Generate a real estate rental poster using Pillow.
Overlays text layout on top of a property image.
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pathlib import Path

FONT_PATH = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
SRC_IMAGE = Path("/home/zyue/votrix-v2/76f51631871a78f6b0cf138a9fb55ffa.jpg")
OUT = Path("/home/zyue/votrix-v2/votrix-backend/scripts/generated_images/poster_rental.png")
OUT.parent.mkdir(exist_ok=True)

# --- poster data ---
DATA = {
    "tag": "整层招租",
    "price": "¥3,000",
    "price_unit": "元/月",
    "title": "阳光国际商务大楼",
    "subtitle": "连云港 · 连云区海边大道 · 8层",
    "features": ["180㎡", "三室一厅二卫", "中央空调", "全屋地板", "办公家具齐全"],
    "contact_hint": "扫码或电话咨询",
}

W, H = 1080, 1350  # 4:5 竖版


def load_fonts():
    return {
        "tag":     ImageFont.truetype(FONT_PATH, 36),
        "price":   ImageFont.truetype(FONT_PATH, 96),
        "unit":    ImageFont.truetype(FONT_PATH, 36),
        "title":   ImageFont.truetype(FONT_PATH, 56),
        "subtitle":ImageFont.truetype(FONT_PATH, 32),
        "feature": ImageFont.truetype(FONT_PATH, 34),
        "hint":    ImageFont.truetype(FONT_PATH, 28),
    }


def make_poster(data: dict) -> Image.Image:
    fonts = load_fonts()

    # 1. background image — crop & resize to fill
    bg = Image.open(SRC_IMAGE).convert("RGB")
    bg_ratio = bg.width / bg.height
    target_ratio = W / H
    if bg_ratio > target_ratio:
        new_h = H
        new_w = int(H * bg_ratio)
    else:
        new_w = W
        new_h = int(W / bg_ratio)
    bg = bg.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - W) // 2
    top = (new_h - H) // 2
    bg = bg.crop((left, top, left + W, top + H))

    # slight blur to soften background
    bg = bg.filter(ImageFilter.GaussianBlur(radius=1.5))

    canvas = bg.copy()
    draw = ImageDraw.Draw(canvas)

    # 2. top gradient overlay (dark → transparent) for tag area
    top_overlay = Image.new("RGBA", (W, 220), (0, 0, 0, 0))
    top_draw = ImageDraw.Draw(top_overlay)
    for y in range(220):
        alpha = int(160 * (1 - y / 220))
        top_draw.line([(0, y), (W, y)], fill=(0, 0, 0, alpha))
    canvas = canvas.convert("RGBA")
    canvas.alpha_composite(top_overlay, (0, 0))

    # 3. bottom card — frosted dark panel
    card_top = H - 480
    card = Image.new("RGBA", (W, H - card_top), (10, 20, 40, 210))
    canvas.alpha_composite(card, (0, card_top))

    # thin gold accent line at card top
    accentH = 4
    accent = Image.new("RGBA", (W, accentH), (212, 175, 55, 255))
    canvas.alpha_composite(accent, (0, card_top))

    draw = ImageDraw.Draw(canvas)
    gold = (212, 175, 55, 255)
    white = (255, 255, 255, 255)
    light = (200, 210, 230, 255)

    # 4. top-left tag pill
    tag_text = data["tag"]
    tag_bbox = draw.textbbox((0, 0), tag_text, font=fonts["tag"])
    tag_w = tag_bbox[2] - tag_bbox[0] + 40
    tag_h = tag_bbox[3] - tag_bbox[1] + 18
    pill = Image.new("RGBA", (tag_w, tag_h), (212, 175, 55, 230))
    canvas.alpha_composite(pill, (40, 36))
    draw.text((40 + 20, 36 + 9), tag_text, font=fonts["tag"], fill=(10, 20, 40, 255))

    # 5. price row
    price_y = card_top + 30
    draw.text((54, price_y), data["price"], font=fonts["price"], fill=gold)
    price_bbox = draw.textbbox((54, price_y), data["price"], font=fonts["price"])
    draw.text((price_bbox[2] + 10, price_y + 58), data["price_unit"], font=fonts["unit"], fill=light)

    # 6. title + subtitle
    title_y = price_y + 112
    draw.text((54, title_y), data["title"], font=fonts["title"], fill=white)
    sub_y = title_y + 68
    draw.text((54, sub_y), data["subtitle"], font=fonts["subtitle"], fill=light)

    # 7. divider
    div_y = sub_y + 52
    draw.line([(54, div_y), (W - 54, div_y)], fill=(212, 175, 55, 120), width=1)

    # 8. feature tags
    feat_y = div_y + 20
    x = 54
    for feat in data["features"]:
        fb = draw.textbbox((0, 0), feat, font=fonts["feature"])
        fw = fb[2] - fb[0] + 28
        fh = fb[3] - fb[1] + 14
        tag_img = Image.new("RGBA", (fw, fh), (212, 175, 55, 40))
        canvas.alpha_composite(tag_img, (x, feat_y))
        # border
        draw2 = ImageDraw.Draw(canvas)
        draw2.rectangle([x, feat_y, x + fw - 1, feat_y + fh - 1],
                        outline=(212, 175, 55, 180), width=1)
        draw2.text((x + 14, feat_y + 7), feat, font=fonts["feature"], fill=gold)
        x += fw + 16

    # 9. bottom hint
    hint_y = H - 52
    draw.text((54, hint_y), data["contact_hint"], font=fonts["hint"], fill=light)

    return canvas.convert("RGB")


if __name__ == "__main__":
    poster = make_poster(DATA)
    poster.save(OUT, quality=95)
    print(f"Saved → {OUT}")
