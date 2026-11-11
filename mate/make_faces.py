"""Mate 1 faces: 128x48, 1 bit (1 = lit pixel). Butler style: monocle on the right eye
(viewer's right) and a handlebar mustache. Generates previews and the C++ data file."""

import sys
from PIL import Image, ImageDraw, ImageFont

W, H = 128, 48
LX, RX, EY = 38, 90, 17   # eye centres
EW, EH, ER = 20, 22, 7    # eye size and corner radius


def canvas():
    img = Image.new("1", (W, H), 0)
    return img, ImageDraw.Draw(img)


# ---------- eyes ----------
def eye_open(d, cx, cy=EY, w=EW, h=EH, r=ER, dy=0, dx=0):
    d.rounded_rectangle([cx - w // 2 + dx, cy - h // 2 + dy, cx + w // 2 - 1 + dx, cy + h // 2 - 1 + dy],
                        radius=r, fill=1)


def eye_closed_line(d, cx, cy=EY + 3):
    d.rounded_rectangle([cx - 10, cy - 1, cx + 9, cy + 1], radius=1, fill=1)


def eye_happy(d, cx, cy=EY + 4, w=20, h=16, t=4):
    # upward arc (^)
    d.arc([cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2 + 6], 195, 345, fill=1, width=t)


def eye_sleep(d, cx, cy=EY - 2, w=20, h=12, t=3):
    # downward arc (u), closed and relaxed
    d.arc([cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2], 15, 165, fill=1, width=t)


def eye_laugh(d, cx, side, cy=EY + 1):
    # > < squint
    if side == "L":
        pts = [(cx - 8, cy - 7), (cx + 7, cy), (cx - 8, cy + 7)]
    else:
        pts = [(cx + 7, cy - 7), (cx - 8, cy), (cx + 7, cy + 7)]
    d.line(pts, fill=1, width=4, joint="curve")


def eye_heart(d, cx, cy=EY):
    s = 5
    d.ellipse([cx - 2 * s, cy - s - 3, cx, cy + s - 3], fill=1)
    d.ellipse([cx, cy - s - 3, cx + 2 * s, cy + s - 3], fill=1)
    d.polygon([(cx - 2 * s + 1, cy), (cx + 2 * s - 1, cy), (cx, cy + 2 * s - 1)], fill=1)


def lid_cut(d, pts):
    d.polygon(pts, fill=0)


# ---------- monocle and mustache ----------
def monocle(d, cx=RX, cy=EY, r=14):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=1, width=2)
    # chain: dotted curve from the ring down to the bottom edge
    for x, y in [(101, 28), (103, 31), (105, 34), (107, 37), (109, 40), (110, 43), (111, 46)]:
        d.point([(x, y), (x + 1, y)], fill=1)


def mustache(d, mood="neutral"):
    cx, cy = 64, 36
    # two lobes meeting under the "nose"
    d.ellipse([cx - 17, cy - 3, cx + 1, cy + 4], fill=1)
    d.ellipse([cx - 1, cy - 3, cx + 17, cy + 4], fill=1)
    d.rectangle([cx - 1, cy - 4, cx, cy - 2], fill=0)  # small notch in the middle
    if mood == "up":
        tipL = [(cx - 16, cy + 1), (cx - 21, cy), (cx - 24, cy - 3), (cx - 23, cy - 5)]
        tipR = [(cx + 16, cy + 1), (cx + 21, cy), (cx + 24, cy - 3), (cx + 23, cy - 5)]
    elif mood == "down":
        tipL = [(cx - 16, cy + 2), (cx - 20, cy + 4), (cx - 22, cy + 6), (cx - 22, cy + 8)]
        tipR = [(cx + 16, cy + 2), (cx + 20, cy + 4), (cx + 22, cy + 6), (cx + 22, cy + 8)]
    elif mood == "flat":
        tipL = [(cx - 16, cy + 1), (cx - 22, cy + 1), (cx - 24, cy)]
        tipR = [(cx + 16, cy + 1), (cx + 22, cy + 1), (cx + 24, cy)]
    elif mood == "wink":  # one side up, the other neutral
        tipL = [(cx - 16, cy + 1), (cx - 21, cy + 1), (cx - 23, cy - 2)]
        tipR = [(cx + 16, cy + 1), (cx + 21, cy), (cx + 24, cy - 3), (cx + 23, cy - 5)]
    else:  # neutral: gentle curl
        tipL = [(cx - 16, cy + 1), (cx - 21, cy + 1), (cx - 23, cy - 2), (cx - 22, cy - 4)]
        tipR = [(cx + 16, cy + 1), (cx + 21, cy + 1), (cx + 23, cy - 2), (cx + 22, cy - 4)]
    d.line(tipL, fill=1, width=2, joint="curve")
    d.line(tipR, fill=1, width=2, joint="curve")


def mouth_open(d):
    d.chord([57, 36, 71, 47], 0, 180, fill=1)


def mouth_o(d):
    d.ellipse([60, 40, 67, 47], outline=1, width=2)


def zz(d):
    # small "z z" over the monocle side
    for (x, y, s) in [(110, 4, 5), (118, 0, 4)]:
        d.line([(x, y), (x + s, y), (x, y + s), (x + s, y + s)], fill=1, width=1)


# ---------- faces ----------
def face(name, blink=False):
    img, d = canvas()
    if name == "neutral":
        if blink:
            eye_closed_line(d, LX); eye_closed_line(d, RX)
        else:
            eye_open(d, LX); eye_open(d, RX)
        monocle(d); mustache(d, "neutral")
    elif name == "happy":
        eye_happy(d, LX); eye_happy(d, RX)
        monocle(d); mustache(d, "up")
    elif name == "sad":
        if blink:
            eye_closed_line(d, LX, EY + 5); eye_closed_line(d, RX, EY + 5)
        else:
            eye_open(d, LX, dy=2); eye_open(d, RX, dy=2)
            # lids falling towards the outside
            lid_cut(d, [(LX - 12, EY - 12), (LX + 12, EY - 12), (LX + 12, EY - 9), (LX - 12, EY + 3)])
            lid_cut(d, [(RX - 12, EY - 12), (RX + 12, EY - 12), (RX + 12, EY + 3), (RX - 12, EY - 9)])
        monocle(d); mustache(d, "down")
    elif name == "surprised":
        if blink:
            eye_closed_line(d, LX); eye_closed_line(d, RX)
        else:
            eye_open(d, LX, w=24, h=26, r=11); eye_open(d, RX, w=24, h=26, r=11)
        monocle(d, r=16); mustache(d, "flat"); mouth_o(d)
    elif name == "thinking":
        if blink:
            eye_closed_line(d, LX - 3, EY); eye_closed_line(d, RX - 3, EY)
        else:
            # looking up and to the side, left eye half closed
            eye_open(d, LX, dx=-3, dy=-2)
            lid_cut(d, [(LX - 16, EY - 14), (LX + 10, EY - 14), (LX + 10, EY - 1), (LX - 16, EY - 1)])
            eye_open(d, RX, dx=-3, dy=-2)
        # raised eyebrow over the left eye
        d.line([(LX - 14, EY - 6), (LX - 4, EY - 11), (LX + 6, EY - 9)], fill=1, width=3, joint="curve")
        monocle(d); mustache(d, "wink")
    elif name == "angry":
        if blink:
            eye_closed_line(d, LX, EY + 4); eye_closed_line(d, RX, EY + 4)
        else:
            eye_open(d, LX, dy=2); eye_open(d, RX, dy=2)
            # lids falling towards the centre
            lid_cut(d, [(LX - 12, EY - 12), (LX + 12, EY - 12), (LX + 12, EY + 3), (LX - 12, EY - 7)])
            lid_cut(d, [(RX - 12, EY - 12), (RX + 12, EY - 12), (RX + 12, EY - 7), (RX - 12, EY + 3)])
        monocle(d); mustache(d, "flat")
    elif name == "laughing":
        eye_laugh(d, LX, "L"); eye_laugh(d, RX, "R")
        monocle(d); mustache(d, "up"); mouth_open(d)
    elif name == "loving":
        eye_heart(d, LX); eye_heart(d, RX)
        monocle(d); mustache(d, "up")
    elif name == "sleepy":
        eye_sleep(d, LX, EY + 2); eye_sleep(d, RX, EY + 2)
        monocle(d); mustache(d, "down"); zz(d)
    elif name == "winking":
        if blink:
            eye_closed_line(d, LX)
        else:
            eye_open(d, LX)
        eye_happy(d, RX)
        monocle(d); mustache(d, "wink")
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
