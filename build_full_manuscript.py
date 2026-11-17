"""
build_full_manuscript.py
------------------------
Constructs the submission-ready academic research paper:
'Palaeoclimate Stability and Modern Biodiversity: Methodological Resolution of Spatial Autocorrelation, Macroecological Ceilings, and Taxonomic Divergence'

Target Word Count: 7,000 - 8,000 words
Abstract: 150 - 200 words
Introduction: 1,000 - 1,200 words
Style: Times New Roman, 10 pt, 1.5 line spacing
Tables: 6 main tables (booktabs style, horizontal lines only)
Figures: 7 main figures (embedded from FIGURES_AND_TABLES/)
References: Unnumbered author-year format, authentic DOIs
"""

import os
import sys
from pathlib import Path
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn

REPO_ROOT = Path(__file__).resolve().parent
FIG_DIR = REPO_ROOT / "FIGURES_AND_TABLES"

def set_cell_border(cell, **kwargs):
    """Set cell borders: top, bottom, left, right."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcBorders = parse_xml(r'<w:tcBorders xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>')
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        edge_data = kwargs.get(edge)
        if edge_data:
            tag = f'w:{edge}'
            element = parse_xml(
                f'<{tag} xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
                f'w:val="{edge_data.get("val", "single")}" '
                f'w:sz="{edge_data.get("sz", 4)}" '
                f'w:space="0" '
                f'w:color="{edge_data.get("color", "auto")}"/>'
            )
            tcBorders.append(element)
        else:
            tag = f'w:{edge}'
            element = parse_xml(
                f'<{tag} xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" w:val="none"/>'
            )
            tcBorders.append(element)
    tcPr.append(tcBorders)

def apply_table_styles(table, col_widths=None):
    """Apply booktabs style: horizontal borders only, no vertical lines."""
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    tblPr = table._tbl.tblPr
    borders = parse_xml(r'''
        <w:tblBorders xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
            <w:top w:val="none"/>
            <w:bottom w:val="none"/>
            <w:left w:val="none"/>
            <w:right w:val="none"/>
            <w:insideH w:val="none"/>
            <w:insideV w:val="none"/>
        </w:tblBorders>
    ''')
    tblPr.append(borders)
    
    n_rows = len(table.rows)
    for r_idx, row in enumerate(table.rows):
        trPr = row._tr.get_or_add_trPr()
        trPr.append(parse_xml(r'<w:cantSplit xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>'))
        if r_idx == 0:
            trPr.append(parse_xml(r'<w:tblHeader xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>'))
            
        for c_idx, cell in enumerate(row.cells):
            cell.vertical_alignment = docx.enum.table.WD_CELL_VERTICAL_ALIGNMENT.CENTER
            if col_widths and c_idx < len(col_widths):
                cell.width = Inches(col_widths[c_idx])
            
            for p in cell.paragraphs:
                p.paragraph_format.line_spacing = 1.15
                p.paragraph_format.space_after = Pt(2)
                p.paragraph_format.space_before = Pt(2)
                for run in p.runs:
                    run.font.name = 'Times New Roman'
                    run.font.size = Pt(8.5)
                    if r_idx == 0:
                        run.font.bold = True
            
            if r_idx == 0:
                set_cell_border(cell, 
                                top={'val': 'single', 'sz': 12, 'color': '000000'},
                                bottom={'val': 'single', 'sz': 6, 'color': '000000'})
            elif r_idx == n_rows - 1:
                set_cell_border(cell, 
                                bottom={'val': 'single', 'sz': 12, 'color': '000000'})
            else:
                set_cell_border(cell)

def add_omml_equation(doc, math_xml_text):
    """Insert native editable OMML math equation."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.0
    
    omml_str = f'''
    <m:oMathPara xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math">
      <m:oMath>
        <m:r><m:t>{math_xml_text}</m:t></m:r>
      </m:oMath>
    </m:oMathPara>
    '''
    math_elm = parse_xml(omml_str)
    p._p.append(math_elm)
    return p

def format_paragraph(p, space_before=0, space_after=6, line_spacing=1.5, align=WD_ALIGN_PARAGRAPH.JUSTIFY):
    p.alignment = align
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = line_spacing

def add_body_p(doc, text, bold_prefix="", space_after=6):
    p = doc.add_paragraph()
    format_paragraph(p, space_before=0, space_after=space_after, line_spacing=1.5)
    if bold_prefix:
        r_pre = p.add_run(bold_prefix)
        r_pre.font.name = 'Times New Roman'
        r_pre.font.size = Pt(10)
        r_pre.font.bold = True
    r = p.add_run(text)
    r.font.name = 'Times New Roman'
    r.font.size = Pt(10)
    return p

def add_heading_1(doc, text):
    p = doc.add_paragraph()
    format_paragraph(p, space_before=12, space_after=4, line_spacing=1.15, align=WD_ALIGN_PARAGRAPH.LEFT)
    r = p.add_run(text)
    r.font.name = 'Times New Roman'
    r.font.size = Pt(12)
    r.font.bold = True
    return p

def add_heading_2(doc, text):
    p = doc.add_paragraph()
    format_paragraph(p, space_before=8, space_after=3, line_spacing=1.15, align=WD_ALIGN_PARAGRAPH.LEFT)
    r = p.add_run(text)
    r.font.name = 'Times New Roman'
    r.font.size = Pt(11)
    r.font.bold = True
    return p

def add_heading_3(doc, text):
    p = doc.add_paragraph()
    format_paragraph(p, space_before=6, space_after=2, line_spacing=1.15, align=WD_ALIGN_PARAGRAPH.LEFT)
    r = p.add_run(text)
    r.font.name = 'Times New Roman'
    r.font.size = Pt(10)
    r.font.bold = True
    r.font.italic = True
    return p

def add_caption(doc, text, is_table=False):
    p = doc.add_paragraph()
    format_paragraph(p, space_before=4, space_after=4, line_spacing=1.15, align=WD_ALIGN_PARAGRAPH.LEFT)
    r = p.add_run(text)
    r.font.name = 'Times New Roman'
    r.font.size = Pt(9)
    r.font.bold = True
    return p

def add_image_box(doc, img_path, width_inches=6.0, caption_text=""):
    p_img = doc.add_paragraph()
    p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_img.paragraph_format.space_before = Pt(6)
    p_img.paragraph_format.space_after = Pt(2)
    p_img.paragraph_format.line_spacing = 1.0
    run = p_img.add_run()
    run.add_picture(str(img_path), width=Inches(width_inches))
    if caption_text:
        add_caption(doc, caption_text)

print("Base manuscript generator setup completed.")
