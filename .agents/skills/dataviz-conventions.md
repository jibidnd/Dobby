# dataviz-conventions

Design and chart conventions for dobby HTML reports and dashboards. Load this before building any chart, stat tile, or figure. These replace ad-hoc style choices — every report should look like it came from the same system.

---

## Design tokens

Use these values for all CSS and matplotlib work. Never hardcode one-off colors.

| Role | Value | Use |
|---|---|---|
| `bg` | `#FFFFFF` | Page background |
| `surface` | `#F8FAFC` | Card, table header, axis background |
| `border` | `#E2E8F0` | Dividers, table lines, axis edges |
| `text-primary` | `#0F172A` | Headlines, values, chart titles |
| `text-secondary` | `#64748B` | Labels, captions, axis ticks |
| `accent` | `#2E6DA4` | Primary series, links, active elements |
| `favorable` | `#15803D` | Improvement vs. prior, favorable delta |
| `adverse` | `#B91C1C` | Deterioration vs. prior, adverse delta |
| `neutral-delta` | `#64748B` | Change within noise / no clear direction |

---

## Color palettes

### Categorical — up to 6 series

```python
CAT = ['#2E6DA4', '#E07B39', '#5B9E6F', '#8B5CF6', '#64748B', '#D4A017']
# Blue, Orange, Green, Purple, Slate, Amber
# Assign in order; never skip a color to "match meaning" unless it's the favorable/adverse pair
```

### Sequential — single-metric heatmaps, density

```python
SEQ_BLUE = ['#DBEAFE', '#93C5FD', '#3B82F6', '#1D4ED8', '#1E3A5F']  # light → dark
```

### Diverging — change metrics (favorable = green, adverse = red)

```python
DIV = ['#15803D', '#4ADE80', '#F3F4F6', '#F87171', '#B91C1C']  # good → neutral → bad
```

Use diverging for: ΔLR, ΔIBNR, ΔFreq, any YoY or QoQ change where direction matters.

---

## Matplotlib baseline

Apply at the top of any script that produces figures:

```python
import matplotlib.pyplot as plt
import matplotlib as mpl

mpl.rcParams.update({
    'figure.facecolor':  '#FFFFFF',
    'axes.facecolor':    '#F8FAFC',
    'axes.edgecolor':    '#E2E8F0',
    'axes.spines.top':   False,
    'axes.spines.right': False,
    'grid.color':        '#E2E8F0',
    'grid.linewidth':    0.5,
    'grid.linestyle':    '-',
    'axes.grid':         True,
    'axes.axisbelow':    True,
    'font.family':       'sans-serif',
    'font.sans-serif':   ['Segoe UI', 'Inter', 'Arial', 'DejaVu Sans'],
    'axes.labelcolor':   '#64748B',
    'xtick.color':       '#64748B',
    'ytick.color':       '#64748B',
    'text.color':        '#0F172A',
    'figure.dpi':        110,
})

# Standard figure size for reports (matches generate-report spec)
FIG_W, FIG_H = 6, 4
```

---

## Chart-type heuristics

| Data shape | Chart type | Notes |
|---|---|---|
| Metric over time (quarters, months) | **Line** | Never bar for time trends; show data points if sparse (<8 periods) |
| Category comparison (state, coverage, vehicle) | **Horizontal bar**, sorted descending | Horizontal reads labels; sort by value, not alpha |
| Composition at a point in time | **Pie or donut** only if ≤5 slices and shares are the point; otherwise **stacked bar** | Avoid pie for more than 5 categories |
| Composition over time | **Stacked area** | Normalize to 100% if relative share matters more than absolute |
| Distribution (severity, loss size, mileage) | **Histogram** (equal-width bins) or **boxplot** for cross-group comparison | Label median and mean lines |
| Two continuous variables (freq vs. sev, premium vs. loss) | **Scatter** | Log-scale axes when range spans >2 orders of magnitude |
| Matrix / relativity table | **Heatmap** with diverging palette | Center on 1.000 for relativities, 0 for changes |
| Single headline metric | **Stat tile** (see below) — no chart | Reserve charts for comparisons and trends |

---

## Stat tiles

Use for KPI rows at the top of a report or dashboard section. HTML/CSS pattern:

```html
<div class="stat-row">
  <div class="stat-tile">
    <div class="stat-label">Loss Ratio</div>
    <div class="stat-value">72.4%</div>
    <div class="stat-delta favorable">▼ 1.8pp vs prior</div>
  </div>
  <div class="stat-tile">
    <div class="stat-label">Frequency</div>
    <div class="stat-value">4.23%</div>
    <div class="stat-delta adverse">▲ 0.12pp vs prior</div>
  </div>
</div>
```

```css
.stat-row   { display: flex; gap: 16px; flex-wrap: wrap; margin: 16px 0; }
.stat-tile  { background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px;
              padding: 16px 20px; min-width: 140px; flex: 1; }
.stat-label { font-size: 11px; color: #64748B; text-transform: uppercase;
              letter-spacing: 0.05em; margin-bottom: 6px; }
.stat-value { font-size: 28px; font-weight: 600; color: #0F172A; line-height: 1; }
.stat-delta { font-size: 12px; margin-top: 6px; }
.favorable  { color: #15803D; }
.adverse    { color: #B91C1C; }
.neutral-delta { color: #64748B; }
```

---

## Table style (extends generate-report defaults)

```css
.tbl { border-collapse: collapse; width: 100%; font-size: 13px; }
.tbl th { background: #F8FAFC; color: #64748B; font-weight: 600;
          font-size: 11px; text-transform: uppercase; letter-spacing: 0.04em;
          padding: 8px 12px; border-bottom: 2px solid #E2E8F0; text-align: left; }
.tbl td { padding: 7px 12px; border-bottom: 1px solid #E2E8F0; color: #0F172A; }
.tbl tr:last-child td { border-bottom: none; }
.tbl .num { text-align: right; font-variant-numeric: tabular-nums; }
```

Use `.num` on all numeric columns. Apply `tabular-nums` so decimal points align.

---

## Two-pass process (from frontend-design)

1. **Plan** — list the 2–5 figures you'll build and the chart type for each. State why each type fits. Do this in thinking, not output — only surface it if the choice is non-obvious.
2. **Build** — derive every color from the palettes above, apply the baseline rcParams, and match the stat tile/table CSS exactly. No one-off style decisions.

---

## CSS specificity rules (from frontend-design)

Never mix element selectors with class selectors on the same property — they cancel unpredictably. Use class selectors exclusively for anything that might appear in more than one context:

```css
/* BAD — element selector fights class selector on padding */
section { padding: 24px; }
.section-compact { padding: 8px; }

/* GOOD — class selectors only */
.section { padding: 24px; }
.section-compact { padding: 8px; }
```

---

## What NOT to do

- Don't use 3D charts, shadows on bars, or gradient fills — they obscure magnitude
- Don't start bar chart axes at non-zero without a visible break marker
- Don't use red/green as the only distinguisher (colorblind accessibility)
- Don't add decorative chart elements (background images, logos inside chart area)
- Don't use pie charts for >5 categories or when absolute values matter