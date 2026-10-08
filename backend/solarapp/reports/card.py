"""Client card: a phone-sized PNG with the roof check result, made to be sent from Messenger."""
from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from ..schemas import AssessmentDoc
from .brand import ASSETS

COMPASS = ["north", "north-northeast", "northeast", "east-northeast", "east", "east-southeast", "southeast", "south-southeast", "south", "south-southwest", "southwest", "west-southwest", "west", "west-northwest", "northwest", "north-northwest"]
INK, MUTED, LINE, GOLD, GOLD_SOFT, GOLD_INK, FIELD, BG = "#111111", "#6b6b66", "#e2e2dc", "#C9A227", "#faf4e1", "#5a4710", "#F5F5F3", "#ffffff"
GOOD, WARN, BAD = "#1f7a3a", "#8f5600", "#b02a1f"


def _font(weight: int, size: int) -> ImageFont.FreeTypeFont:
    path = ASSETS / "fonts" / f"Montserrat-{weight}.ttf"
    try:
        return ImageFont.truetype(str(path), size)
    except OSError:
        return ImageFont.load_default()


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
    words, lines, cur = str(text).split(), [], ""
    for w in words:
        t = f"{cur} {w}".strip()
        if draw.textlength(t, font=font) > max_w and cur:
            lines.append(cur)
            cur = w
        else:
            cur = t
    if cur:
        lines.append(cur)
    return lines


def compass(az: float) -> str:
    return COMPASS[int(round((az % 360) / 22.5)) % 16]


def build_client_card(doc: AssessmentDoc, results: dict, company: dict, next_step: str = "") -> bytes:
    prod = results["production"]
    selected = next(p for p in results["panels"] if p["panel"]["id"] == results["selected_panel_id"])
    panel = selected["panel"]
    k = results.get("k") or {}
    sets = k.get("sets") or []
    kset = sets[k["selected_set_index"]] if sets and k.get("selected_set_index") is not None else None
    shade = results.get("shade") or {}
    audit = results.get("audit") or {}
    bills = (audit.get("audit_vs_bill") or {}).get("bills") or []
    bill_kwh = float(bills[0]["kwh"]) if bills else None

    W, P = 1080, 64
    f_small, f_body, f_body_b, f_head, f_title, f_big = _font(600, 28), _font(400, 30), _font(600, 32), _font(700, 30), _font(700, 76), _font(700, 80)
    img = Image.new("RGB", (W, 3200), BG)
    d = ImageDraw.Draw(img)
    # header band
    d.rectangle([0, 0, W, 300], fill=INK)
    d.rectangle([0, 300, W, 308], fill=GOLD)
    logo_path = ASSETS / "logo-mark.png"
    x0 = P
    if logo_path.exists():
        mark = Image.open(logo_path).convert("RGBA")
        white = Image.new("RGBA", mark.size, (255, 255, 255, 0))
        # white version of the mark: keep alpha, paint white
        alpha = mark.split()[3]
        white.paste((255, 255, 255, 255), mask=alpha)
        white = white.resize((96, 96), Image.LANCZOS)
        img.paste(white, (P, 56), white)
        x0 = P + 120
    d.text((x0, 62), (company.get("company_name") or "PL Development Inc.").upper(), font=f_small, fill=GOLD)
    d.text((x0, 104), "Roof Potential Check", font=f_title, fill="#ffffff")
    who = (doc.customer_name or "") + (f"  ·  {doc.address}" if doc.address else "")
    d.text((P, 212), _wrap(d, who, f_body, W - 2 * P)[0] if who else "", font=f_body, fill="#b8b8b2")
    when = datetime.now().strftime("%B %d, %Y")
    d.text((P, 254), when, font=f_body, fill="#b8b8b2")
    y = 308 + 56

    # big numbers
    col_w = (W - 2 * P - 40) // 3
    monthly = round(prod["avg_monthly_kwh"] / 10) * 10
    for i, (val, lab) in enumerate([(f"{prod['total_panels']}", "panels fit"), (f"{prod['system_kwp']:.2f}", "kWp system size"), (f"≈ {monthly:,.0f}", "kWh in a typical month")]):
        cx = P + i * (col_w + 20)
        d.rounded_rectangle([cx, y, cx + col_w, y + 190], radius=16, fill=FIELD)
        d.text((cx + 24, y + 22), val, font=f_big, fill=INK)
        for j, line in enumerate(_wrap(d, lab, f_small, col_w - 40)):
            d.text((cx + 24, y + 128 + j * 30), line, font=f_small, fill=MUTED)
    y += 190 + 40

    # bill
    if bill_kwh:
        cover = prod["avg_monthly_kwh"] / bill_kwh * 100.0
        text = f"Your bill shows {bill_kwh:,.0f} kWh a month. Your roof can make about {cover:.0f}% of that" + (", more than your house uses." if cover >= 100 else ".")
        lines = _wrap(d, text, f_body_b, W - 2 * P - 48)
        bh = 40 + len(lines) * 44
        d.rounded_rectangle([P, y, W - P, y + bh], radius=16, fill=GOLD_SOFT)
        for j, line in enumerate(lines):
            d.text((P + 24, y + 22 + j * 44), line, font=f_body_b, fill=GOLD_INK)
        y += bh + 40

    def heading(t: str) -> None:
        nonlocal y
        d.text((P, y), t.upper(), font=f_head, fill=GOLD_INK)
        y += 58

    heading("Your roof, face by face")
    for fs, f in zip(prod["faces"], doc.faces):
        t1 = f"{f.name}  ·  faces {compass(f.azimuth_deg)}, {f.tilt_deg:g}° tilt"
        t2 = f"{fs['panel_count']} panels  ·  {fs['panel_count'] * panel['watt_peak'] / 1000:.2f} kWp  ·  about {round(fs['annual_kwh'] / 12 / 10) * 10:,.0f} kWh a month"
        d.text((P, y), t1, font=f_body_b, fill=INK)
        d.text((P, y + 44), t2, font=f_body, fill=MUTED)
        y += 100
        d.rectangle([P, y, W - P, y + 2], fill=LINE)
        y += 22
    y += 20

    heading("Measured on your roof")
    lines = []
    if kset and kset.get("valid"):
        when_t = ""
        try:
            when_t = datetime.fromisoformat(kset["measured_at"]).strftime("%I:%M %p").lstrip("0") if kset.get("measured_at") else ""
        except Exception:  # noqa: BLE001
            when_t = ""
        lines.append(f"Sun on the roof: {kset['avg_irradiance_wm2']:,.0f} W/m² ({(kset.get('sky_condition') or 'clear')} sky{', ' + when_t if when_t else ''})")
        lines.append(f"Test panel: panels here perform at {k['k_raw'] * 100:.0f}% of their label at that moment, {k['k_site'] * 100:.0f}% after allowing for heat and sun angle")
    else:
        lines.append("Sun reading not used; long-term sun records only.")
    for f in doc.faces:
        lines.append(f"{f.name}: tilt {f.tilt_deg:g}°, direction {f.azimuth_deg:g}°, {f.length_m:g} m eave × {f.width_m:g} m slope" + (f", ridge {f.ridge_m:g} m" if f.shape == "hip" and f.ridge_m else "") + (" (triangle)" if f.shape == "tri" else ""))
    for t in lines:
        for line in _wrap(d, t, f_body, W - 2 * P):
            d.text((P, y), line, font=f_body, fill=INK)
            y += 42
        y += 6
    y += 24

    notes = []
    for f in doc.faces:
        sb = shade.get(f.id) or {}
        for o in sb.get("obstacles", []):
            colour = GOOD if o["cls"] == "clear" else WARN if o["cls"] == "small" else BAD
            notes.append((colour, f"{o['label'] or 'Obstruction'} to the {compass(o['direction_deg'])}: " + ("no effect" if o["cls"] == "clear" else "small early or late loss in some months" if o["cls"] == "small" else "shades part of the roof in the main hours")))
        for w in sb.get("walls", []):
            if w["whole_face"]:
                notes.append((BAD, f"Wall to the {compass(w['side_deg'])} beside {f.name}: shades the whole face"))
            elif w["strip_m"] and w["strip_m"] > 0:
                notes.append((BAD, f"Wall to the {compass(w['side_deg'])} beside {f.name}: no panels within {w['strip_m']:.1f} m of it"))
            else:
                notes.append((WARN, f"Wall to the {compass(w['side_deg'])} beside {f.name}: small early or late loss only"))
        if sb.get("shade_loss_pct", 0) >= 1:
            notes.append((WARN, f"{f.name}: shade takes about {sb['shade_loss_pct']:.0f}% of the direct sun over the year"))
    if notes:
        heading("Shade")
        for colour, text in notes:
            d.ellipse([P + 2, y + 12, P + 22, y + 32], fill=colour)
            for line in _wrap(d, text, f_body, W - 2 * P - 40):
                d.text((P + 40, y), line, font=f_body, fill=INK)
                y += 42
            y += 6
        y += 24

    # next step band
    nt = next_step or "Next step: a free energy audit."
    nd = "We'll go through your bill and how you use power, then work out how much of your bill solar can cut and what the system costs. Please have your latest bill ready."
    nd_lines = _wrap(d, nd, f_body, W - 2 * P - 48)
    nh = 40 + 48 + len(nd_lines) * 40 + 20
    d.rounded_rectangle([P, y, W - P, y + nh], radius=16, fill=INK)
    d.text((P + 24, y + 28), nt, font=_font(700, 38), fill=GOLD)
    for j, line in enumerate(nd_lines):
        d.text((P + 24, y + 92 + j * 40), line, font=f_body, fill="#e6e6e1")
    y += nh + 36
    foot = "Estimate from your measured roof and long-term sun records for this location (PVGIS). Output is higher in dry months and lower in rainy ones. This is not a quotation."
    for line in _wrap(d, foot, _font(400, 26), W - 2 * P):
        d.text((P, y), line, font=_font(400, 26), fill=MUTED)
        y += 36
    y += 40
    out = img.crop((0, 0, W, int(y)))
    buf = io.BytesIO()
    out.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
