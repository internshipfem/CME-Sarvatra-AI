"""
Document styling constants — fonts, margins, spacing, and military colors.
Used by all DOCX templates for standard Indian Army CME doctrinal styling.
"""

from docx.shared import Pt, Inches, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

# Page layout: Standard A4 margins
PAGE_MARGIN_TOP = Cm(2.0)
PAGE_MARGIN_BOTTOM = Cm(2.0)
PAGE_MARGIN_LEFT = Cm(2.54)
PAGE_MARGIN_RIGHT = Cm(2.54)

# Fonts
FONT_NAME = 'Arial'
FONT_NAME_BODY = 'Georgia'
FONT_SIZE_BODY = Pt(10.5)
FONT_SIZE_HEADING = Pt(13)
FONT_SIZE_SUBHEADING = Pt(11)
FONT_SIZE_SMALL = Pt(8.5)
FONT_SIZE_META = Pt(9.5)
FONT_SIZE_TITLE = Pt(15)

# Doctrinal Classification Colors
COLOR_CONFIDENTIAL = RGBColor(153, 27, 27)    # #991b1b Crimson
COLOR_SECRET = RGBColor(127, 29, 29)          # #7f1d1d Deep Red
COLOR_RESTRICTED = RGBColor(180, 83, 9)       # #b45309 Amber
COLOR_UNCLASSIFIED = RGBColor(30, 41, 59)     # #1e293b Slate Navy

# General Colors
COLOR_BLACK = RGBColor(15, 23, 42)            # #0f172a Dark Slate
COLOR_DARK_GRAY = RGBColor(51, 65, 85)        # #334155
COLOR_MUTED = RGBColor(100, 116, 139)         # #64748b
COLOR_LINE = RGBColor(15, 23, 42)

# Spacing
LINE_SPACING = Pt(14)
PARAGRAPH_SPACING_BEFORE = Pt(0)
PARAGRAPH_SPACING_AFTER = Pt(6)

# Alignment shortcuts
ALIGN_LEFT = WD_ALIGN_PARAGRAPH.LEFT
ALIGN_CENTER = WD_ALIGN_PARAGRAPH.CENTER
ALIGN_RIGHT = WD_ALIGN_PARAGRAPH.RIGHT
ALIGN_JUSTIFY = WD_ALIGN_PARAGRAPH.JUSTIFY
