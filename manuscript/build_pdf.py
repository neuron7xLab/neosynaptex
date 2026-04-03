#!/usr/bin/env python3
"""
Build arXiv-ready PDF from XFORM_MANUSCRIPT_DRAFT.md
Uses WeasyPrint for high-quality typesetting with embedded figures.
"""
import markdown
import re
import os
from pathlib import Path
from weasyprint import HTML

MANUSCRIPT = Path(__file__).parent / "XFORM_MANUSCRIPT_DRAFT.md"
OUTPUT = Path(__file__).parent / "arxiv_submission.pdf"
FIGURES_DIR = Path(__file__).parent / "figures"

# Read manuscript
md_text = MANUSCRIPT.read_text(encoding="utf-8")

# Replace figure references with actual images
# Insert figures at the appropriate section (after §4.7 Figures description)
fig_html_block = f"""
<div class="figure-panel">
  <img src="{FIGURES_DIR / 'fig1_substrates.png'}" alt="Figure 1: Substrate scaling" />
  <p class="fig-caption"><strong>Figure 1.</strong> Topo-cost scaling across six substrates.
  <em>Row 1 (Tier 1, evidential):</em> zebrafish morphogenesis, HRV PhysioNet, EEG PhysioNet.
  <em>Row 2 (Tier 2, simulation):</em> Gray-Scott, Kuramoto, BN-Syn.
  Red lines: Theil-Sen robust regression. Each panel shows γ and 95% CI.</p>
</div>

<div class="figure-panel">
  <img src="{FIGURES_DIR / 'fig2_convergence.png'}" alt="Figure 2: Convergence" />
  <p class="fig-caption"><strong>Figure 2.</strong> Cross-substrate γ convergence by tier.
  Green: Tier 1 (evidential). Blue: Tier 2 (simulation).
  Dashed line: γ = 1.0 reference. Error bars: 95% bootstrap CI.</p>
</div>

<div class="figure-panel">
  <img src="{FIGURES_DIR / 'fig3_controls.png'}" alt="Figure 3: Controls" />
  <p class="fig-caption"><strong>Figure 3.</strong> Negative controls.
  Shaded band: metastable zone [0.85, 1.15].
  All controls fall outside, confirming falsifiability.</p>
</div>
"""

# Insert figures right before §5. Discussion
md_text = md_text.replace(
    "## 5. Discussion",
    fig_html_block + "\n\n## 5. Discussion"
)

# Convert markdown to HTML
extensions = ['tables', 'fenced_code']
html_body = markdown.markdown(md_text, extensions=extensions)

# Fix LaTeX math for display (simple approach: render as styled text)
# Replace $$...$$ with styled display math
def format_display_math(match):
    expr = match.group(1).strip()
    return f'<div class="display-math">{expr}</div>'

def format_inline_math(match):
    expr = match.group(1).strip()
    return f'<span class="inline-math">{expr}</span>'

html_body = re.sub(r'\$\$(.*?)\$\$', format_display_math, html_body, flags=re.DOTALL)
html_body = re.sub(r'\$([^$]+?)\$', format_inline_math, html_body)

# Full HTML with arXiv-aesthetic CSS
full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<style>
@page {{
    size: A4;
    margin: 2.2cm 2.5cm 2.5cm 2.5cm;
    @top-center {{
        content: "Universal γ-scaling at the edge of metastability";
        font-size: 7.5pt;
        color: #888;
        font-family: "Latin Modern Roman", "Computer Modern", "CMU Serif", "STIX Two Text", "Times New Roman", Georgia, serif;
        font-style: italic;
    }}
    @bottom-center {{
        content: counter(page);
        font-size: 8.5pt;
        color: #555;
        font-family: "Latin Modern Roman", "Computer Modern", "CMU Serif", "STIX Two Text", "Times New Roman", Georgia, serif;
    }}
}}

@page :first {{
    @top-center {{ content: none; }}
}}

body {{
    font-family: "Latin Modern Roman", "Computer Modern", "CMU Serif", "STIX Two Text", "Times New Roman", Georgia, serif;
    font-size: 10.5pt;
    line-height: 1.45;
    color: #1a1a1a;
    text-align: justify;
    hyphens: auto;
    orphans: 3;
    widows: 3;
    font-feature-settings: "liga", "kern";
}}

/* Title block */
h1 {{
    font-size: 16pt;
    font-weight: 700;
    text-align: center;
    margin-top: 0.8cm;
    margin-bottom: 0.3cm;
    line-height: 1.25;
    letter-spacing: -0.015em;
    color: #111;
}}

h1 + p > strong:first-child {{
    display: block;
    text-align: center;
    font-size: 11.5pt;
    margin-top: 0.4cm;
}}

/* Author info block */
body > p:nth-of-type(1),
body > p:nth-of-type(2),
body > p:nth-of-type(3) {{
    text-align: center;
    margin: 0.05cm 0;
    font-size: 10pt;
    color: #444;
}}

/* Abstract styling */
h2:first-of-type {{
    font-size: 11pt;
    text-align: center;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin-top: 0.6cm;
    border-top: 0.5pt solid #bbb;
    padding-top: 0.4cm;
}}

h2:first-of-type + p {{
    font-size: 9.8pt;
    line-height: 1.4;
    margin: 0.3cm 1.2cm 0.5cm 1.2cm;
    text-align: justify;
    color: #222;
}}

/* Section headings */
h2 {{
    font-size: 13pt;
    font-weight: 700;
    margin-top: 0.7cm;
    margin-bottom: 0.25cm;
    color: #111;
    border-bottom: none;
    page-break-after: avoid;
}}

h3 {{
    font-size: 11pt;
    font-weight: 700;
    margin-top: 0.5cm;
    margin-bottom: 0.15cm;
    color: #222;
    page-break-after: avoid;
}}

h4 {{
    font-size: 10.5pt;
    font-weight: 700;
    font-style: italic;
    margin-top: 0.35cm;
    margin-bottom: 0.1cm;
    color: #333;
}}

/* Horizontal rules as section separators */
hr {{
    border: none;
    border-top: 0.4pt solid #ccc;
    margin: 0.5cm 0;
}}

/* Paragraphs */
p {{
    margin: 0.15cm 0;
    text-indent: 0.5cm;
}}

h1 + p, h2 + p, h3 + p, h4 + p,
hr + p, .figure-panel + p,
blockquote + p, table + p,
ol + p, ul + p {{
    text-indent: 0;
}}

/* Tables - publication quality */
table {{
    width: 100%;
    border-collapse: collapse;
    margin: 0.4cm 0;
    font-size: 9pt;
    line-height: 1.3;
    page-break-inside: avoid;
}}

thead {{
    border-top: 1.5pt solid #222;
    border-bottom: 0.8pt solid #222;
}}

thead th {{
    padding: 4pt 6pt;
    text-align: left;
    font-weight: 700;
    color: #111;
    font-size: 8.5pt;
}}

tbody td {{
    padding: 3pt 6pt;
    border-bottom: 0.3pt solid #ddd;
    vertical-align: top;
}}

tbody tr:last-child td {{
    border-bottom: 1.5pt solid #222;
}}

/* Table captions (paragraphs starting with **Table) */
table + p {{
    font-size: 9pt;
    color: #444;
    margin: 0.15cm 0 0.4cm 0;
    text-indent: 0;
    line-height: 1.35;
}}

/* Math styling */
.display-math {{
    text-align: center;
    margin: 0.3cm 1cm;
    font-style: italic;
    font-size: 10.5pt;
    color: #1a1a1a;
    line-height: 1.5;
}}

.inline-math {{
    font-style: italic;
    color: #1a1a1a;
    white-space: nowrap;
}}

/* Figures */
.figure-panel {{
    margin: 0.5cm 0;
    padding: 0;
    text-align: center;
    page-break-inside: avoid;
    break-inside: avoid;
}}

.figure-panel img {{
    max-width: 100%;
    height: auto;
    display: block;
    margin: 0 auto;
    border: 0.3pt solid #e0e0e0;
}}

.fig-caption {{
    font-size: 9pt;
    color: #444;
    text-align: justify;
    margin: 0.15cm 0.8cm 0.3cm 0.8cm;
    text-indent: 0;
    line-height: 1.35;
}}

/* Lists */
ol, ul {{
    margin: 0.15cm 0 0.15cm 0.8cm;
    padding: 0;
}}

li {{
    margin: 0.05cm 0;
    text-indent: 0;
    font-size: 10pt;
}}

/* Block quotes */
blockquote {{
    margin: 0.3cm 1cm;
    padding: 0.15cm 0.3cm;
    border-left: 2pt solid #ccc;
    color: #444;
    font-size: 9.5pt;
}}

/* Code */
code {{
    font-family: "Latin Modern Mono", "Courier New", monospace;
    font-size: 9pt;
    background: #f5f5f5;
    padding: 1pt 3pt;
    border-radius: 2pt;
}}

pre {{
    background: #f8f8f8;
    padding: 0.2cm 0.4cm;
    border: 0.3pt solid #e0e0e0;
    font-size: 8.5pt;
    overflow-x: auto;
    line-height: 1.3;
}}

/* References */
h2:last-of-type {{
    font-size: 11pt;
    margin-top: 0.5cm;
}}

/* Strong/emphasis */
strong {{
    font-weight: 700;
    color: #111;
}}

em {{
    font-style: italic;
    color: #222;
}}

/* Print optimization */
@media print {{
    body {{ font-size: 10.5pt; }}
    .figure-panel {{ page-break-inside: avoid; }}
    h2, h3 {{ page-break-after: avoid; }}
    table {{ page-break-inside: avoid; }}
}}
</style>
</head>
<body>
{html_body}
</body>
</html>
"""

print("Generating PDF...")
HTML(string=full_html, base_url=str(FIGURES_DIR)).write_pdf(str(OUTPUT))
print(f"✓ PDF: {OUTPUT}")
print(f"  Size: {OUTPUT.stat().st_size / 1024:.0f} KB")
