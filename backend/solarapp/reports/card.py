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


def _handle(url: str) -> str:
    u = (url or "").strip()
    for pre in ("https://", "http://", "www."):
        if u.lower().startswith(pre):
            u = u[len(pre):]
    return u.rstrip("/")


def _qr(url: str, size: int) -> Image.Image | None:
    try:
        import qrcode
    except ImportError:
        return None
    q = qrcode.QRCode(box_size=8, border=1)
    q.add_data(url)
    q.make(fit=True)
    return q.make_image(fill_color=INK, back_color="white").convert("RGB").resize((size, size), Image.NEAREST)


def build_client_card(doc: AssessmentDoc, results: dict, company: dict, next_step: str = "", public_url: str = "") -> bytes:
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
    img = Image.new("RGB", (W, 3600), BG)
    d = ImageDraw.Draw(img)
    # header band: height follows the customer line
    logo_path = ASSETS / "logo-mark.png"
    x0 = P
    white = None
    if logo_path.exists():
        mark = Image.open(logo_path).convert("RGBA")
        white = Image.new("RGBA", mark.size, (255, 255, 255, 0))
        alpha = mark.split()[3]
        white.paste((255, 255, 255, 255), mask=alpha)
        white = white.resize((96, 96), Image.LANCZOS)
        x0 = P + 120
    who = (doc.customer_name or "") + (f"  ·  {doc.address}" if doc.address else "")
    who_lines = _wrap(d, who, f_body, W - 2 * P)[:2] if who else []
    when = datetime.now().strftime("%-d %b %Y")
    band_h = 230 + 40 * len(who_lines) + 44
    d.rectangle([0, 0, W, band_h], fill=INK)
    d.rectangle([0, band_h, W, band_h + 8], fill=GOLD)
    if logo_path.exists():
        img.paste(white, (P, 56), white)
    d.text((x0, 62), (company.get("company_name") or "PL Development Inc.").upper(), font=f_small, fill=GOLD)
    d.text((x0, 104), "Your Roof Check", font=f_title, fill="#ffffff")
    for j, line in enumerate(who_lines):
        d.text((P, 212 + j * 40), line, font=f_body, fill="#b8b8b2")
    d.text((P, 212 + 40 * len(who_lines) + 4), when, font=f_body, fill="#b8b8b2")
    y = band_h + 8 + 56

    # big numbers
    col_w = (W - 2 * P - 40) // 3
    monthly = round(prod["avg_monthly_kwh"] / 10) * 10
    for i, (val, lab) in enumerate([(f"{prod['total_panels']}", "panels fit"), (f"{prod['system_kwp']:.2f}", "kWp system size"), (f"~{monthly:,.0f}", "kWh a month, typical")]):
        cx = P + i * (col_w + 20)
        d.rounded_rectangle([cx, y, cx + col_w, y + 190], radius=16, fill=FIELD)
        fv = f_big
        while d.textlength(val, font=fv) > col_w - 48 and fv.size > 40:
            fv = _font(700, fv.size - 6)
        d.text((cx + 24, y + 22 + (f_big.size - fv.size) // 2), val, font=fv, fill=INK)
        for j, line in enumerate(_wrap(d, lab, f_small, col_w - 40)):
            d.text((cx + 24, y + 128 + j * 30), line, font=f_small, fill=MUTED)
    y += 190 + 40

    # bill: what the full roof makes, in the customer's unit
    if bill_kwh:
        ratio = prod["avg_monthly_kwh"] / bill_kwh
        if ratio >= 1.05:
            text = f"Your bill shows {bill_kwh:,.0f} kWh a month. Your roof can make about {monthly:,.0f} kWh, around {ratio:.1f} times what your house uses. The system we propose will be sized to your bill, so it needs only part of the roof."
        else:
            text = f"Your bill shows {bill_kwh:,.0f} kWh a month. Your roof can make about {monthly:,.0f} kWh, about {ratio * 100:.0f}% of what your house uses."
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

    heading("Each part of your roof")
    for fs, f in zip(prod["faces"], doc.faces):
        t1 = f"{f.name}  ·  faces {compass(f.azimuth_deg)}, {f.tilt_deg:g}° pitch"
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
        lines.append(f"Sunlight on the roof: {kset['avg_irradiance_wm2']:,.0f} W/m² ({(kset.get('sky_condition') or 'clear')} sky{', ' + when_t if when_t else ''})")
        good = " That is a good roof." if k.get("k_site", 0) >= 0.9 else ""
        lines.append(f"Test panel: {k['k_raw'] * 100:.0f}% of rated power at that moment; {k['k_site'] * 100:.0f}% once heat and sun angle are allowed for.{good}")
    else:
        lines.append("No sun reading on the day; we used long-term sun records only.")
    for f in doc.faces:
        lines.append(f"{f.name}: pitch {f.tilt_deg:g}°, faces {f.azimuth_deg:g}° ({compass(f.azimuth_deg)}), {f.length_m:g} m wide × {f.width_m:g} m up the slope" + (f", {f.ridge_m:g} m at the ridge" if f.shape == "hip" and f.ridge_m else "") + (" (triangle)" if f.shape == "tri" else ""))
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
            notes.append((colour, f"{o['label'] or 'Obstruction'} to the {compass(o['direction_deg'])}: " + ("no effect" if o["cls"] == "clear" else "small early or late loss in some months" if o["cls"] == "small" else "shades part of the roof in the middle of the day")))
        for w in sb.get("walls", []):
            if w["whole_face"]:
                notes.append((BAD, f"Wall on the {compass(w['side_deg'])} side of {f.name}: shades that whole part of the roof at midday"))
            elif w["strip_m"] and w["strip_m"] > 0:
                notes.append((BAD, f"Wall on the {compass(w['side_deg'])} side of {f.name}: we keep panels {w['strip_m']:.1f} m away from it"))
            else:
                notes.append((WARN, f"Wall on the {compass(w['side_deg'])} side of {f.name}: small early or late loss only"))
        if sb.get("shade_loss_pct", 0) >= 1:
            pct = sb["shade_loss_pct"]
            notes.append((WARN if pct < 10 else BAD, f"{f.name}: shade costs about {pct:.0f}% of the year's sun." + (" Small." if pct < 5 else "")))
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
    nt = (next_step or "").strip() or "Next step: your free energy audit"
    nd = "We'll go through your latest bill and the appliances you use, then work out how much solar can cut from your bill and what the system costs. Please have your latest bill ready."
    nt_lines = _wrap(d, nt, _font(700, 38), W - 2 * P - 48)[:2]
    nd_lines = _wrap(d, nd, f_body, W - 2 * P - 48)
    nh = 28 + len(nt_lines) * 48 + 16 + len(nd_lines) * 40 + 24
    d.rounded_rectangle([P, y, W - P, y + nh], radius=16, fill=INK)
    for j, line in enumerate(nt_lines):
        d.text((P + 24, y + 28 + j * 48), line, font=_font(700, 38), fill=GOLD)
    for j, line in enumerate(nd_lines):
        d.text((P + 24, y + 28 + len(nt_lines) * 48 + 16 + j * 40), line, font=f_body, fill="#e6e6e1")
    y += nh + 36

    # contact and the way back in for whoever this is forwarded to
    contact = [company.get("company_name") or "PL Development Inc."]
    if company.get("owner_name"):
        contact.append(company["owner_name"])
    if company.get("phone"):
        contact.append(company["phone"])
    if company.get("messenger"):
        contact.append(_handle(company["messenger"]))
    if company.get("facebook"):
        contact.append(_handle(company["facebook"]))
    qr = _qr(f"{public_url.rstrip('/')}?utm_source=card&utm_medium=messenger", 200) if public_url else None  # public_url is the estimate's own address
    text_w = W - 2 * P - (240 if qr else 0)
    d.rectangle([P, y, W - P, y + 2], fill=LINE)
    y0 = y + 24
    for line in _wrap(d, "  ·  ".join(contact), f_body_b, text_w):
        d.text((P, y0), line, font=f_body_b, fill=INK)
        y0 += 42
    if qr:
        for line in _wrap(d, "Forwarded this? Scan for your own free estimate.", _font(400, 26), text_w):
            d.text((P, y0), line, font=_font(400, 26), fill=MUTED)
            y0 += 34
        img.paste(qr, (W - P - 200, y + 24))
        y0 = max(y0, y + 24 + 200)
    y = y0 + 24
    foot = "This estimate comes from the measurements we took on your roof and long-term sun records for your area (PVGIS). Output is higher in the dry months and lower in the rainy ones. This is not a quotation."
    for line in _wrap(d, foot, _font(400, 26), W - 2 * P):
        d.text((P, y), line, font=_font(400, 26), fill=MUTED)
        y += 36
    y += 40
    out = img.crop((0, 0, W, int(y)))
    buf = io.BytesIO()
    out.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
