from io import BytesIO
from typing import Dict, List

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


GIORNI = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]

# Palette
C_PRIMARY = colors.HexColor("#0F4C5C")
C_ACCENT = colors.HexColor("#1E847F")
C_GOLD = colors.HexColor("#D9A441")
C_REST = colors.HexColor("#1E847F")        # cell R
C_REST_TXT = colors.white
C_WORK_BG = colors.HexColor("#F7F4EE")     # cell vuota
C_SUN_HDR = colors.HexColor("#D9A441")     # colonna domenica
C_OK = colors.HexColor("#1E7F4F")
C_WARN = colors.HexColor("#B8860B")
C_BAD = colors.HexColor("#B23A48")
C_ROW_ALT = colors.HexColor("#F2F7F7")
C_GRID = colors.HexColor("#B8D8D8")


def _summary_table(summary: Dict, col_widths=None):
    data = [["Metrica", "Valore"]]
    for k, v in summary.items():
        data.append([str(k), str(v)])
    t = Table(data, colWidths=col_widths or [200, 320], repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), C_PRIMARY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, C_GRID),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, C_ROW_ALT]),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return t


def _ranking_table(ranking_df: pd.DataFrame, highlight_pos: int = None):
    data = [list(ranking_df.columns)] + ranking_df.astype(object).values.tolist()
    t = Table(data, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), C_PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.4, C_GRID),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, C_ROW_ALT]),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    # Highlight top 3
    if len(data) > 1:
        style.append(("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#FFE9B3")))
        style.append(("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"))
    if len(data) > 2:
        style.append(("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#FFF3CC")))
    if len(data) > 3:
        style.append(("BACKGROUND", (0, 3), (-1, 3), colors.HexColor("#FFF9E0")))
    if highlight_pos and 1 <= highlight_pos <= len(data) - 1:
        style.append(("BOX", (0, highlight_pos), (-1, highlight_pos), 1.5, C_GOLD))
    t.setStyle(TableStyle(style))
    return t


def _pattern_table(pattern):
    header = ["Sett"] + GIORNI
    data = [header]
    for i, row in enumerate(pattern, start=1):
        data.append([f"S{i:02}"] + ["R" if cell else "" for cell in row])

    n_rows = len(data)
    n_cols = len(header)

    col_widths = [22] + [16] * 7
    t = Table(data, colWidths=col_widths, repeatRows=1)

    style = [
        ("BACKGROUND", (0, 0), (-1, 0), C_PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (7, 0), (7, 0), C_SUN_HDR),
        ("BACKGROUND", (0, 1), (0, -1), C_PRIMARY),
        ("TEXTCOLOR", (0, 1), (0, -1), colors.white),
        ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.3, C_GRID),
        ("LEFTPADDING", (0, 0), (-1, -1), 1),
        ("RIGHTPADDING", (0, 0), (-1, -1), 1),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]

    # color R cells (rest=teal) and work cells (light)
    for r in range(1, n_rows):
        for c in range(1, n_cols):
            cell_val = data[r][c]
            if cell_val == "R":
                style.append(("BACKGROUND", (c, r), (c, r), C_REST))
                style.append(("TEXTCOLOR", (c, r), (c, r), C_REST_TXT))
                style.append(("FONTNAME", (c, r), (c, r), "Helvetica-Bold"))
            else:
                # tinge of light bg, slightly different for Sunday
                if c == 7:
                    style.append(("BACKGROUND", (c, r), (c, r), colors.HexColor("#FFF1D6")))
                else:
                    style.append(("BACKGROUND", (c, r), (c, r), C_WORK_BG))

    t.setStyle(TableStyle(style))
    return t


def _coverage_table(result: Dict):
    header = ["Giorno", "Domanda", "In servizio", "Eccedenza", "Copertura %"]
    data = [header]
    for g in GIORNI:
        d = result["demand"][g]
        l = result["al_lavoro"][g]
        e = result["extra"][g]
        cov = round((l / d) * 100, 1) if d else 0.0
        data.append([g, d, l, e, f"{cov}%"])

    t = Table(data, colWidths=[45, 55, 65, 60, 65], repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), C_PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.4, C_GRID),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, C_ROW_ALT]),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    # highlight Sunday row
    style.append(("BACKGROUND", (0, 7), (-1, 7), colors.HexColor("#FFF1D6")))
    style.append(("FONTNAME", (0, 7), (0, 7), "Helvetica-Bold"))

    # color extra column
    for r in range(1, len(data)):
        extra_val = data[r][3]
        if extra_val == 0:
            color = C_OK
        elif extra_val <= 2:
            color = C_WARN
        else:
            color = C_BAD
        style.append(("TEXTCOLOR", (3, r), (3, r), color))
        style.append(("FONTNAME", (3, r), (3, r), "Helvetica-Bold"))

    t.setStyle(TableStyle(style))
    return t


def _stats_table(result: Dict, pos: int):
    rows = [
        ["#", str(pos)],
        ["N (settimane)", str(result["N"])],
        ["K (riposi/sett)", str(result["K"])],
        ["Driver totali", str(result["tot_autisti"])],
        ["Riposi/ciclo (T)", str(result["T"])],
        ["Riposi/anno", f"{result['riposi_anno']:.2f}"],
        ["Delta vs target", f"{result['delta_riposi']:+.2f}"],
        ["Picco eccedenza", str(result["max_extra"])],
        ["Totale eccedenza", str(result["total_extra"])],
        ["Dom base -> eff", f"{result['dom_domenica_base']} -> {result['dom_domenica_eff']}"],
        ["Fattore riserva dom.", f"{result['riserva_factor']:.3f}"],
    ]
    t = Table(rows, colWidths=[110, 90])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), C_ACCENT),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.white),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("BACKGROUND", (1, 0), (1, -1), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.3, C_GRID),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return t


def _solution_header(pos: int, result: Dict, styles):
    data = [[
        Paragraph(
            f"<font color='white' size='13'><b>#{pos}</b></font>",
            styles["bare"],
        ),
        Paragraph(
            f"<font color='white' size='13'><b>N = {result['N']}  &nbsp;  K = {result['K']}</b></font>",
            styles["bare"],
        ),
        Paragraph(
            f"<font color='white' size='10'>Driver: <b>{result['tot_autisti']}</b> &nbsp;&nbsp; "
            f"Picco: <b>{result['max_extra']}</b> &nbsp;&nbsp; "
            f"Totale extra: <b>{result['total_extra']}</b> &nbsp;&nbsp; "
            f"Riposi/anno: <b>{result['riposi_anno']:.2f}</b></font>",
            styles["bare"],
        ),
    ]]
    t = Table(data, colWidths=[30, 110, 380])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), C_GOLD),
                ("BACKGROUND", (1, 0), (-1, 0), C_PRIMARY),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (0, 0), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return t


def build_pdf_report(
    summary: Dict,
    ranking_df: pd.DataFrame,
    results: List[Dict],
    selected_pos: int = 1,
) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        title="Report Rotazione Riposi",
        author="Rotazione Riposi Streamlit",
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="bare", parent=styles["Normal"], leading=14))
    h1 = ParagraphStyle(
        "h1", parent=styles["Title"], textColor=C_PRIMARY, fontSize=22, leading=26
    )
    h2 = ParagraphStyle(
        "h2", parent=styles["Heading2"], textColor=C_PRIMARY, fontSize=14, spaceBefore=8
    )
    sub = ParagraphStyle(
        "sub", parent=styles["Normal"], textColor=C_ACCENT, fontSize=11, leading=14
    )

    story = []

    # Cover
    story.append(Paragraph("Report Rotazione Riposi", h1))
    story.append(Paragraph("Analisi configurazioni CP-SAT e classifica soluzioni", sub))
    story.append(Spacer(1, 14))

    story.append(_summary_table(summary))
    story.append(Spacer(1, 16))

    story.append(Paragraph("Classifica soluzioni", h2))
    story.append(_ranking_table(ranking_df, highlight_pos=selected_pos))

    # One page per solution
    for pos, result in enumerate(results, start=1):
        story.append(PageBreak())
        story.append(_solution_header(pos, result, styles))
        story.append(Spacer(1, 10))

        body_data = [[
            _stats_table(result, pos),
            _coverage_table(result),
            _pattern_table(result["pattern"]),
        ]]
        body = Table(body_data, colWidths=[210, 300, 200])
        body.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )
        story.append(body)

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
