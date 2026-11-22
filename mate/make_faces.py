"""Mate 1 faces: 128x48, 1 bit (1 = lit pixel). Friendly style (option B, 22/11/2026): round
eyes with a small highlight and a small mouth. Generates previews and the C++ data file."""

import sys
from PIL import Image, ImageDraw, ImageFont

W, H = 128, 48
LX, RX, EY = 42, 86, 19   # eye centres
R = 12                    # eye radius
MX, MY = 64, 36           # mouth centre


def canvas():
    img = Image.new("1", (W, H), 0)
    return img, ImageDraw.Draw(img)


# ---------- eyes ----------
def eye_round(d, cx, cy=EY, r=R, look=(0, 0)):
    """Solid round eye with a dark highlight; look moves the highlight (where it is looking)."""
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=1)
    hx, hy = cx + r // 2 - 1 + look[0], cy - r // 2 + 1 + look[1]
    d.ellipse([hx - 3, hy - 3, hx + 3, hy + 3], fill=0)


def eye_closed(d, cx, cy=EY):
    d.rounded_rectangle([cx - 12, cy - 1, cx + 11, cy + 1], radius=1, fill=1)


def eye_happy(d, cx, cy=EY):
    # upward arc (^)
    d.arc([cx - 12, cy - 8, cx + 12, cy + 14], 200, 340, fill=1, width=5)


def eye_sleep(d, cx, cy=EY):
    # downward arc (u), closed and relaxed
    d.arc([cx - 11, cy - 8, cx + 11, cy + 6], 20, 160, fill=1, width=3)


def eye_laugh(d, cx, side, cy=EY):
    # > < squint
    if side == "L":
        pts = [(cx - 9, cy - 8), (cx + 8, cy), (cx - 9, cy + 8)]
    else:
        pts = [(cx + 8, cy - 8), (cx - 9, cy), (cx + 8, cy + 8)]
    d.line(pts, fill=1, width=4, joint="curve")


def eye_heart(d, cx, cy=EY):
    s = 6
    d.ellipse([cx - 2 * s, cy - s - 4, cx, cy + s - 4], fill=1)
    d.ellipse([cx, cy - s - 4, cx + 2 * s, cy + s - 4], fill=1)
    d.polygon([(cx - 2 * s + 1, cy - 1), (cx + 2 * s - 1, cy - 1), (cx, cy + 2 * s - 2)], fill=1)


def lid_cut(d, pts):
    d.polygon(pts, fill=0)


# ---------- mouths ----------
def mouth_smile(d):
    d.arc([MX - 9, MY - 6, MX + 9, MY + 6], 25, 155, fill=1, width=2)


def mouth_open(d, big=False):
    w = 12 if big else 10
    d.chord([MX - w, MY - 6, MX + w, MY + 10], 0, 180, fill=1)


def mouth_frown(d):
    d.arc([MX - 8, MY + 1, MX + 8, MY + 11], 205, 335, fill=1, width=2)


def mouth_flat(d, dx=0):
    d.rectangle([MX - 5 + dx, MY + 2, MX + 5 + dx, MY + 3], fill=1)


def mouth_o(d):
    d.ellipse([MX - 4, MY - 1, MX + 4, MY + 8], outline=1, width=2)


def zz(d):
    for (x, y, s) in [(108, 6, 5), (116, 1, 4)]:
        d.line([(x, y), (x + s, y), (x, y + s), (x + s, y + s)], fill=1, width=1)


# ---------- faces ----------
def face(name, blink=False):
    img, d = canvas()
    if name == "neutral":
        if blink:
            eye_closed(d, LX); eye_closed(d, RX)
        else:
            eye_round(d, LX); eye_round(d, RX)
        mouth_smile(d)
    elif name == "happy":
        eye_happy(d, LX); eye_happy(d, RX)
        mouth_open(d)
    elif name == "sad":
        if blink:
            eye_closed(d, LX, EY + 4); eye_closed(d, RX, EY + 4)
        else:
            eye_round(d, LX, EY + 2, look=(-6, 8)); eye_round(d, RX, EY + 2, look=(-6, 8))
            # lids falling towards the outside
            lid_cut(d, [(LX - 14, EY - 12), (LX + 14, EY - 12), (LX + 14, EY - 8), (LX - 14, EY + 1)])
            lid_cut(d, [(RX - 14, EY - 12), (RX + 14, EY - 12), (RX + 14, EY + 1), (RX - 14, EY - 8)])
        mouth_frown(d)
    elif name == "surprised":
        if blink:
            eye_closed(d, LX); eye_closed(d, RX)
        else:
            eye_round(d, LX, r=14); eye_round(d, RX, r=14)
        mouth_o(d)
    elif name == "thinking":
        if blink:
            eye_closed(d, LX); eye_closed(d, RX)
        else:
            # looking up and to the side
            eye_round(d, LX, look=(-8, -2)); eye_round(d, RX, look=(-8, -2))
        mouth_flat(d, dx=5)
    elif name == "angry":
        if blink:
            eye_closed(d, LX, EY + 3); eye_closed(d, RX, EY + 3)
        else:
            eye_round(d, LX, EY + 2, look=(-6, 8)); eye_round(d, RX, EY + 2, look=(-6, 8))
            # lids falling towards the centre
            lid_cut(d, [(LX - 14, EY - 12), (LX + 14, EY - 12), (LX + 14, EY + 1), (LX - 14, EY - 7)])
            lid_cut(d, [(RX - 14, EY - 12), (RX + 14, EY - 12), (RX + 14, EY - 7), (RX - 14, EY + 1)])
        mouth_flat(d)
    elif name == "laughing":
        eye_laugh(d, LX, "L"); eye_laugh(d, RX, "R")
        mouth_open(d, big=True)
    elif name == "loving":
        eye_heart(d, LX); eye_heart(d, RX)
        mouth_smile(d)
    elif name == "sleepy":
        eye_sleep(d, LX, EY + 2); eye_sleep(d, RX, EY + 2)
        mouth_flat(d)
        zz(d)
    elif name == "winking":
        if blink:
            eye_closed(d, LX)
        else:
            eye_round(d, LX)
        eye_happy(d, RX)
        mouth_smile(d)
    else:
        raise ValueError(name)
    return img


FACES = ["neutral", "happy", "sad", "surprised", "thinking",
         "angry", "laughing", "loving", "sleepy", "winking"]
BLINKS = {"neutral", "sad", "surprised", "thinking", "angry", "winking"}
LABELS = {"neutral": "Neutral", "happy": "Feliz", "sad": "Triste", "surprised": "Sorprendido",
          "thinking": "Pensando", "angry": "Enojado", "laughing": "Risa", "loving": "Enamorado",
          "sleepy": "Dormido", "winking": "Guiño"}


def oled_frame(face_img, scale=3):
    """Full 128x64 screen: status bar with 'Mate 1' + face, OLED colours, scaled."""
    screen = Image.new("1", (128, 64), 0)
    sd = ImageDraw.Draw(screen)
    try:
        f = ImageFont.truetype("DejaVuSans.ttf", 11)
    except OSError:
        f = ImageFont.load_default()
    tw = sd.textlength("Mate 1", font=f)
    sd.text(((128 - tw) / 2, 1), "Mate 1", fill=1, font=f)
    screen.paste(face_img, (0, 16))
    rgb = Image.new("RGB", (128, 64), (8, 10, 14))
    lit = Image.new("RGB", (128, 64), (150, 220, 255))
    rgb.paste(lit, mask=screen.convert("L"))
    return rgb.resize((128 * scale, 64 * scale), Image.NEAREST)


def preview(path, cols=2, scale=3):
    try:
        lf = ImageFont.truetype("DejaVuSans-Bold.ttf", 16)
    except OSError:
        lf = ImageFont.load_default()
    cell_w, cell_h = 128 * scale + 24, 64 * scale + 34
    rows = (len(FACES) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell_w + 12, rows * cell_h + 12), (235, 235, 235))
    sd = ImageDraw.Draw(sheet)
    for i, name in enumerate(FACES):
        x = 12 + (i % cols) * cell_w
        y = 12 + (i // cols) * cell_h
        sd.text((x, y), LABELS[name], fill=(20, 20, 20), font=lf)
        sheet.paste(oled_frame(face(name), scale), (x, y + 24))
    sheet.save(path)


def blink_sheet(path, scale=3):
    items = [n for n in FACES if n in BLINKS]
    cell_w, cell_h = 128 * scale + 24, 64 * scale + 12
    sheet = Image.new("RGB", (2 * cell_w + 12, len(items) * cell_h + 12), (235, 235, 235))
    for i, n in enumerate(items):
        sheet.paste(oled_frame(face(n), scale), (12, 12 + i * cell_h))
        sheet.paste(oled_frame(face(n, blink=True), scale), (12 + cell_w, 12 + i * cell_h))
    sheet.save(path)


def pack(img):
    """Row-major, MSB first, 1 = lit."""
    px = img.load()
    out = bytearray()
    for y in range(H):
        for xb in range(0, W, 8):
            b = 0
            for i in range(8):
                if px[xb + i, y]:
                    b |= 0x80 >> i
            out.append(b)
    return bytes(out)


def c_array(data, indent="        "):
    lines = []
    for i in range(0, len(data), 16):
        lines.append(indent + ", ".join(f"0x{b:02x}" for b in data[i:i + 16]) + ",")
    return "\n".join(lines)


def export_header(path):
    blink_names = [n for n in FACES if n in BLINKS]
    enum = ",\n".join(f"    k{n.capitalize()}" for n in FACES)
    opens = ",\n".join("    {\n" + c_array(pack(face(n))) + "\n    }" for n in FACES)
    blinks = ",\n".join("    {\n" + c_array(pack(face(n, blink=True))) + "\n    }" for n in blink_names)
    idx = ", ".join(str(blink_names.index(n)) if n in BLINKS else "-1" for n in FACES)
    text = f"""// Generated by mate/make_faces.py. Do not edit by hand: change the script and regenerate.
// Mate 1 faces: {W}x{H}, 1 bit per pixel, row-major, MSB first, 1 = lit pixel.
#pragma once

#include <stdint.h>

namespace mate_faces {{

constexpr int kWidth = {W};
constexpr int kHeight = {H};
constexpr int kBytes = kWidth / 8 * kHeight;

enum Face {{
{enum},
    kCount
}};

static const uint8_t kOpen[kCount][kBytes] = {{
{opens}
}};

constexpr int kBlinkCount = {len(blink_names)};

static const uint8_t kBlink[kBlinkCount][kBytes] = {{
{blinks}
}};

// Index into kBlink for each face, or -1 when the face does not blink.
static const int8_t kBlinkIndex[kCount] = {{{idx}}};

}}  // namespace mate_faces
"""
    with open(path, "w") as f:
        f.write(text)


if __name__ == "__main__":
    # usage: make_faces.py <preview_dir> [header_path]
    out = sys.argv[1]
    preview(f"{out}/mate1-caras.png")
    blink_sheet(f"{out}/mate1-parpadeo.png")
    if len(sys.argv) > 2:
        export_header(sys.argv[2])
    print("ok")
