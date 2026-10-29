#!/usr/bin/env python3
"""Pinterest pins for /gifts/ pages. 1000x1500, same navy/gold chrome as site/media/pins/.

The five hand-made pins stay untouched. Each gift guide gets a new file named for
its slug. Titles are the page h1 (a "$50" in a title is that guide's name, not a
price we invented). Hooks never include a dollar amount.

build.py calls render() while it still has the media copy. Running this file
directly draws one sample pin next to the template.
"""
import os, re
from PIL import Image, ImageDraw, ImageFont

W, H = 1000, 1500
NAVY = (21, 34, 56)
CREAM = (244, 234, 214)
GOLD = (231, 183, 95)
# Legacy pins. render() refuses to write these names.
LEGACY = {
    "holiday-fragrance-gifts.png",
    "cologne-gifts-for-him.png",
    "perfume-gifts-for-her.png",
    "fragrance-gifts-under-50.png",
    "fragrance-gift-sets.png",
}
HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "fonts")
SERIF = os.path.join(FONT_DIR, "PlayfairDisplay-Variable.ttf")
SANS = os.path.join(FONT_DIR, "SourceSans3-Semibold.ttf")
SANS_REG = os.path.join(FONT_DIR, "SourceSans3-Regular.ttf")
# Phrases that stay on one line. Longest first so "for boyfriend" wins over "for".
KEEP = (
    "for mother-in-law", "for father-in-law", "for granddaughter", "for best friend", "for boyfriend", "for girlfriend", "for grandson", "for teen girls", "for teen boys", "for husband", "for wife", "for grandma", "for grandpa", "for teachers", "for daughter", "for stepdad", "for new dad", "for new mom", "for couples", "for niece", "for nephew", "for sister", "for brother", "for teens", "for uncle", "for aunt", "for boss", "for son", "his and hers", "for him", "for her", "for mom", "for dad",
    "stocking stuffers", "stocking stuffer", "travel sizes", "gift sets",
    "under $100", "under $15", "under $20", "under $25", "under $30", "under $40", "under $50", "under $75",
)
# (eyebrow, hook). The hook is a caption, not a price.
META = {
    "gifts": ("HOLIDAY", "Designer bottles, on sale right now."),
    "for-him": ("FOR HIM", "The bottles worth giving him."),
    "for-her": ("FOR HER", "The bottles worth giving her."),
    "under-50": ("BUDGET", "Checked bottles in this budget."),
    "perfume-gifts-for-her-under-50": ("FOR HER", "Women's perfumes in this budget."),
    "best-mens-cologne-under-40": ("FOR HIM", "Men's colognes in this budget."),
    "stocking-stuffer-minis": ("MINIS", "Travel sprays and minis for a stocking."),
    "holiday-gift-sets": ("GIFT SETS", "Boxed sets checked for the holidays."),
    "gift-sets": ("GIFT SETS", "Boxed sets, grouped by brand."),
    "cologne-gifts-for-him-under-50": ("FOR HIM", "Men's colognes picked as gifts."),
    "perfume-gifts-for-her-under-40": ("FOR HER", "Women's perfumes picked as gifts."),
    "fragrance-gifts-for-teens": ("FOR TEENS", "A budget list for a teen gift."),
    "fragrance-gifts-for-coworkers-under-40": ("COWORKERS", "Fresh bottles for an office gift."),
    "fragrance-gifts-for-college-students": ("COLLEGE", "Noted bottles for a student gift."),
    "stocking-stuffer-fragrances": ("STOCKING", "Bottles, minis, and travel sizes."),
    "luxury-fragrance-gifts": ("LUXURY", "Prestige bottles for a big gift."),
    "luxury-fragrance-gifts-under-100": ("LUXURY", "Prestige bottles in this budget."),
    "luxury-cologne-gifts-for-him": ("FOR HIM", "Designer and niche colognes for a big gift."),
    "luxury-perfume-gifts-for-her": ("FOR HER", "Designer and niche perfumes for a big gift."),
    "secret-santa-fragrances-under-30": ("SECRET SANTA", "A list for a gift exchange."),
    "christmas-perfume-gifts-for-mom": ("FOR MOM", "Women's perfumes for mom."),
    "cologne-gifts-for-dad": ("FOR DAD", "Men's colognes for dad."),
    "cologne-gifts-for-boyfriend": ("BOYFRIEND", "Sweet and fresh colognes."),
    "perfume-gifts-for-girlfriend": ("GIRLFRIEND", "Floral and sweet perfumes."),
    "perfume-gifts-for-wife": ("WIFE", "Crowd-pleasing perfumes for a spouse."),
    "cologne-gifts-for-husband": ("HUSBAND", "Colognes worth giving a spouse."),
    "perfume-gifts-for-grandma": ("GRANDMA", "Classic, elegant, comforting scents."),
    "cologne-gifts-for-grandpa": ("GRANDPA", "Timeless, refined colognes."),
    "perfume-gifts-for-sister": ("SISTER", "Crowd-pleasing perfumes for a sister."),
    "cologne-gifts-for-brother": ("BROTHER", "Crowd-pleasing colognes for a brother."),
    "perfume-gifts-for-best-friend": ("BEST FRIEND", "Shareable scents, including unisex bottles."),
    "perfume-gifts-for-mother-in-law": ("MOTHER-IN-LAW", "Classic, elegant, crowd-pleasing scents."),
    "cologne-gifts-for-father-in-law": ("FATHER-IN-LAW", "Polished colognes for an in-law gift."),
    "cologne-gifts-for-son": ("FOR SON", "Starter colognes under a gift cap."),
    "perfume-gifts-for-daughter": ("DAUGHTER", "Fruity and sweet perfumes."),
    "fragrance-gifts-for-teachers-under-40": ("TEACHERS", "Florals and one woody cologne."),
    "perfume-gifts-for-aunt": ("FOR AUNT", "Classic florals for an aunt gift."),
    "cologne-gifts-for-uncle": ("FOR UNCLE", "Fresh colognes for an uncle gift."),
    "fragrance-gifts-for-boss": ("FOR BOSS", "Polished bottles for a workplace gift."),
    "perfume-gifts-for-her-under-30": ("FOR HER", "Women's perfumes in this gift budget."),
    "perfume-gifts-for-niece": ("FOR NIECE", "Bright florals for a niece gift."),
    "cologne-gifts-for-nephew": ("FOR NEPHEW", "Fresh and sweet colognes for a nephew gift."),
    "his-and-hers-fragrance-gifts": ("COUPLES", "Matched pairs from the same house."),
    "hanukkah-fragrance-gifts": ("HANUKKAH", "A list for eight nights."),
    "fragrance-gifts-for-new-mom": ("NEW MOM", "Lighter bottles for a new parent."),
    "perfume-gifts-for-granddaughter": ("GRANDDAUGHTER", "Florals and sweet perfumes for a younger gift."),
    "cologne-gifts-for-grandson": ("GRANDSON", "Fresh and sweet colognes for a younger gift."),
    "cologne-gifts-for-new-dad": ("NEW DAD", "Lighter bottles for a new parent."),
    "perfume-gifts-for-mom-under-50": ("FOR MOM", "Women's perfumes in this gift budget."),
    "christmas-cologne-gifts-for-dad": ("FOR DAD", "Classic colognes for a Christmas gift."),
    "cologne-gifts-for-teen-boys": ("TEEN BOYS", "Fresh colognes for a younger gift."),
    "perfume-gifts-for-teen-girls": ("TEEN GIRLS", "Fruity and sweet perfumes for a younger gift."),
    "cologne-gifts-for-stepdad": ("STEPDAD", "Polished colognes for a stepdad gift."),
    "fragrance-gifts-for-couples": ("COUPLES", "Two house pairs you can give together."),
    "fragrance-stocking-stuffers-under-25": ("STOCKING", "Bottles, minis, and travel sizes."),
}
DEFAULT_EYEBROW = "GIFT GUIDE"
DEFAULT_HOOK = "Checked deals from authorized retailers."

def _font(path, size, weight=None):
    font = ImageFont.truetype(path, size)
    if weight is not None:
        font.set_variation_by_axes([weight])
    return font

def _width(text, font):
    box = font.getbbox(text)
    return box[2] - box[0]

def _tokenize(title):
    rest = re.sub(r"\s+", " ", (title or "").strip())
    tokens = []
    while rest:
        rest = rest.lstrip()
        low = rest.lower()
        hit = next((p for p in KEEP if low.startswith(p) and (len(rest) == len(p) or rest[len(p)].isspace())), None)
        if hit:
            tokens.append(rest[:len(hit)])
            rest = rest[len(hit):]
            continue
        word, _, rest = rest.partition(" ")
        tokens.append(word)
    return tokens

def _cap_line(line):
    line = line.strip()
    if not line:
        return line
    # "and travel sizes" stays a continuation, not a new title.
    if line.lower().startswith(("and ", "or ")):
        return line[0].lower() + line[1:]
    return line[0].upper() + line[1:]

def _group(tokens, n):
    """Split tokens into n lines with close character counts."""
    if n <= 1 or len(tokens) <= 1:
        return [" ".join(tokens)]
    total = sum(len(t) for t in tokens) + len(tokens) - 1
    lines, cur, acc = [], [], 0
    for i, tok in enumerate(tokens):
        cur.append(tok)
        acc += len(tok) + 1
        left_tokens = len(tokens) - i - 1
        left_lines = n - len(lines) - 1
        if left_lines <= 0:
            continue
        # Keep enough tokens for the remaining lines, and break near the target width.
        if left_tokens <= left_lines or acc >= total / n:
            lines.append(" ".join(cur))
            cur, acc = [], 0
    if cur:
        lines.append(" ".join(cur))
    return lines

def _merge_small(tokens):
    """Keep 'and' / 'or' on the same line as the words they join."""
    out = []
    i = 0
    while i < len(tokens):
        if tokens[i].lower() in {"and", "or"} and i + 1 < len(tokens):
            out.append(tokens[i] + " " + tokens[i + 1])
            i += 2
        else:
            out.append(tokens[i])
            i += 1
    return out

def break_title(title, font, max_w):
    tokens = _merge_small(_tokenize(title))
    if not tokens:
        raise SystemExit("pin title is empty")
    best = None
    for n in (3, 2, 4, 1):
        if len(tokens) < n:
            continue
        lines = [_cap_line(line) for line in _group(tokens, n)]
        if any(_width(line, font) > max_w for line in lines):
            continue
        widths = [_width(line, font) for line in lines]
        # Prefer three even lines, then fewer lines, then a smaller widest line.
        score = (0 if n == 3 else 1, max(widths) - min(widths), max(widths), n)
        if best is None or score < best[0]:
            best = (score, lines)
    if best:
        return best[1]
    # One token is wider than the column. The caller shrinks the font and tries again.
    return [_cap_line(" ".join(tokens))]

def _center(draw, text, y, font, fill, cx):
    box = font.getbbox(text)
    x = cx - (box[2] - box[0]) / 2 - box[0]
    draw.text((x, y), text, font=font, fill=fill)
    return box[3] - box[1]

def _tracked(draw, text, y, font, fill, cx, tracking):
    widths = [font.getbbox(ch)[2] - font.getbbox(ch)[0] for ch in text]
    total = sum(widths) + tracking * (len(text) - 1 if text else 0)
    x = cx - total / 2
    for ch, w in zip(text, widths):
        box = font.getbbox(ch)
        draw.text((x - box[0], y), ch, font=font, fill=fill)
        x += w + tracking
    box = font.getbbox(text or "H")
    return box[3] - box[1]

def copy_for(slug):
    eyebrow, hook = META.get(slug, (DEFAULT_EYEBROW, DEFAULT_HOOK))
    if "$" in hook or re.search(r"\d", hook):
        raise SystemExit(f"pin hook for {slug} must not state a price ({hook})")
    return eyebrow, hook

def render(dest, template, slug, title, site_host="scentdealsdaily.com"):
    """Draw one pin. dest must not be one of the five legacy filenames."""
    name = os.path.basename(dest)
    if name in LEGACY:
        raise SystemExit(f"refusing to overwrite legacy pin {name}")
    if os.path.abspath(dest) == os.path.abspath(template):
        raise SystemExit("refusing to draw a pin on top of its template")
    eyebrow, hook = copy_for(slug)
    im = Image.open(template).convert("RGB")
    if im.size != (W, H):
        raise SystemExit(f"pin template is {im.size}, expected {(W, H)}")
    im = im.copy()
    # The shared chrome (frame, wordmark, bottle) ends above y=728.
    # Cover only the old title so the bottle and the frame stay pixel-identical.
    band_box = (64, 736, 936, 1438)
    bw, bh = band_box[2] - band_box[0], band_box[3] - band_box[1]
    scale = 2
    band = Image.new("RGB", (bw * scale, bh * scale), NAVY)
    draw = ImageDraw.Draw(band)
    cx = band.size[0] // 2
    max_w = bw * scale - 48
    lines, font, line_h = None, None, 0
    for size in (76, 70, 64, 58, 52, 46, 40):
        font = _font(SERIF, size * scale, 620)
        lines = break_title(title, font, max_w)
        if any(_width(line, font) > max_w for line in lines):
            continue
        line_h = font.getbbox("Hg")[3] - font.getbbox("Hg")[1]
        if line_h * len(lines) + 18 * scale * (len(lines) - 1) < 460 * scale:
            break
    else:
        raise SystemExit(f"pin title does not fit: {title}")
    eye = _font(SANS, 22 * scale)
    hook_font = _font(SANS_REG, 32 * scale)
    url_font = _font(SANS, 20 * scale)
    # Eyebrow just under the bottle, title in the same band the old pins use.
    y = 18 * scale
    y += _tracked(draw, eyebrow, y, eye, GOLD, cx, 5 * scale) + 28 * scale
    gap = int(line_h * 0.22)
    for line in lines:
        y += _center(draw, line, y, font, CREAM, cx) + gap
    y += 10 * scale
    rule_w = 72 * scale
    draw.rectangle((cx - rule_w // 2, y, cx + rule_w // 2, y + 3 * scale), fill=GOLD)
    y += 28 * scale
    hook_lines = _wrap_hook(hook, hook_font, max_w)
    hgap = int(hook_font.getbbox("Hg")[3] * 0.35)
    for line in hook_lines:
        y += _center(draw, line, y, hook_font, GOLD, cx) + hgap
    url = site_host.lower().removeprefix("https://").removeprefix("http://").strip("/")
    url_y = band.size[1] - 78 * scale
    _tracked(draw, url, url_y, url_font, CREAM, cx, 2 * scale)
    im.paste(band.resize((bw, bh), Image.Resampling.LANCZOS), (band_box[0], band_box[1]))
    os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
    im.save(dest, "PNG")
    return dest

def _wrap_hook(hook, font, max_w):
    words = hook.split()
    lines, cur = [], ""
    for word in words:
        trial = (cur + " " + word).strip()
        if _width(trial, font) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    if not lines or any(_width(line, font) > max_w for line in lines):
        raise SystemExit(f"pin hook does not fit: {hook}")
    return lines

if __name__ == "__main__":
    import sys
    root = os.path.dirname(HERE)
    template = os.path.join(root, "site", "media", "pins", "holiday-fragrance-gifts.png")
    dest = sys.argv[1] if len(sys.argv) > 1 else "/tmp/pin-sample.png"
    render(dest, template, "perfume-gifts-for-girlfriend", "Perfume gifts for girlfriend")
    print("wrote", dest)
