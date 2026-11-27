#!/usr/bin/env python3
"""Render three calm 9:16 shorts into site/media/videos/.

Visuals follow the navy-and-gold bottle cards already on the site. Each short
opens with an honest hook, states one checked price fact, and ends on the
price plus scentdealsdaily.com. No affiliate URL is drawn or requested.

Speech is CMU Flite's slt voice (BSD, from the Arctic recordings). The click
and the music bed are generated in this script, so both are original.

Prices were read on Nov 27, 2026 from the live ScentDealsDaily product pages,
which matched data/deals.json (checked 2026-11-27T01:27:40Z):
  Le Male Le Parfum 4.2 oz  $98.95 vs $142.00 compare-at
  1 Million Lucky 3.4 oz    $75.95 vs $92.00 compare-at
  Replica Jazz Club 3.4 oz  $81.95 vs $170.00 compare-at
"""
import math
import os
import random
import struct
import subprocess
import tempfile
import wave

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_DIR = os.path.join(ROOT, "scripts", "fonts")
OUT_DIR = os.path.join(ROOT, "site", "media", "videos")
W, H = 1080, 1920
NAVY = (14, 24, 48)
GOLD = (224, 177, 90)
CREAM = (247, 241, 230)
MUTED = (198, 192, 180)
FPS = 30
XFADE = 0.40
HOOK_HOLD = 2.20
END_HOLD = 5.00

PRODUCTS = [
    {
        "file": "le-male-le-parfum-newformat.mp4",
        "image": "site/media/products/jean-paul-gaultier-le-male-le-parfum-cologne.jpg",
        "title": "Le Male Le Parfum",
        "line": "Eau de Parfum Intense · 4.2 oz",
        "price": "$98.95",
        "was": "$142.00",
        "knockout": True,
        "speech": (
            "Jean Paul Gaultier Le Male Le Parfum, four point two ounces, "
            "is ninety-eight dollars and ninety-five cents at Fragrance Shop. "
            "The listed compare-at price is one hundred forty-two dollars."
        ),
    },
    {
        "file": "1-million-lucky-newformat.mp4",
        "image": "site/media/products/paco-rabanne-1-million-lucky-cologne.jpg",
        "title": "1 Million Lucky",
        "line": "Eau de Toilette · 3.4 oz",
        "price": "$75.95",
        "was": "$92.00",
        "knockout": False,
        "speech": (
            "Paco Rabanne One Million Lucky, three point four ounces, "
            "is seventy-five dollars and ninety-five cents at Fragrance Shop. "
            "The listed compare-at price is ninety-two dollars."
        ),
    },
    {
        "file": "replica-jazz-club-newformat.mp4",
        "image": "site/media/products/maison-margiela-replica-jazz-club.jpg",
        "title": "Replica Jazz Club",
        "line": "Eau de Toilette · 3.4 oz",
        "price": "$81.95",
        "was": "$170.00",
        "knockout": True,
        "speech": (
            "Maison Margiela Replica Jazz Club, three point four ounces, "
            "is eighty-one dollars and ninety-five cents at Fragrance Shop. "
            "The listed compare-at price is one hundred seventy dollars."
        ),
    },
]


def font(name, size):
    path = os.path.join(FONT_DIR, name)
    return ImageFont.truetype(path, size)


def display(size):
    try:
        return font("PlayfairDisplay-Variable.ttf", size)
    except Exception:
        return font("SourceSans3-Semibold.ttf", size)


def sans(size, semibold=False):
    return font("SourceSans3-Semibold.ttf" if semibold else "SourceSans3-Regular.ttf", size)


def text_width(draw, text, face):
    return draw.textlength(text, font=face)


def center(draw, text, y, face, fill):
    width = text_width(draw, text, face)
    draw.text(((W - width) / 2, y), text, font=face, fill=fill)
    return y


def wrap(draw, text, face, max_width):
    words = text.split()
    lines, cur = [], ""
    for word in words:
        trial = word if not cur else cur + " " + word
        if text_width(draw, trial, face) <= max_width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines or [text]


def canvas():
    image = Image.new("RGB", (W, H), NAVY)
    draw = ImageDraw.Draw(image)
    inset = 42
    draw.rectangle((inset, inset, W - inset, H - inset), outline=GOLD, width=3)
    return image, draw


def knock_white(image, tol=18):
    """Clear near-white pixels that touch the photo edge. Leave interior whites."""
    image = image.convert("RGBA")
    pixels = image.load()
    width, height = image.size
    seen = bytearray(width * height)
    stack = []

    def near(x, y):
        r, g, b, _a = pixels[x, y]
        return r >= 255 - tol and g >= 255 - tol and b >= 255 - tol

    for x in range(width):
        stack.append((x, 0))
        stack.append((x, height - 1))
    for y in range(height):
        stack.append((0, y))
        stack.append((width - 1, y))
    cleared = 0
    while stack:
        x, y = stack.pop()
        index = y * width + x
        if seen[index]:
            continue
        seen[index] = 1
        if not near(x, y):
            continue
        r, g, b, _a = pixels[x, y]
        pixels[x, y] = (r, g, b, 0)
        cleared += 1
        if x + 1 < width:
            stack.append((x + 1, y))
        if x:
            stack.append((x - 1, y))
        if y + 1 < height:
            stack.append((x, y + 1))
        if y:
            stack.append((x, y - 1))
    # A photo that is mostly white margin still keeps the bottle. Abort only when
    # the flood reaches so far that a white box has been eaten with the backdrop.
    if cleared > width * height * 0.88:
        return None
    # One pass to drop a thin white fringe next to cleared pixels.
    fringe = []
    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            if a == 0 or min(r, g, b) < 248:
                continue
            if any(
                0 <= nx < width and 0 <= ny < height and pixels[nx, ny][3] == 0
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
            ):
                fringe.append((x, y))
    for x, y in fringe:
        r, g, b, _a = pixels[x, y]
        pixels[x, y] = (r, g, b, 0)
    return image


def load_bottle(rel, knockout, max_w, max_h):
    image = Image.open(os.path.join(ROOT, rel)).convert("RGBA")
    if knockout:
        cut = knock_white(image)
        if cut is not None:
            image = cut
    bounds = image.getbbox()
    if bounds:
        image = image.crop(bounds)
    scale = min(max_w / image.width, max_h / image.height)
    if abs(scale - 1) > 0.01:
        image = image.resize(
            (max(1, int(image.width * scale)), max(1, int(image.height * scale))),
            Image.Resampling.LANCZOS,
        )
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    # Soften a hard cut edge against the navy field.
    if knockout:
        alpha = image.getchannel("A").filter(ImageFilter.GaussianBlur(0.6))
        image.putalpha(alpha)
    return image


def paste_center(base, sprite, y):
    x = (W - sprite.width) // 2
    base.paste(sprite, (x, int(y)), sprite)


def draw_wordmark(draw, y):
    face = sans(34, semibold=True)
    center(draw, "ScentDealsDaily", y, face, GOLD)
    rule_w = 92
    draw.rectangle(((W - rule_w) / 2, y + 52, (W + rule_w) / 2, y + 56), fill=GOLD)


def card_hook(product):
    image, draw = canvas()
    draw_wordmark(draw, 250)
    title_face = display(78)
    lines = wrap(draw, product["title"], title_face, 900)
    y = 520
    hook = display(64)
    center(draw, "The price we checked", y, hook, CREAM)
    y = 700
    for line in lines:
        center(draw, line, y, title_face, CREAM)
        y += 96
    center(draw, product["line"], y + 20, sans(36), MUTED)
    return image


def card_product(product):
    image, draw = canvas()
    draw_wordmark(draw, 78)
    title_face = display(68)
    lines = wrap(draw, product["title"], title_face, 920)
    y = 180
    for line in lines:
        center(draw, line, y, title_face, CREAM)
        y += 82
    center(draw, product["line"], y + 4, sans(32), MUTED)
    bottle = load_bottle(product["image"], product["knockout"], 860, 820)
    paste_center(image, bottle, 430)
    price_y = 1320
    center(draw, product["price"], price_y, display(108), GOLD)
    center(draw, "at FragranceShop", price_y + 130, sans(36, semibold=True), CREAM)
    center(draw, f"Compare-at {product['was']}", price_y + 184, sans(32), MUTED)
    center(draw, "Price checked Nov 27, 2026 and may change", 1728, sans(28), MUTED)
    center(draw, "ScentDealsDaily  ·  Ad", 1790, sans(26), GOLD)
    return image


def card_end(product):
    image, draw = canvas()
    draw_wordmark(draw, 280)
    center(draw, "The price we checked", 520, display(58), CREAM)
    lines = wrap(draw, product["title"], display(64), 920)
    y = 640
    for line in lines:
        center(draw, line, y, display(64), CREAM)
        y += 80
    center(draw, product["price"], y + 40, display(120), GOLD)
    center(draw, f"Compare-at {product['was']}  ·  FragranceShop", y + 190, sans(34), MUTED)
    center(draw, "scentdealsdaily.com", 1500, display(52), CREAM)
    center(draw, "Price checked Nov 27, 2026 and may change", 1620, sans(30), MUTED)
    return image


def write_wav(path, samples, rate=44100):
    with wave.open(path, "w") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        frames = b"".join(struct.pack("<h", max(-32767, min(32767, int(s)))) for s in samples)
        handle.writeframes(frames)


def synth_bed(path, seconds):
    """Quiet original pad. Two low fifths, no borrowed recording."""
    rate = 44100
    n = int(seconds * rate)
    tones = (146.83, 220.00, 293.66)  # D3, A3, D4
    out = []
    for i in range(n):
        t = i / rate
        fade = 1.0
        if t < 1.2:
            fade = t / 1.2
        elif t > seconds - 1.4:
            fade = max(0.0, (seconds - t) / 1.4)
        trem = 0.85 + 0.15 * math.sin(2 * math.pi * 0.18 * t)
        sample = 0.0
        for freq in tones:
            sample += math.sin(2 * math.pi * freq * t)
        sample = sample / len(tones) * 0.045 * fade * trem
        out.append(sample * 32767)
    write_wav(path, out, rate)


def synth_click(path):
    """Short original cap click: a damped noise burst, not a sampled recording."""
    rate = 44100
    n = int(0.09 * rate)
    rng = random.Random(27)
    prev = 0.0
    out = []
    for i in range(n):
        t = i / rate
        noise = rng.uniform(-1, 1)
        # Simple high-pass so it reads as a click rather than a thud.
        hp = noise - prev
        prev = noise
        env = math.exp(-t * 55)
        out.append(hp * env * 0.55 * 32767)
    write_wav(path, out, rate)


def speak(text, path):
    subprocess.check_call(
        [
            "flite",
            "-voice",
            "slt",
            "--setf",
            "duration_stretch=1.12",
            "-t",
            text,
            "-o",
            path,
        ]
    )


def render_product(product, work):
    hook = card_hook(product)
    mid = card_product(product)
    end = card_end(product)
    stem = os.path.splitext(product["file"])[0]
    hook_p = os.path.join(work, stem + "-hook.png")
    mid_p = os.path.join(work, stem + "-mid.png")
    end_p = os.path.join(work, stem + "-end.png")
    hook.save(hook_p)
    mid.save(mid_p)
    end.save(end_p)
    voice = os.path.join(work, stem + "-voice.wav")
    speak(product["speech"], voice)
    voice_len = float(
        subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", voice],
            text=True,
        ).strip()
    )
    voice_start = 0.45
    product_span = max(12.0, voice_start + voice_len + 1.3)
    first_offset = HOOK_HOLD - XFADE
    combined = first_offset + product_span
    offset2 = combined - XFADE
    total = offset2 + END_HOLD
    if not 15 <= total <= 25:
        raise SystemExit(f"{product['file']}: duration {total:.2f}s is outside 15-25")
    bed = os.path.join(work, stem + "-bed.wav")
    click = os.path.join(work, stem + "-click.wav")
    synth_bed(bed, total)
    synth_click(click)
    out = os.path.join(OUT_DIR, product["file"])
    filter_v = (
        f"[0:v]scale={W}:{H},fps={FPS},format=yuv420p,setpts=PTS-STARTPTS[v0];"
        f"[1:v]scale={W}:{H},fps={FPS},format=yuv420p,setpts=PTS-STARTPTS[v1];"
        f"[2:v]scale={W}:{H},fps={FPS},format=yuv420p,setpts=PTS-STARTPTS[v2];"
        f"[v0][v1]xfade=transition=fade:duration={XFADE}:offset={first_offset:.3f}[vx];"
        f"[vx][v2]xfade=transition=fade:duration={XFADE}:offset={offset2:.3f}[v]"
    )
    filter_a = (
        f"[3:a]volume=0.22,aformat=channel_layouts=stereo,apad=whole_dur={total:.3f}[bed];"
        f"[4:a]volume=0.9,adelay={int(voice_start*1000)}|{int(voice_start*1000)},aformat=channel_layouts=stereo,apad=whole_dur={total:.3f}[voice];"
        f"[5:a]volume=0.45,adelay=280|280,aformat=channel_layouts=stereo,apad=whole_dur={total:.3f}[click];"
        f"[bed][voice][click]amix=inputs=3:duration=first:normalize=0[a]"
    )
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-t", f"{HOOK_HOLD:.3f}", "-i", hook_p,
        "-loop", "1", "-t", f"{product_span:.3f}", "-i", mid_p,
        "-loop", "1", "-t", f"{END_HOLD:.3f}", "-i", end_p,
        "-i", bed, "-i", voice, "-i", click,
        "-filter_complex", filter_v + ";" + filter_a,
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "high", "-crf", "20",
        "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2",
        "-movflags", "+faststart",
        "-t", f"{total:.3f}",
        out,
    ]
    subprocess.check_call(cmd)
    print(f"wrote {out} ({total:.2f}s, voice {voice_len:.2f}s)")
    return hook_p, mid_p, end_p, out


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="sdd-video-") as work:
        for product in PRODUCTS:
            render_product(product, work)


if __name__ == "__main__":
    main()
