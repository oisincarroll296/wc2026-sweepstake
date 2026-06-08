"""
WC 2026 Sweepstake – promotional graphic generator.
Run from:  C:\World Cup
Output:    promo/sweepstake_promo.jpg
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import numpy as np

# ── Palette ───────────────────────────────────────────────────────────────────
BG      = '#0D1B2A'
PANEL   = '#162032'
BORDER  = '#2D4460'
GOLD    = '#D4A017'
GOLD_DK = '#A07810'
WHITE   = '#F1F5F9'
MUTED   = '#94A3B8'
BLUE    = '#105CAC'
GREEN   = '#15803D'
AMBER   = '#C47A1E'
RED     = '#B91C1C'
PURPLE  = '#6D28D9'
TEAL    = '#0E7490'
DIM     = '#1E293B'
ACCENT  = '#1E3A5F'   # slightly lighter than BG for header accent band

PAD = 0.07

# ── Figure ────────────────────────────────────────────────────────────────────
W, H = 12, 18
fig = plt.figure(figsize=(W, H), facecolor=BG, dpi=150)
ax  = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W); ax.set_ylim(0, H)
ax.axis('off'); ax.set_facecolor(BG)

# ── Helpers ───────────────────────────────────────────────────────────────────
def box(x, y, w, h, fc=PANEL, ec=BORDER, lw=0.8, z=2):
    p = FancyBboxPatch((x + PAD, y + PAD), w - 2*PAD, h - 2*PAD,
                       boxstyle=f"round,pad={PAD}",
                       facecolor=fc, edgecolor=ec, linewidth=lw, zorder=z)
    ax.add_patch(p)

def t(x, y, s, sz=10, c=WHITE, bold=False, italic=False, ha='left', va='center', z=4):
    ax.text(x, y, s, fontsize=sz, color=c,
            fontweight='bold' if bold else 'normal',
            fontstyle='italic' if italic else 'normal',
            ha=ha, va=va, zorder=z, clip_on=False)

def section_bar(x, y, w, label, fc=BLUE):
    box(x, y, w, 0.55, fc=fc, ec='none', z=3)
    t(x + w/2, y + 0.275, label, sz=11, bold=True, ha='center', z=4)

def divider_line(y, x0=0.4, x1=None, color=BORDER, lw=0.7, z=3):
    if x1 is None:
        x1 = W - 0.4
    ax.plot([x0, x1], [y, y], color=color, linewidth=lw, zorder=z)

# ═══════════════════════════════════════════════════════════════════════════════
# HEADER  — gold banner with diagonal stripe accents
# ═══════════════════════════════════════════════════════════════════════════════
box(0, 15.9, W, 2.1, fc=GOLD, ec='none', z=2)

# Diagonal stripe decoration on the gold banner
for xi in np.arange(-1, W + 2, 0.9):
    ax.fill_betweenx([15.9, 18.0],
                     [xi, xi + 1.4], [xi + 0.15, xi + 1.55],
                     color=GOLD_DK, alpha=0.35, zorder=3)

# Tournament start callout (top-right of header)
box(8.8, 16.8, 3.0, 0.9, fc=BG, ec=GOLD_DK, lw=1.5, z=5)
t(10.3, 17.35, 'STARTS', sz=7.5, c=MUTED, bold=True, ha='center', z=6)
t(10.3, 17.05, 'JUNE 11, 2026', sz=9, c=GOLD, bold=True, ha='center', z=6)

# Main title
t(W/2 - 0.3, 17.38, 'WORLD CUP 2026', sz=26, c=BG, bold=True, ha='center', z=6)
t(W/2 - 0.3, 16.82, 'SWEEPSTAKE', sz=22, c=BG, bold=True, ha='center', z=6)

# Tagline on dark strip below header
box(0, 15.5, W, 0.48, fc=DIM, ec='none', z=2)
t(W/2, 15.75, '13 Players  ·  48 Teams  ·  4 Tiers  ·  All the Glory',
  sz=10.5, c=MUTED, ha='center', z=3)

# ═══════════════════════════════════════════════════════════════════════════════
# LEFT PANEL – WHAT TO BUY
# ═══════════════════════════════════════════════════════════════════════════════
LX, LY, LW, LH = 0.25, 7.8, 5.55, 7.4
box(LX, LY, LW, LH)
section_bar(LX, LY + LH - 0.65, LW, 'WHAT TO BUY', fc=BLUE)

packages = [
    ('Buy In',          '€5', GOLD,   'Your entry  ·  8 teams across 4 tiers',  True),
    ('Prediction Pack', '€5', GREEN,  'WC Winner  ·  Golden Boot  ·  Dark Horse', False),
    ('Mulligan',        '€3', AMBER,  'Full redraw of all 8 teams',              False),
    ('9th Team',        '€3', PURPLE, 'Extra team for the knockout stage',        False),
    ('Resurrection',    '€5', RED,    'Replace one eliminated team',              False),
    ('Insurance',       '€2', TEAL,   '+25 pts per Tier 1 team out before R16',  False),
]

ROW = 1.02
for i, (name, price, colour, desc, highlight) in enumerate(packages):
    ry = LY + LH - 1.1 - i * ROW
    # subtle row highlight for Buy In
    if highlight:
        box(LX + 0.1, ry - 0.35, LW - 0.2, 0.78, fc=ACCENT, ec=GOLD, lw=1.0, z=3)
    # price pill
    box(LX + 0.25, ry - 0.28, 0.82, 0.62, fc=colour, ec='none', z=4)
    t(LX + 0.66, ry + 0.03, price, sz=13, bold=True, ha='center', z=5)
    # text
    t(LX + 1.25, ry + 0.18, name, sz=10.5, bold=True, z=4)
    t(LX + 1.25, ry - 0.08, desc, sz=8.5,  c=MUTED, z=4)
    if i < len(packages) - 1:
        divider_line(ry - 0.38, x0=LX + 0.15, x1=LX + LW - 0.15)

# ═══════════════════════════════════════════════════════════════════════════════
# RIGHT PANEL – WHAT TO SEND US
# ═══════════════════════════════════════════════════════════════════════════════
RX, RY, RW, RH = 6.2, 7.8, 5.55, 7.4
box(RX, RY, RW, RH)
section_bar(RX, RY + RH - 0.65, RW, 'WHAT TO SEND', fc=GREEN)

groups = [
    ('Your name',
     [('Your full name  (first + last)', WHITE, False)]),
    ('Payment reference on Revolut Shared Pocket',
     [('"NAME  -  BUY IN"',              GOLD,  True),
      ('"NAME  -  BUY IN, PRED PACK"',   GOLD,  True)]),
    ('Captain picks, Send to me directly',
     [('Pre-tournament captain',          MUTED, False),
      ('Knockout stage captain',          MUTED, False)]),
    ('Predictions, Send to me directly  (Pred Pack buyers)',
     [('World Cup Winner',                MUTED, False),
      ('Golden Boot winner',              MUTED, False),
      ('Dark Horse  (Tier 3 or 4 team)',  MUTED, False)]),
]

gy = RY + RH - 1.05
for gi, (header, bullets) in enumerate(groups):
    t(RX + 0.35, gy, header, sz=10, bold=True, c=WHITE, z=4)
    gy -= 0.40
    for text, clr, itl in bullets:
        t(RX + 0.75, gy, f'→  {text}', sz=9, c=clr, italic=itl, z=4)
        gy -= 0.38
    if gi < len(groups) - 1:
        divider_line(gy + 0.08, x0=RX + 0.2, x1=RX + RW - 0.2)
        gy -= 0.12

# Contact strip
box(RX + 0.2, RY + 0.2, RW - 0.4, 0.95, fc=DIM, ec=GOLD, lw=1.5, z=4)
t(RX + RW/2, RY + 0.72, 'Send your details to:', sz=8.5, c=MUTED, ha='center', z=5)
t(RX + RW/2, RY + 0.42, 'oisincarroll296@gmail.com', sz=9.5, c=GOLD, bold=True, ha='center', z=5)

# ═══════════════════════════════════════════════════════════════════════════════
# TIMELINE
# ═══════════════════════════════════════════════════════════════════════════════
TX, TY, TW, TH = 0.25, 1.3, W - 0.5, 6.2
box(TX, TY, TW, TH)
section_bar(TX, TY + TH - 0.65, TW, 'KEY DATES & TIMELINE', fc=PURPLE)

events = [
    ('NOW',       'Sign up & pay your Buy In',                              GOLD),
    ('11 Jun',    'Opening match  —  Predictions locked 1 hr before',      BLUE),
    ('26 Jun',    'Buy-in deadline  —  before last group game',            AMBER),
    ('29 Jun',    'Knockouts begin  —  Resurrection & KO captains open',  GREEN),
    ('Late Jun',  'Ninth Team draw for eligible players',                  PURPLE),
    ('19 Jul',    'THE FINAL!',                   GOLD),
]

DX   = TX + 2.1
TOP  = TY + TH - 1.1
BOT  = TY + 0.65
STEP = (TOP - BOT) / (len(events) - 1)

ax.plot([DX, DX], [BOT, TOP], color=BORDER, linewidth=2.5,
        solid_capstyle='round', zorder=3)

for i, (date, desc, colour) in enumerate(events):
    ey = TOP - i * STEP
    # horizontal tick
    ax.plot([DX - 0.12, DX + 0.12], [ey, ey], color=colour, linewidth=1.5, zorder=4)
    ax.plot(DX, ey, 'o', ms=16, color=colour, zorder=5)
    ax.plot(DX, ey, 'o', ms=7,  color=BG,     zorder=6)
    t(DX - 0.22, ey, date, sz=9.5, c=colour, bold=True, ha='right', z=5)
    t(DX + 0.35, ey, desc, sz=9.5, c=WHITE,              ha='left',  z=5)

# Connector label between "NOW" and first match
ax.annotate('', xy=(DX, TOP - STEP * 0.5),
            xytext=(DX, TOP - STEP * 0.5 + 0.01),
            arrowprops=dict(arrowstyle='-', color=BORDER, lw=0))  # no-op spacer

# ═══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════════════════
box(0.25, 0.2, W - 0.5, 0.85, fc=DIM, ec=GOLD, lw=1.5, z=2)
t(W/2, 0.69, 'Live scores, portfolios & full rules:', sz=8.5, c=MUTED, ha='center', z=3)
t(W/2, 0.39, 'https://fellas-wc2026-sweepstake.streamlit.app/',
  sz=9.5, c=GOLD, bold=True, ha='center', z=3)

# ── Save ──────────────────────────────────────────────────────────────────────
os.makedirs(os.path.dirname(os.path.abspath(__file__)), exist_ok=True)
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sweepstake_promo.jpg')
plt.savefig(out, dpi=150, facecolor=BG)
print(f'Saved: {out}')
plt.close()
