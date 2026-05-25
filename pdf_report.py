from io import BytesIO
from typing import Dict

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _styled_table(data, col_widths=None):
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F4C5C")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#B8D8D8")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F7F7")]),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def build_pdf_report(summary: Dict, ranking_df: pd.DataFrame, top_df: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        title="Report Rotazione Riposi",
        author="Rotazione Riposi Streamlit",
        leftMargin=30,
        rightMargin=30,
        topMargin=28,
        bottomMargin=28,
    )

    styles = getSampleStyleSheet()
    story = []

    title = Paragraph("<b>Report Rotazione Riposi</b>", styles["Title"])
    subtitle = Paragraph(
        "Analisi configurazioni e classifica soluzioni migliori", styles["Heading3"]
    )

    story.append(title)
    story.append(subtitle)
    story.append(Spacer(1, 12))

    summary_data = [["Metrica", "Valore"]]
    for key, value in summary.items():
        summary_data.append([str(key), str(value)])

    story.append(_styled_table(summary_data, col_widths=[190, 320]))
    story.append(Spacer(1, 14))

    story.append(Paragraph("<b>Classifica Top Soluzioni</b>", styles["Heading2"]))
    rank_data = [ranking_df.columns.tolist()] + ranking_df.values.tolist()
    story.append(_styled_table(rank_data))
    story.append(Spacer(1, 14))

    story.append(Paragraph("<b>Dettaglio Pattern Soluzione #1</b>", styles["Heading2"]))
    top_data = [top_df.columns.tolist()] + top_df.values.tolist()
    story.append(_styled_table(top_data))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
