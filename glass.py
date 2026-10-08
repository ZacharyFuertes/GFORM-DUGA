"""Glassmorphism primitives for GFORM DUGA.

Gengar-inspired palette: deep black-purple base, rich violet mids, neon purple
accents, with very subtle cyan/magenta ghostly highlights. No pure black, no
green.

Tkinter cannot do a real backdrop-filter, so the frosted panels are assembled in
PIL: the region behind a panel is cropped from the animated-free base backdrop,
Gaussian-blurred, blended toward rgba(25, 10, 40, 0.6), masked to a rounded
rect, then given a luminous lavender stroke and a soft drop shadow. The result
is a single RGBA image the panel canvas draws, so the corners really are
rounded and the ring really is blurred backdrop.
"""

import math

import tkinter as tk
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps, ImageTk

# ── palette ────────────────────────────────────────────────────────────────────
BG_BASE = "#0B0614"
GRADIENT = ((0.00, "#0B0614"), (0.40, "#150826"), (0.72, "#25103E"), (1.00, "#3A1160"))

PURPLE_DEEP = "#6B2D8B"
PURPLE_RICH = "#8B3A9E"
NEON = "#B84DFF"
NEON_SOFT = "#C77DFF"
LAVENDER = "#E6DAFF"
MUTED = "#9C8FC4"
BORDER = "#8B5CF6"
GLOW = "#A855F7"
CYAN = "#8FE9FF"
MAGENTA = "#FF7AB6"

# Content surfaces are deliberately flat constants: Tk widgets cannot have a
# transparent background, so a matching solid keeps the frosted ring (which
# shows real blurred backdrop) from showing a seam against the content.
SURFACE = "#190A28"
SURFACE_ALT = "#1F0D33"
INPUT_BG = "#241140"
INPUT_FG = "#D9CCFF"
BORDER_SOFT = "#3A2258"

GLASS_TINT = (25, 10, 40)
GLASS_ALPHA = 153          # rgba(25, 10, 40, 0.6)
OUTER = 10                 # shadow margin, shows sharp backdrop
RADIUS = 20                # corner radius
BODY_INSET = 24            # canvas edge -> content frame (14px frosted ring)

FONT = "Segoe UI"
MONO = "Consolas"


# ── colour helpers ─────────────────────────────────────────────────────────────
def hex_to_rgb(value):
    if isinstance(value, str):
        value = value.lstrip("#")
        return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))
    return tuple(value)


def rgb_to_hex(value):
    return "#%02X%02X%02X" % tuple(int(max(0, min(255, c))) for c in value)


def mix(a, b, t):
    """Blend colour a toward colour b by t (0..1)."""
    ca, cb = hex_to_rgb(a), hex_to_rgb(b)
    return rgb_to_hex(ca[i] + (cb[i] - ca[i]) * t for i in range(3))


def darken(value, t):
    return mix(value, "#000000", t)


def lighten(value, t):
    return mix(value, "#FFFFFF", t)


# ── backdrop ───────────────────────────────────────────────────────────────────
def _gradient_column(height):
    col = Image.new("RGB", (1, height))
    px = col.load()
    last = len(GRADIENT) - 1
    for y in range(height):
        t = y / max(1, height - 1)
        seg = 0
        while seg < last and t > GRADIENT[seg + 1][0]:
            seg += 1
        t0, c0 = GRADIENT[seg]
        t1, c1 = GRADIENT[min(seg + 1, last)]
        f = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
        f = min(max(f, 0.0), 1.0)
        a, b = hex_to_rgb(c0), hex_to_rgb(c1)
        px[0, y] = tuple(int(a[i] + (b[i] - a[i]) * f) for i in range(3))
    return col


def _haze(img, cx, cy, radius, colour, strength):
    if radius <= 1:
        return img
    glow = ImageOps.invert(Image.radial_gradient("L"))
    glow = glow.resize((radius * 2, radius * 2), Image.BILINEAR)
    glow = glow.point(lambda v: int(v * strength))
    mask = Image.new("L", img.size, 0)
    mask.paste(glow, (int(cx - radius), int(cy - radius)))
    return Image.composite(Image.new("RGB", img.size, colour), img, mask)


def _vignette(img):
    w, h = img.size
    vig = ImageOps.invert(Image.radial_gradient("L")).resize((w, h), Image.BILINEAR)
    vig = vig.point(lambda v: int(160 + v * 0.375))
    return Image.composite(img, Image.new("RGB", (w, h), "#050209"), vig)


def build_background(width, height):
    """Deep black-purple base -> dark purple -> rich violet, plus purple haze
    and very subtle cyan/magenta ghostly accents."""
    img = _gradient_column(height).resize((width, height), Image.BILINEAR)

    w, h = float(width), float(height)
    for cx, cy, r, colour, strength in (
        (w * 0.16, h * 0.28, int(h * 0.44), PURPLE_DEEP, 0.46),
        (w * 0.86, h * 0.20, int(h * 0.40), PURPLE_RICH, 0.36),
        (w * 0.64, h * 0.92, int(h * 0.46), "#4C128F", 0.34),
        (w * 0.06, h * 0.86, int(h * 0.34), "#5A1E9E", 0.30),
        (w * 0.44, h * 0.06, int(h * 0.30), MAGENTA, 0.10),
        (w * 0.94, h * 0.66, int(h * 0.26), CYAN, 0.09),
    ):
        img = _haze(img, cx, cy, int(r), colour, strength)
    return _vignette(img)


# ── shape helpers ──────────────────────────────────────────────────────────────
def rounded_mask(width, height, radius):
    mask = Image.new("L", (width, height), 0)
    if width > 0 and height > 0:
        ImageDraw.Draw(mask).rounded_rectangle(
            [0, 0, width - 1, height - 1], radius, fill=255)
    return mask


def rounded_points(x0, y0, x1, y1, radius, steps=7):
    """Canvas polygon points for a rounded rectangle (used for pills/bars)."""
    r = min(radius, (x1 - x0) / 2.0, (y1 - y0) / 2.0)
    pts = []

    def arc(cx, cy, a0, a1):
        for i in range(steps + 1):
            a = a0 + (a1 - a0) * i / steps
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))

    arc(x1 - r, y0 + r, -math.pi / 2, 0)
    arc(x1 - r, y1 - r, 0, math.pi / 2)
    arc(x0 + r, y1 - r, math.pi / 2, math.pi)
    arc(x0 + r, y0 + r, math.pi, 3 * math.pi / 2)
    return pts


def frosted(crop, radius=RADIUS, blur=28, tint=GLASS_TINT, alpha=GLASS_ALPHA):
    """Blurred backdrop blended toward rgba(tint, alpha), rounded, with a soft
    inner top highlight and a luminous lavender hairline border."""
    soft = crop.filter(ImageFilter.GaussianBlur(blur))
    tinted = Image.blend(soft, Image.new("RGB", soft.size, rgb_to_hex(tint)),
                         alpha / 255.0)
    rgba = tinted.convert("RGBA")
    mask = rounded_mask(rgba.width, rgba.height, radius)

    # inner highlight, strongest at the top edge
    highlight = Image.new("L", rgba.size, 0)
    hd = ImageDraw.Draw(highlight)
    band = max(1, int(rgba.height * 0.45))
    for y in range(band):
        hd.line([(0, y), (rgba.width, y)], fill=int(30 * (1 - y / band)))
    white = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
    white.putalpha(ImageChops.multiply(highlight, mask))
    rgba = Image.alpha_composite(rgba, white)
    rgba.putalpha(mask)

    ImageDraw.Draw(rgba).rounded_rectangle(
        [0, 0, rgba.width - 1, rgba.height - 1], radius,
        outline=(196, 158, 255, 210), width=1)
    return rgba


# ── widgets ────────────────────────────────────────────────────────────────────
class Theme:
    """Owns the baked backdrop image and re-renders every frosted panel when
    the window size changes."""

    def __init__(self, root):
        self.root = root
        self.backdrop = None
        self.ready = False
        self.panels = []
        self._after = None
        root.bind("<Configure>", self._on_resize, add="+")

    def _on_resize(self, event):
        if event.widget is not self.root or event.width < 200 or event.height < 200:
            return
        if (self.backdrop is not None
                and abs(self.backdrop.width - event.width) < 3
                and abs(self.backdrop.height - event.height) < 3):
            return
        if self._after:
            try:
                self.root.after_cancel(self._after)
            except tk.TclError:
                pass
        w, h = event.width, event.height
        self._after = self.root.after(160, lambda: self.build(w, h))

    def build(self, width, height):
        self.backdrop = build_background(width, height)
        self.ready = True
        self.refresh()

    def register(self, panel):
        self.panels.append(panel)
        if self.ready:
            panel.render()

    def refresh(self):
        for panel in list(self.panels):
            try:
                panel.render()
            except tk.TclError:
                pass
        if getattr(self, "on_refresh", None):
            try:
                self.on_refresh()
            except tk.TclError:
                pass


class GlassPanel(tk.Canvas):

    """Frosted card: blurred backdrop tile + drop shadow + luminous border,
    with a content frame floating on a 14px glass ring."""

    def __init__(self, parent, theme, radius=RADIUS, outer=OUTER,
                 body_inset=BODY_INSET, **kw):
        kw.setdefault("highlightthickness", 0)
        kw.setdefault("bd", 0)
        kw.setdefault("bg", BG_BASE)
        super().__init__(parent, **kw)
        self.theme = theme
        self.radius = radius
        self.outer = outer
        self.body_inset = body_inset
        self.body = tk.Frame(self, bg=SURFACE, bd=0, highlightthickness=0)
        self._body = self.create_window(0, 0, window=self.body, anchor="nw")
        theme.register(self)
        self.bind("<Configure>", lambda e: self.render())

    def _origin(self):
        root = self.theme.root
        return (self.winfo_rootx() - root.winfo_rootx(),
                self.winfo_rooty() - root.winfo_rooty())

    def render(self):
        w, h = self.winfo_width(), self.winfo_height()
        if w < 8 or h < 8 or not self.theme.ready:
            return
        ox, oy = self._origin()
        backdrop = self.theme.backdrop
        ox = max(0, min(ox, max(0, backdrop.width - 1)))
        oy = max(0, min(oy, max(0, backdrop.height - 1)))
        w = min(w, backdrop.width - ox)
        h = min(h, backdrop.height - oy)
        if w < 8 or h < 8:
            return

        crop = backdrop.crop((ox, oy, ox + w, oy + h))
        tile = crop.convert("RGBA")

        shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        s = max(1, self.outer - 2)
        ImageDraw.Draw(shadow).rounded_rectangle(
            [s, s + 3, w - s - 1, h - s + 1], self.radius, fill=(4, 1, 9, 175))
        tile = Image.alpha_composite(tile, shadow.filter(ImageFilter.GaussianBlur(11)))

        gw, gh = w - 2 * self.outer, h - 2 * self.outer
        if gw > 2 and gh > 2:
            panel = frosted(crop.crop((self.outer, self.outer,
                                       self.outer + gw, self.outer + gh)),
                            radius=self.radius)
            tile.alpha_composite(panel, (self.outer, self.outer))

        self._photo = ImageTk.PhotoImage(tile)
        self.delete("chrome")
        self.create_image(0, 0, image=self._photo, anchor="nw", tags="chrome")

        self.coords(self._body, self.body_inset, self.body_inset)
        self.itemconfig(self._body,
                        width=max(1, w - 2 * self.body_inset),
                        height=max(1, h - 2 * self.body_inset))


class GlassButton(tk.Canvas):
    """Rounded glass pill with a soft outer glow and hover feedback."""

    VARIANTS = {
        "primary": (NEON, "#FFFFFF", 16),
        "ghost":   (SURFACE_ALT, INPUT_FG, 12),
        "danger":  (mix(SURFACE, MAGENTA, 0.35), MAGENTA, 10),
    }

    def __init__(self, parent, text="", command=None, variant="ghost",
                 font=(FONT, 11, "bold"), height=46, **kw):
        self._text = text
        self._command = command
        self._variant = variant
        self._state = kw.pop("state", "normal")
        kw.setdefault("highlightthickness", 0)
        kw.setdefault("bd", 0)
        kw.setdefault("cursor", "hand2")
        super().__init__(parent, height=height, **kw)
        self._font = font
        self._hover = False
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
        self._draw()

    # tkinter option plumbing so existing .config(state=...) calls keep working
    def configure(self, cnf=None, **kw):
        merged = dict(cnf or {})
        merged.update(kw)
        redraw = False
        for key, attr in (("state", "_state"), ("text", "_text"),
                          ("command", "_command"), ("variant", "_variant")):
            if key in merged:
                setattr(self, attr, merged.pop(key))
                redraw = True
        if merged:
            super().configure(**merged)
        if redraw or not self.winfo_exists():
            self._draw()
        return self

    config = configure

    def cget(self, key):
        if key in ("state", "text", "command", "variant"):
            return getattr(self, "_" + key)
        return super().cget(key)

    def _on_enter(self, _event=None):
        if self._state == "normal":
            self._hover = True
            self._draw()

    def _on_leave(self, _event=None):
        self._hover = False
        self._draw()

    def _on_click(self, event=None):
        if self._state != "normal" or not self._command:
            return "break"
        self._command()
        return "break"

    def _draw(self):
        if not self.winfo_exists():
            return
        w, h = self.winfo_width(), self.winfo_height()
        if w < 4 or h < 4:
            return
        self.delete("all")
        fill, label, glow = self.VARIANTS.get(self._variant, self.VARIANTS["ghost"])

        if self._state == "disabled":
            fill = darken(fill, 0.45)
            label = darken(label, 0.55)
        elif self._hover:
            fill = lighten(fill, 0.16)
            label = lighten(label, 0.18)

        # two-step glow behind the pill
        for step, colour in enumerate((mix(fill, NEON, 0.35), mix(fill, NEON, 0.18)),
                                      start=1):
            pad = 3 * step
            self.create_polygon(
                rounded_points(pad, pad, w - pad, h - pad, (h - 2 * pad) / 2),
                fill=colour, outline="", smooth=False)

        self.create_polygon(
            rounded_points(4, 4, w - 4, h - 4, (h - 8) / 2),
            fill=fill, outline=lighten(fill, 0.30), smooth=False)
        self.create_text(w / 2, h / 2, text=self._text, fill=label,
                         font=self._font)


class Pill(tk.Canvas):
    """Small rounded status pill used in the header."""

    def __init__(self, parent, text="IDLE", colour=MUTED, **kw):
        kw.setdefault("highlightthickness", 0)
        kw.setdefault("bd", 0)
        super().__init__(parent, height=30, width=132, **kw)
        self._text = text
        self._colour = colour
        self._dot = colour
        self.bind("<Configure>", lambda e: self._draw())
        self._draw()

    def set(self, text, colour=None):
        self._text = text
        if colour:
            self._colour = colour
            self._dot = colour
        self._draw()

    def set_dot(self, colour):
        """Move the indicator without touching the label (keeps RUNNING etc.)."""
        self._dot = colour
        self._draw()

    def _draw(self):
        w, h = self.winfo_width(), self.winfo_height()
        if w < 8 or h < 8:
            return
        self.delete("all")
        c = self._colour
        self.create_polygon(rounded_points(2, 2, w - 2, h - 2, (h - 4) / 2),
                            fill=mix(SURFACE, c, 0.30),
                            outline=mix(c, "#000000", 0.25), smooth=False)
        self.create_oval(14, h / 2 - 4, 22, h / 2 + 4, fill=self._dot,
                         outline="")
        self.create_text(30, h / 2, text=self._text, fill=lighten(c, 0.35),
                         font=(FONT, 9, "bold"), anchor="w")
