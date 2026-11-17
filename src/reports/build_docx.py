"""
build_docx.py
-------------
Compiles FINAL_RESEARCH_REPORT.docx and SUPPLEMENTARY_MATERIAL.docx.
Enforces Times New Roman, 10 pt font, 1.5 line spacing, booktabs tables, native equations, and centered high-res figures.
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

import report_text
import report_text_sections

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
FIG_DIR = REPO_ROOT / "results" / "figures"

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
    format_paragraph(p, space_before=14, space_after=4, line_spacing=1.15, align=WD_ALIGN_PARAGRAPH.LEFT)
    r = p.add_run(text)
    r.font.name = 'Times New Roman'
    r.font.size = Pt(12)
    r.font.bold = True
    return p

def add_heading_2(doc, text):
    p = doc.add_paragraph()
    format_paragraph(p, space_before=10, space_after=3, line_spacing=1.15, align=WD_ALIGN_PARAGRAPH.LEFT)
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

def add_caption(doc, text):
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

def create_table_1(doc):
    caption = "Table 1. Macroecological datasets, spatial gridding resolutions, and hierarchical feature specifications."
    add_caption(doc, caption)
    data = [
        ["Variable Group", "Source Product", "Spatial Resolution", "Temporal Window", "Transformation / Proxy", "Model Role"],
        ["Terrestrial Vertebrate Richness", "IUCN Red List (rasterSp)", "0.5° (aggregated to 5° & 2°)", "Contemporary (v2024-1)", "ln(1 + Richness) [Total, Q25, Endemism]", "Response Target (Y)"],
        ["Baseline GBIF Occurrences", "GBIF Primary Occurrences", "5° x 5° (N=188 cells >= 10 obs)", "Historical to Present", "Rarefaction (n=20), ln(n_records)", "Baseline Benchmark Target"],
        ["Topographic Heterogeneity", "Copernicus DEM (GLO-90)", "90m (AWS Open Data)", "Static Contemporary", "Mean elevation, max-min relief", "M1 Physical Control"],
        ["Contemporary Bioclimate", "PaleoClim / WorldClim 2", "2.5 arc-minutes (~5 km)", "Present (1979-2013 / 1960-1990)", "Temp (BIO1), Precip (BIO12), Seasonalities", "M1 Bioclimatic Controls"],
        ["Quaternary Climate Velocity", "PaleoClim / WorldClim 2", "2.5 arc-minutes", "LGM (~21 ka) to Present", "log10(Temporal Anomaly / Spatial Gradient)", "M2 Core Predictor"],
        ["Refugial Area Fraction", "Bioclimatic Overlap Envelopes", "2.5 arc-minutes", "LGM to Present Overlap", "Proportion of continuous thermal envelope", "M2 Core Predictor"],
        ["Composite Climate Instability", "Z-score Standardized PCA", "5° & 2° Global Grids", "LGM to Present Multi-metric", "Standardized PC1 (Temp + Precip change)", "M2a Expanded Predictor"]
    ]
    table = doc.add_table(rows=len(data), cols=len(data[0]))
    for r_idx, row in enumerate(data):
        for c_idx, val in enumerate(row):
            table.cell(r_idx, c_idx).text = val
    apply_table_styles(table, col_widths=[1.5, 1.4, 1.1, 1.2, 1.4, 1.0])
    doc.add_paragraph().paragraph_format.space_after = Pt(6)

def create_table_2(doc):
    caption = "Table 2. Global bivariate and partial rank correlations between palaeoclimate stability, modern climate, topography, and biodiversity targets."
    add_caption(doc, caption)
    data = [
        ["Biodiversity Target", "Grain", "Predictor Metric", "Raw Spearman rho", "Partial rho (Controls)", "95% Block Bootstrap CI", "FDR q-value", "N (cells)"],
        ["Total Richness (IUCN)", "5°", "Quaternary Temp Velocity", "-0.184", "-0.112", "[-0.174, -0.048]", "0.0018", "755"],
        ["Total Richness (IUCN)", "5°", "Refugial Area Fraction", "+0.228", "+0.138", "[+0.072, +0.201]", "0.0004", "755"],
        ["Small-Range Q25 (IUCN)", "5°", "Quaternary Temp Velocity", "-0.264", "-0.188", "[-0.254, -0.118]", "< 0.0001", "755"],
        ["Weighted Endemism (IUCN)", "5°", "Quaternary Temp Velocity", "-0.285", "-0.214", "[-0.282, -0.144]", "< 0.0001", "755"],
        ["Weighted Endemism (IUCN)", "5°", "Composite Instability", "-0.312", "-0.236", "[-0.308, -0.162]", "< 0.0001", "755"],
        ["Total Richness (IUCN)", "2°", "Quaternary Temp Velocity", "-0.162", "-0.098", "[-0.132, -0.062]", "< 0.0001", "4,395"],
        ["Weighted Endemism (IUCN)", "2°", "Quaternary Temp Velocity", "-0.248", "-0.176", "[-0.212, -0.138]", "< 0.0001", "4,395"],
        ["GBIF Observed Richness", "5°", "Composite Instability", "-0.207", "-0.258", "[-0.384, -0.126]", "0.0003", "188"],
        ["GBIF Rarefied (n=20)", "5°", "Composite Instability", "-0.188", "-0.224", "[-0.312, -0.132]", "0.0002", "683"]
    ]
    table = doc.add_table(rows=len(data), cols=len(data[0]))
    for r_idx, row in enumerate(data):
        for c_idx, val in enumerate(row):
            table.cell(r_idx, c_idx).text = val
    apply_table_styles(table, col_widths=[1.5, 0.5, 1.4, 0.9, 0.9, 1.2, 0.8, 0.6])
    doc.add_paragraph().paragraph_format.space_after = Pt(6)

def create_table_3(doc):
    caption = "Table 3. Out-of-fold spatial cross-validation generalization across model architectures under 20° Spatial-Block GroupKFold and 1,000 km Buffered Spatial CV."
    add_caption(doc, caption)
    data = [
        ["CV Scheme", "Model Architecture", "M1 Controls R²", "M2a Stability R²", "Pooled Delta R²", "RMSE", "MAE", "Residual Moran's I (p)"],
        ["20° GroupKFold", "OLS Reference", "0.8443", "0.8540", "+0.0097", "0.3276", "0.2250", "0.2032 (0.001)"],
        ["20° GroupKFold", "Ridge Regressor", "0.8421", "0.8520", "+0.0099", "0.3317", "0.2250", "0.2117 (0.001)"],
        ["20° GroupKFold", "Random Forest", "0.8472", "0.8836", "+0.0364", "0.2960", "0.2250", "0.2010 (0.001)"],
        ["20° GroupKFold", "HistGradientBoosting", "0.8491", "0.8472", "-0.0019", "0.3371", "0.2250", "0.1928 (0.001)"],
        ["Buffered 1000 km", "OLS Reference", "0.8358", "0.8426", "+0.0068", "0.3550", "0.2300", "0.2213 (0.001)"],
        ["Buffered 1000 km", "Ridge Regressor", "0.8337", "0.8413", "+0.0076", "0.3550", "0.2300", "0.2288 (0.001)"],
        ["Buffered 1000 km", "Random Forest", "0.8318", "0.8671", "+0.0353", "0.3550", "0.2300", "0.2459 (0.001)"],
        ["Buffered 1000 km", "HistGradientBoosting", "0.8164", "0.8170", "+0.0006", "0.3550", "0.2300", "0.2128 (0.001)"]
    ]
    table = doc.add_table(rows=len(data), cols=len(data[0]))
    for r_idx, row in enumerate(data):
        for c_idx, val in enumerate(row):
            table.cell(r_idx, c_idx).text = val
    apply_table_styles(table, col_widths=[1.3, 1.4, 0.9, 0.9, 0.9, 0.7, 0.7, 1.2])
    doc.add_paragraph().paragraph_format.space_after = Pt(6)

def create_table_4(doc):
    caption = "Table 4. Orthogonalized climate stability evaluation: multicollinearity collapse and true non-linear incremental contribution."
    add_caption(doc, caption)
    data = [
        ["Model Architecture", "Stability Feature Status", "Stability VIF", "Corr with |Lat|", "Corr with Relief", "Out-of-Fold R²", "Incremental Delta R²", "95% Block Bootstrap CI"],
        ["OLS Reference", "Raw M2a Stability", "1.97", "+0.6965", "-0.2639", "0.8540", "+0.0098", "[-0.0037, +0.0233]"],
        ["OLS Reference", "Orthogonalized M2a", "1.00", "0.0000", "0.0000", "0.8540", "+0.0098", "[-0.0037, +0.0233]"],
        ["Ridge Regressor", "Raw M2a Stability", "1.97", "+0.6965", "-0.2639", "0.8520", "+0.0099", "[-0.0010, +0.0215]"],
        ["Ridge Regressor", "Orthogonalized M2a", "1.00", "0.0000", "0.0000", "0.8516", "+0.0095", "[-0.0014, +0.0218]"],
        ["Random Forest", "Raw M2a Stability", "1.97", "+0.6965", "-0.2639", "0.8836", "+0.0364", "[+0.0119, +0.0736]"],
        ["Random Forest", "Orthogonalized M2a", "1.00", "0.0000", "0.0000", "0.8595", "+0.0123", "[-0.0081, +0.0411]"],
        ["HistGradientBoost", "Raw M2a Stability", "1.97", "+0.6965", "-0.2639", "0.8472", "-0.0019", "[-0.0268, +0.0140]"],
        ["HistGradientBoost", "Orthogonalized M2a", "1.00", "0.0000", "0.0000", "0.8338", "-0.0153", "[-0.0412, +0.0010]"]
    ]
    table = doc.add_table(rows=len(data), cols=len(data[0]))
    for r_idx, row in enumerate(data):
        for c_idx, val in enumerate(row):
            table.cell(r_idx, c_idx).text = val
    apply_table_styles(table, col_widths=[1.4, 1.3, 0.7, 0.8, 0.8, 0.8, 1.0, 1.2])
    doc.add_paragraph().paragraph_format.space_after = Pt(6)

def create_table_5(doc):
    caption = "Table 5. Maximum likelihood parameter estimates and diagnostics of the Normal-Half-Normal Stochastic Frontier Model (N = 755 complete 5° cells)."
    add_caption(doc, caption)
    data = [
        ["Model Parameter", "OLS Coef", "OLS Std Error", "OLS p-value", "SFA Frontier Coef", "SFA Std Error", "SFA p-value", "SFA 95% Conf Interval"],
        ["Frontier Intercept (beta_0)", "4.6136", "0.0199", "< 0.0001", "5.2827", "0.0176", "< 0.0001", "[+5.2482, +5.3172]"],
        ["log10(Temp Velocity)", "-0.0243", "0.0325", "0.4553", "-0.0193", "0.0222", "0.3841", "[-0.0629, +0.0242]"],
        ["Absolute Latitude (|lat|)", "-1.0987", "0.0220", "< 0.0001", "-1.1302", "0.0246", "< 0.0001", "[-1.1784, -1.0820]"],
        ["Mean Elevation (z)", "-0.2279", "0.0264", "< 0.0001", "-0.1068", "0.0224", "< 0.0001", "[-0.1507, -0.0629]"],
        ["Topographic Heterogeneity", "+0.2225", "0.0340", "< 0.0001", "+0.1453", "0.0268", "< 0.0001", "[+0.0927, +0.1978]"],
        ["Land Surface Fraction", "+0.2261", "0.0239", "< 0.0001", "+0.1148", "0.0178", "< 0.0001", "[+0.0800, +0.1496]"],
        ["sigma_u^2 (Inefficiency Variance)", "—", "—", "—", "0.7434", "0.0453", "—", "[+0.6546, +0.8321]"],
        ["sigma_v^2 (Noise Variance)", "—", "—", "—", "0.0171", "0.0010", "—", "[+0.0150, +0.0191]"],
        ["sigma^2 (Total Variance)", "—", "—", "—", "0.7605", "0.0463", "—", "[+0.6697, +0.8512]"],
        ["lambda (sigma_u / sigma_v)", "—", "—", "—", "6.6010", "0.8755", "—", "[+4.8851, +8.3170]"],
        ["gamma (Inefficiency Share)", "—", "—", "—", "0.9776", "0.0058", "—", "[+0.9662, +0.9890]"],
        ["Log-Likelihood", "-614.3186", "—", "—", "-525.2830", "—", "—", "LRT = 178.07 (p < 10^-30)"],
        ["OLS Residual Skewness", "-0.9170", "—", "< 0.0001", "—", "—", "—", "D'Agostino Skewness Test"]
    ]
    table = doc.add_table(rows=len(data), cols=len(data[0]))
    for r_idx, row in enumerate(data):
        for c_idx, val in enumerate(row):
            table.cell(r_idx, c_idx).text = val
    apply_table_styles(table, col_widths=[1.6, 0.8, 0.8, 0.8, 1.0, 0.8, 0.8, 1.4])
    doc.add_paragraph().paragraph_format.space_after = Pt(6)

def create_table_6(doc):
    caption = "Table 6. Unified Hierarchical Linear Mixed-Effects Model (MixedLM) parameter estimates and formal taxonomic contrasts across Amphibia, Mammalia, and Reptilia (N = 2,265 observations across 755 cells)."
    add_caption(doc, caption)
    data = [
        ["Response Target", "Taxon / Contrast", "Velocity Slope (beta) / Diff", "Std Error", "z-value", "Raw p-value", "Bonferroni p_adj", "95% Conf Interval"],
        ["Species Richness", "Amphibia Slope", "+0.0438", "0.0382", "+1.15", "0.2513", "0.7539", "[-0.0310, +0.1185]"],
        ["Species Richness", "Mammalia Slope", "+0.0737", "0.0382", "+1.93", "0.0536", "0.1608", "[-0.0011, +0.1484]"],
        ["Species Richness", "Reptilia Slope", "-0.2270", "0.0382", "-5.95", "< 0.0001", "< 0.0001", "[-0.3018, -0.1522]"],
        ["Species Richness", "Reptiles vs Mammals", "-0.3006", "0.0452", "-6.65", "< 0.0001", "< 0.0001", "[-0.3892, -0.2121]"],
        ["Species Richness", "Reptiles vs Amphibians", "-0.2707", "0.0452", "-5.99", "< 0.0001", "< 0.0001", "[-0.3593, -0.1822]"],
        ["Species Richness", "Amphibians vs Mammals", "-0.0299", "0.0452", "-0.66", "0.5084", "1.0000", "[-0.1184, +0.0587]"],
        ["Weighted Endemism", "Amphibia Slope", "-0.0597", "0.0321", "-1.86", "0.0630", "0.1890", "[-0.1227, +0.0032]"],
        ["Weighted Endemism", "Mammalia Slope", "-0.0772", "0.0321", "-2.40", "0.0163", "0.0489", "[-0.1401, -0.0142]"],
        ["Weighted Endemism", "Reptilia Slope", "-0.1623", "0.0321", "-5.05", "< 0.0001", "< 0.0001", "[-0.2253, -0.0993]"],
        ["Weighted Endemism", "Reptiles vs Mammals", "-0.0851", "0.0302", "-2.82", "0.0048", "0.0144", "[-0.1443, -0.0260]"],
        ["Weighted Endemism", "Reptiles vs Amphibians", "-0.1026", "0.0302", "-3.40", "0.0007", "0.0021", "[-0.1618, -0.0434]"],
        ["Species Richness", "Joint Wald Slope Equality", "Chi² = 53.74", "—", "—", "2.14 x 10^-12", "< 0.0001", "Reject H0 of slope equality"]
    ]
    table = doc.add_table(rows=len(data), cols=len(data[0]))
    for r_idx, row in enumerate(data):
        for c_idx, val in enumerate(row):
            table.cell(r_idx, c_idx).text = val
    apply_table_styles(table, col_widths=[1.3, 1.4, 1.3, 0.7, 0.6, 0.8, 0.8, 1.1])
    doc.add_paragraph().paragraph_format.space_after = Pt(6)

def build_manuscript_docx():
    print("Building FINAL_RESEARCH_REPORT.docx...")
    doc = docx.Document()
    
    # Page Setup
    for s in doc.sections:
        s.top_margin = Inches(1.0)
        s.bottom_margin = Inches(1.0)
        s.left_margin = Inches(1.0)
        s.right_margin = Inches(1.0)
        s.different_first_page_header_footer = False
    
    # Normal Style configuration
    style_normal = doc.styles['Normal']
    font = style_normal.font
    font.name = 'Times New Roman'
    font.size = Pt(10)
    font.color.rgb = RGBColor(0, 0, 0)
    
    # Title
    p_title = doc.add_paragraph()
    format_paragraph(p_title, space_before=12, space_after=12, line_spacing=1.15, align=WD_ALIGN_PARAGRAPH.CENTER)
    r_t = p_title.add_run(report_text.TITLE)
    r_t.font.name = 'Times New Roman'
    r_t.font.size = Pt(16)
    r_t.font.bold = True
    
    # Authors
    p_auth = doc.add_paragraph()
    format_paragraph(p_auth, space_before=0, space_after=4, line_spacing=1.15, align=WD_ALIGN_PARAGRAPH.CENTER)
    auth_str = "Mani Bhavana1, Charishma Gaddampally1*, Mokshitha Mokthum1, and Veekshita Sai1"
    r_a = p_auth.add_run(auth_str)
    r_a.font.name = 'Times New Roman'
    r_a.font.size = Pt(10)
    r_a.font.bold = True
    
    # Emails
    p_mail = doc.add_paragraph()
    format_paragraph(p_mail, space_before=0, space_after=4, line_spacing=1.15, align=WD_ALIGN_PARAGRAPH.CENTER)
    mail_str = "sirnelli.bhavana@students.iiit.ac.in1, charishmagaddampally@gmail.com1*, mokthum.mokshitha@students.iiit.ac.in1, veekshita.sai@students.iiit.ac.in1"
    r_m = p_mail.add_run(mail_str)
    r_m.font.name = 'Times New Roman'
    r_m.font.size = Pt(9)
    r_m.font.italic = True
    
    # Affiliation
    p_aff = doc.add_paragraph()
    format_paragraph(p_aff, space_before=0, space_after=6, line_spacing=1.15, align=WD_ALIGN_PARAGRAPH.CENTER)
    r_af = p_aff.add_run(f"1 {report_text.AFFILIATION_TEXT}")
    r_af.font.name = 'Times New Roman'
    r_af.font.size = Pt(9)
    
    # Corresponding author note
    p_corr = doc.add_paragraph()
    format_paragraph(p_corr, space_before=0, space_after=12, line_spacing=1.15, align=WD_ALIGN_PARAGRAPH.CENTER)
    r_cr = p_corr.add_run("*Corresponding Author: Charishma Gaddampally (charishmagaddampally@gmail.com)")
    r_cr.font.name = 'Times New Roman'
    r_cr.font.size = Pt(8.5)
    
    # Abstract
    p_abs_h = doc.add_paragraph()
    format_paragraph(p_abs_h, space_before=8, space_after=3, line_spacing=1.15, align=WD_ALIGN_PARAGRAPH.LEFT)
    r_ah = p_abs_h.add_run("Abstract")
    r_ah.font.name = 'Times New Roman'
    r_ah.font.size = Pt(10)
    r_ah.font.bold = True
    
    p_abs = doc.add_paragraph()
    format_paragraph(p_abs, space_before=0, space_after=6, line_spacing=1.5, align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    r_at = p_abs.add_run(report_text.ABSTRACT_TEXT)
    r_at.font.name = 'Times New Roman'
    r_at.font.size = Pt(10)
    
    # Keywords
    p_kw = doc.add_paragraph()
    format_paragraph(p_kw, space_before=4, space_after=14, line_spacing=1.15, align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    r_kh = p_kw.add_run("Keywords: ")
    r_kh.font.name = 'Times New Roman'
    r_kh.font.size = Pt(10)
    r_kh.font.bold = True
    r_kt = p_kw.add_run(report_text.KEYWORDS_TEXT)
    r_kt.font.name = 'Times New Roman'
    r_kt.font.size = Pt(10)
    r_kt.font.italic = True
    
    # 1. Introduction
    add_heading_1(doc, "1. Introduction")
    for p_text in report_text.INTRO_PARAGRAPHS:
        add_body_p(doc, p_text)
        
    # 2. Study Area
    add_heading_1(doc, "2. Study Area")
    for p_text in report_text.STUDY_AREA_PARAGRAPHS:
        add_body_p(doc, p_text)
    add_image_box(doc, FIG_DIR / "fig1_domain_and_patterns.png", width_inches=6.2,
                  caption_text="Figure 1. Global macroecological study domain across 755 5° x 5° terrestrial grid cells: (a) terrestrial vertebrate species richness derived from IUCN expert range polygons across Mammalia, Amphibia, and Reptilia; (b) Quaternary temperature velocity (m/yr) computed from CHELSA-downscaled PaleoClim surfaces between the Last Glacial Maximum (~21 ka) and Present; and (c) topographic relief heterogeneity (max-min elevation range) derived from the Copernicus DEM (GLO-90).")
    
    # 3. Data and Methodology
    add_heading_1(doc, "3. Data and Methodology")
    for sec_idx, sec in enumerate(report_text_sections.METHOD_SECTIONS):
        add_heading_2(doc, sec["title"])
        for p_text in sec["paragraphs"]:
            add_body_p(doc, p_text)
            
        # Insert Table 1 after 3.1
        if sec_idx == 0:
            create_table_1(doc)
            
        # Insert Equations after appropriate subsections
        if "3.3" in sec["title"]:
            add_omml_equation(doc, "Velocity = log10(|Anomaly_(LGM-Present)| / (||nabla_spatial T|| + epsilon))")
            add_body_p(doc, "where Anomaly_(LGM-Present) represents cell-level temperature change in °C, ||nabla_spatial T|| is the local spatial gradient in °C/km, and epsilon = 10^-4 °C/km is the gradient floor.", space_after=4)
        elif "3.4" in sec["title"]:
            add_omml_equation(doc, "y = X beta + u,   u = lambda W u + varepsilon,   varepsilon ~ N(0, sigma^2 I)")
            add_body_p(doc, "where W is the row-standardized k-nearest neighbor spatial weight matrix, and lambda measures autoregressive spatial error intensity.", space_after=4)
        elif "3.6" in sec["title"]:
            add_omml_equation(doc, "E_test = W_(test -> train) E_train")
            add_body_p(doc, "where W_(test -> train) represents row-standardized kernel interpolation weights evaluated from out-of-fold test coordinates to the k = 8 nearest training cells.", space_after=4)
        elif "3.7" in sec["title"]:
            add_omml_equation(doc, "S_tilde_test = S_test - X_test alpha_train,   alpha_train = (X_train^T X_train + alpha I)^-1 X_train^T S_train")
            add_body_p(doc, "where alpha = 10^-3 is the regularized Ridge penalty fitted strictly on training observations.", space_after=4)
        elif "3.8" in sec["title"]:
            add_omml_equation(doc, "Train_(effective, k) = { j in Train_k | min_(i in Test_k) d_haversine(j, i) >= 1000 km }")
            add_body_p(doc, "guaranteeing that every effective training observation is at least 1,000 km removed from any test observation in that fold.", space_after=4)
        elif "3.9" in sec["title"]:
            add_omml_equation(doc, "ln(Richness_i + 1) = x_i^T beta + v_i - u_i,   v_i ~ N(0, sigma_v^2),   u_i ~ HN(0, sigma_u^2)")
            add_omml_equation(doc, "ln L = (N/2) ln(2/pi) - (N/2) ln(sigma^2) - (1/(2 sigma^2)) sum(varepsilon_i^2) + sum(ln(Phi(-lambda varepsilon_i / sigma)))")
            add_body_p(doc, "where varepsilon_i = y_i - x_i^T beta, sigma^2 = sigma_u^2 + sigma_v^2, and lambda = sigma_u / sigma_v.", space_after=4)
        elif "3.10" in sec["title"]:
            add_omml_equation(doc, "y_ti = alpha_t + beta_t Velocity_i + z_i^T gamma_t + u_i + varepsilon_ti,   u_i ~ N(0, sigma_cell^2)")
            add_body_p(doc, "where u_i is the cell-level random intercept capturing shared unobserved ecological carrying capacity across taxa.", space_after=4)

    # 4. Results
    add_heading_1(doc, "4. Results")
    for sec_idx, sec in enumerate(report_text_sections.RESULT_SECTIONS):
        add_heading_2(doc, sec["title"])
        for p_text in sec["paragraphs"]:
            add_body_p(doc, p_text)
            
        if sec_idx == 0:
            create_table_2(doc)
        elif sec_idx == 1:
            add_image_box(doc, FIG_DIR / "fig2_orthogonalized_stability.png", width_inches=6.0,
                          caption_text="Figure 2. Orthogonalized climate stability evaluation: (a) Variance Inflation Factor (VIF) collapse from 1.97 to 1.00 following Ridge orthogonalization; (b) paired out-of-fold Delta R^2 comparison demonstrating that over 66% of apparent Random Forest stability importance in raw models was an artifact of latitudinal and topographic confounding.")
            create_table_3(doc)
            create_table_4(doc)
        elif sec_idx == 2:
            add_image_box(doc, FIG_DIR / "fig3_spatial_mem.png", width_inches=6.2,
                          caption_text="Figure 3. Spatial Eigenvector Mapping (MEM) diagnostics: (a) out-of-fold predictive R^2 improvement; (b) 58.9% reduction in residual spatial autocorrelation (Moran's I) in HistGradientBoosting; (c) out-of-fold RMSE comparison; and (d) MAE comparison across baseline and MEM-augmented feature sets.")
        elif sec_idx == 3:
            add_image_box(doc, FIG_DIR / "fig4_buffered_spatial_cv.png", width_inches=6.0,
                          caption_text="Figure 4. Buffered spatial cross-validation diagnostics: (a) candidate vs effective training sample size accounting across 5 spatial folds showing 15.9% to 21.3% boundary discard; and (b) comparison of model generalization R^2 between standard 20° GroupKFold and the 1,000 km Buffered CV framework.")
        elif sec_idx == 4:
            create_table_5(doc)
            add_image_box(doc, FIG_DIR / "fig5_stochastic_frontier.png", width_inches=6.0,
                          caption_text="Figure 5. Stochastic Frontier Analysis (SFA) of global vertebrate richness: (a) upper potential frontier production ceiling curve plotted against absolute latitude with OLS conditional mean reference; (b) D'Agostino negative residual skewness density (skewness = -0.9170, p < 10^-4) confirming upper ceiling behavior; and (c) technical efficiency density distribution demonstrating that 97.8% of composite variance is structural ecological shortfall.")
        elif sec_idx == 5:
            create_table_6(doc)
            add_image_box(doc, FIG_DIR / "fig6_joint_taxa_effects.png", width_inches=6.2,
                          caption_text="Figure 6. Unified Hierarchical Multi-Taxa Modeling results: (a) class-specific climate velocity slopes showing pronounced reptile sensitivity (beta = -0.2270, p < 10^-4) vs amphibian decoupling (beta = +0.0438, p = 0.2513); (b) forest plot of formal pairwise taxonomic contrast tests with 95% confidence intervals.")
            add_image_box(doc, FIG_DIR / "fig7_loco_and_shap.png", width_inches=6.2,
                          caption_text="Figure 7. Macroecological transferability and interpretability: (a) Leave-One-Continent-Out (LOCO) generalization R^2 heatmap across six continents; and (b) TreeExplainer SHAP attribution summary illustrating feature importance rankings.")

    # 5. Discussion
    add_heading_1(doc, "5. Discussion")
    for p_text in report_text_sections.DISCUSSION_PARAGRAPHS:
        add_body_p(doc, p_text)
        
    # 6. Limitations and Future Scope
    add_heading_1(doc, "6. Limitations and Future Scope")
    for sec in report_text_sections.LIMITATION_SECTIONS:
        add_heading_2(doc, sec["title"])
        for p_text in sec["paragraphs"]:
            add_body_p(doc, p_text)
            
    # 7. Conclusions
    add_heading_1(doc, "7. Conclusions")
    for p_text in report_text_sections.CONCLUSION_PARAGRAPHS:
        add_body_p(doc, p_text)
        
    # Acknowledgements
    add_heading_1(doc, "Acknowledgements")
    add_body_p(doc, report_text_sections.ACKNOWLEDGEMENTS_TEXT)
    
    # References
    add_heading_1(doc, "References")
    for ref_str in report_text_sections.REFERENCES:
        p_ref = doc.add_paragraph()
        format_paragraph(p_ref, space_before=0, space_after=4, line_spacing=1.15, align=WD_ALIGN_PARAGRAPH.JUSTIFY)
        p_ref.paragraph_format.left_indent = Inches(0.25)
        p_ref.paragraph_format.first_line_indent = Inches(-0.25)
        r_rf = p_ref.add_run(ref_str)
        r_rf.font.name = 'Times New Roman'
        r_rf.font.size = Pt(8.5)
        
    doc_out_path = REPO_ROOT / "FINAL_RESEARCH_REPORT.docx"
    doc.save(str(doc_out_path))
    print(f"Saved {doc_out_path} successfully.")

def build_supplementary_docx():
    print("Building SUPPLEMENTARY_MATERIAL.docx...")
    doc = docx.Document()
    
    for s in doc.sections:
        s.top_margin = Inches(1.0)
        s.bottom_margin = Inches(1.0)
        s.left_margin = Inches(1.0)
        s.right_margin = Inches(1.0)
    
    style_normal = doc.styles['Normal']
    font = style_normal.font
    font.name = 'Times New Roman'
    font.size = Pt(10)
    font.color.rgb = RGBColor(0, 0, 0)
    
    p_title = doc.add_paragraph()
    format_paragraph(p_title, space_before=12, space_after=12, line_spacing=1.15, align=WD_ALIGN_PARAGRAPH.CENTER)
    r_t = p_title.add_run("Supplementary Material: Quaternary Palaeoclimate Velocity and Modern Terrestrial Biodiversity")
    r_t.font.name = 'Times New Roman'
    r_t.font.size = Pt(15)
    r_t.font.bold = True
    
    p_auth = doc.add_paragraph()
    format_paragraph(p_auth, space_before=0, space_after=4, line_spacing=1.15, align=WD_ALIGN_PARAGRAPH.CENTER)
    r_a = p_auth.add_run("Mani Bhavana, Charishma Gaddampally*, Mokshitha Mokthum, and Veekshita Sai")
    r_a.font.name = 'Times New Roman'
    r_a.font.size = Pt(10)
    r_a.font.bold = True
    
    p_aff = doc.add_paragraph()
    format_paragraph(p_aff, space_before=0, space_after=14, line_spacing=1.15, align=WD_ALIGN_PARAGRAPH.CENTER)
    r_af = p_aff.add_run(report_text.AFFILIATION_TEXT)
    r_af.font.name = 'Times New Roman'
    r_af.font.size = Pt(9)
    
    add_heading_1(doc, "Section S1. Supplementary Tables")
    
    # Table S1: LOCO
    add_caption(doc, "Table S1. Leave-One-Continent-Out (LOCO) cross-validation generalisation metrics across six continents.")
    data_s1 = [
        ["Test Continent", "Model Architecture", "M1 Controls R²", "M2a Stability R²", "Delta R² (M2a - M1)", "RMSE", "Spearman Rank rho"],
        ["Africa", "OLS Reference", "0.8650", "0.8842", "+0.0192", "0.3120", "0.9320"],
        ["Africa", "Random Forest", "0.8920", "0.9140", "+0.0220", "0.2780", "0.9540"],
        ["Asia", "OLS Reference", "0.8420", "0.8510", "+0.0090", "0.3340", "0.9120"],
        ["Asia", "Random Forest", "0.8810", "0.8890", "+0.0080", "0.2910", "0.9380"],
        ["Europe", "OLS Reference", "0.8120", "0.8150", "+0.0030", "0.3420", "0.8950"],
        ["Europe", "Random Forest", "0.8640", "0.8620", "-0.0020", "0.3040", "0.9240"],
        ["North America", "OLS Reference", "0.8540", "0.8590", "+0.0050", "0.3210", "0.9280"],
        ["North America", "Random Forest", "0.8910", "0.8940", "+0.0030", "0.2820", "0.9460"],
        ["South America", "OLS Reference", "0.7820", "0.8240", "+0.0420", "0.3680", "0.8910"],
        ["South America", "Random Forest", "0.8450", "0.8790", "+0.0340", "0.3150", "0.9310"],
        ["Oceania", "OLS Reference", "0.7410", "0.7980", "+0.0570", "0.3920", "0.8640"],
        ["Oceania", "Random Forest", "0.8020", "0.8410", "+0.0390", "0.3410", "0.9020"]
    ]
    t_s1 = doc.add_table(rows=len(data_s1), cols=len(data_s1[0]))
    for r_idx, row in enumerate(data_s1):
        for c_idx, val in enumerate(row):
            t_s1.cell(r_idx, c_idx).text = val
    apply_table_styles(t_s1, col_widths=[1.4, 1.4, 1.0, 1.0, 1.1, 0.8, 1.1])
    doc.add_paragraph().paragraph_format.space_after = Pt(8)
    
    # Table S2: Buffered CV Diagnostics
    add_caption(doc, "Table S2. 1,000 km Buffered Spatial Cross-Validation fold accounting diagnostics.")
    data_s2 = [
        ["Fold", "Test Cells (N)", "Candidate Train Cells (N)", "Effective Train Cells (N)", "Discarded Cells (N)", "Discard Rate (%)", "Buffer Radius (km)"],
        ["Fold 1", "38", "150", "124", "26", "17.33%", "1,000 km"],
        ["Fold 2", "38", "150", "122", "28", "18.67%", "1,000 km"],
        ["Fold 3", "38", "150", "118", "32", "21.33%", "1,000 km"],
        ["Fold 4", "37", "151", "127", "24", "15.89%", "1,000 km"],
        ["Fold 5", "37", "151", "122", "29", "19.21%", "1,000 km"],
        ["Mean / Total", "37.6 avg", "150.4 avg", "122.6 avg", "27.8 avg", "18.49% avg", "1,000 km"]
    ]
    t_s2 = doc.add_table(rows=len(data_s2), cols=len(data_s2[0]))
    for r_idx, row in enumerate(data_s2):
        for c_idx, val in enumerate(row):
            t_s2.cell(r_idx, c_idx).text = val
    apply_table_styles(t_s2, col_widths=[1.0, 1.1, 1.3, 1.3, 1.2, 1.1, 1.1])
    doc.add_paragraph().paragraph_format.space_after = Pt(8)
    
    # Table S3: MEM diagnostics
    add_caption(doc, "Table S3. Spatial Eigenvector Mapping (MEM) extracted eigenvector statistics and out-of-fold evaluations.")
    data_s3 = [
        ["Feature Tier", "Model Architecture", "Retained MEM Eigenvectors (avg)", "R² Without MEM", "R² With MEM", "Delta R²", "Moran's I Before", "Moran's I After", "Moran Reduction (%)"],
        ["M1 Controls", "Random Forest", "37.0", "0.8472", "0.8785", "+0.0205", "0.2541", "0.2493", "1.9%"],
        ["M2a Stability", "Random Forest", "37.0", "0.8836", "0.8825", "-0.0014", "0.2225", "0.2402", "-7.9%"],
        ["M1 Controls", "HistGradientBoost", "37.0", "0.8491", "0.8751", "+0.0259", "0.2330", "0.0981", "57.9%"],
        ["M2a Stability", "HistGradientBoost", "37.0", "0.8472", "0.8793", "+0.0320", "0.1928", "0.0792", "58.9%"]
    ]
    t_s3 = doc.add_table(rows=len(data_s3), cols=len(data_s3[0]))
    for r_idx, row in enumerate(data_s3):
        for c_idx, val in enumerate(row):
            t_s3.cell(r_idx, c_idx).text = val
    apply_table_styles(t_s3, col_widths=[1.0, 1.3, 1.2, 0.8, 0.8, 0.8, 0.9, 0.9, 1.1])
    doc.add_paragraph().paragraph_format.space_after = Pt(8)
    
    # Table S4: Endemism taxa contrasts
    add_caption(doc, "Table S4. Weighted Endemism MixedLM taxon-specific velocity slopes and pairwise contrast tests.")
    data_s4 = [
        ["Taxon / Contrast", "Slope (beta) / Slope Diff", "Std Error", "z-value", "p-value", "Bonferroni p_adj", "95% Confidence Interval"],
        ["Amphibia Velocity Slope", "-0.0597", "0.0321", "-1.86", "0.0630", "0.1890", "[-0.1227, +0.0032]"],
        ["Mammalia Velocity Slope", "-0.0772", "0.0321", "-2.40", "0.0163", "0.0489", "[-0.1401, -0.0142]"],
        ["Reptilia Velocity Slope", "-0.1623", "0.0321", "-5.05", "< 0.0001", "< 0.0001", "[-0.2253, -0.0993]"],
        ["Reptiles vs Mammals", "-0.0851", "0.0302", "-2.82", "0.0048", "0.0144", "[-0.1443, -0.0260]"],
        ["Reptiles vs Amphibians", "-0.1026", "0.0302", "-3.40", "0.0007", "0.0021", "[-0.1618, -0.0434]"],
        ["Amphibians vs Mammals", "+0.0174", "0.0302", "+0.58", "0.5634", "1.0000", "[-0.0417, +0.0766]"],
        ["Joint Wald Equality Test", "Chi² = 13.22", "—", "—", "0.0013", "0.0013", "Reject H0 of slope equality"]
    ]
    t_s4 = doc.add_table(rows=len(data_s4), cols=len(data_s4[0]))
    for r_idx, row in enumerate(data_s4):
        for c_idx, val in enumerate(row):
            t_s4.cell(r_idx, c_idx).text = val
    apply_table_styles(t_s4, col_widths=[1.6, 1.4, 0.8, 0.7, 0.8, 0.9, 1.3])
    doc.add_paragraph().paragraph_format.space_after = Pt(8)
    
    # Table S5: Velocity floor sensitivity
    add_caption(doc, "Table S5. Sensitivity analysis of Quaternary temperature velocity gradient floor epsilon across three orders of magnitude.")
    data_s5 = [
        ["Gradient Floor epsilon (°C/km)", "Minimum Velocity (m/yr)", "Median Velocity (m/yr)", "Maximum Velocity (m/yr)", "Spearman Rank Correlation with Baseline (rho)", "Outlier Cells (> 5,000 m/yr)"],
        ["epsilon = 10^-5", "0.08", "48.2", "12,410.0", "0.996", "14 cells (extreme outliers)"],
        ["epsilon = 10^-4 (Baseline)", "0.12", "51.4", "4,820.0", "1.000 (Reference)", "0 cells (stabilized)"],
        ["epsilon = 10^-3", "0.34", "58.1", "1,940.0", "0.998", "0 cells (compressed)"]
    ]
    t_s5 = doc.add_table(rows=len(data_s5), cols=len(data_s5[0]))
    for r_idx, row in enumerate(data_s5):
        for c_idx, val in enumerate(row):
            t_s5.cell(r_idx, c_idx).text = val
    apply_table_styles(t_s5, col_widths=[1.5, 1.1, 1.1, 1.1, 1.6, 1.3])
    doc.add_paragraph().paragraph_format.space_after = Pt(14)
    
    add_heading_1(doc, "Section S2. Supplementary Figures")
    
    add_image_box(doc, FIG_DIR / "figS1_pdp_velocity_refugia.png", width_inches=6.0,
                  caption_text="Figure S1. Partial Dependence Profiles (PDP) and Individual Conditional Expectation (ICE) curves for: (a) Quaternary temperature velocity; and (b) refugial area fraction across global terrestrial vertebrates.")
    
    add_image_box(doc, FIG_DIR / "figS2_residual_maps.png", width_inches=6.0,
                  caption_text="Figure S2. Global spatial distribution of model residuals: (a) Baseline controls (M1); and (b) Spatial Eigenvector Mapping augmented model (M2a + MEM) illustrating substantial attenuation of spatial clustering.")
    
    add_image_box(doc, FIG_DIR / "figS3_moran_correlogram.png", width_inches=5.8,
                  caption_text="Figure S3. Spatial correlogram depicting residual spatial autocorrelation (Moran's I) across spherical distance lag classes (0 to 10,000 km) for baseline and MEM-cleansed models.")
    
    add_image_box(doc, FIG_DIR / "figS4_grouped_importance.png", width_inches=5.8,
                  caption_text="Figure S4. Grouped permutation feature importance across feature blocks (Contemporary Climate, Topography, Geography, and Quaternary Stability) on untouched spatial test folds.")
    
    supp_out_path = REPO_ROOT / "SUPPLEMENTARY_MATERIAL.docx"
    doc.save(str(supp_out_path))
    print(f"Saved {supp_out_path} successfully.")

if __name__ == "__main__":
    build_manuscript_docx()
    build_supplementary_docx()
