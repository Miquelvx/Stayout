### ======== STAYOUT - Fonctions Generate PDF ======== ### 

# ----------------------------
# IMPORTATIONS DES LIBRAIRIES
# ----------------------------
import os
import io
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.enums import TA_CENTER

# --- Couleurs ---
F1_GREEN = '#09ab3b'
F1_RED   = '#e10600'
F1_DARKRED = '#aa0909'
F1_DARK  = '#15151e'
F1_GREY  = '#38383f'
F1_LIGHT = '#f5f5f5'
WHITE    = '#ffffff'
BLACK    = '#000000'


# --- Styles ---
def base_styles():
    styles = getSampleStyleSheet()

    app_title = ParagraphStyle(
        'AppTitle',
        fontSize=20,
        textColor=F1_DARK,
        fontName='Helvetica-Bold',
        alignment=TA_CENTER,
        spaceAfter=16,
    )
    app_subtitle = ParagraphStyle(
        'AppSubtitle',
        fontSize=10,
        textColor=F1_GREY,
        fontName='Helvetica',
        alignment=TA_CENTER,
        spaceAfter=10,
    )
    doc_title = ParagraphStyle(
        'DocTitle',
        fontSize=14,
        textColor=F1_DARK,
        fontName='Helvetica-Bold',
        alignment=TA_CENTER,
        spaceAfter=6,
    )
    doc_subtitle = ParagraphStyle(
        'DocSubtitle',
        fontSize=10,
        textColor=F1_GREY,
        fontName='Helvetica',
        alignment=TA_CENTER,
        spaceAfter=12,
    )
    title = ParagraphStyle(
        'Title',
        fontSize=12,
        textColor=F1_DARK,
        fontName='Helvetica-Bold',
        spaceAfter=4,
        alignment=TA_CENTER,
    )
    section_title = ParagraphStyle(
        'SectionTitle',
        fontSize=10,
        textColor=F1_DARK,
        fontName='Helvetica-Bold',
        spaceBefore=2,
        spaceAfter=6,
        underlineWidth=1,
        underlineColor=F1_RED,
    )
    body = ParagraphStyle(
        'Body',
        fontSize=8,
        textColor=F1_DARK,
        fontName='Helvetica',
        spaceAfter=2,
        leading=11,
    )
    footer = ParagraphStyle(
        'Footer',
        fontSize=8,
        textColor=F1_GREY,
        fontName='Helvetica',
        alignment=TA_CENTER,
    )

    return {
        'app_title': app_title,
        'app_subtitle': app_subtitle,
        'doc_title': doc_title,
        'doc_subtitle': doc_subtitle,
        'title': title,
        'section_title': section_title,
        'body': body,
        'footer': footer,
    }


# --- Header --- 
def build_header(styles, event_name, round_num, date_event, year, doc_type, logo_path=None):
    story = []

    ## Logo image
    if logo_path and os.path.exists(logo_path):
        logo = RLImage(logo_path, width=5*cm, height=3*cm, kind='proportional')
        logo.hAlign = 'CENTER'
        story.append(logo)
    else:
        story.append(Paragraph("STAYOUT", styles['app_title']))

    ## Titre du document
    story.append(Paragraph(f"{year} {event_name.upper()}", styles['doc_title']))

    ## Calcul date de l'évènement
    date_j2 = date_event - timedelta(days=2)
    date_event = f"{date_j2.day:02d} - {date_event.day:02d} {date_event.month_name().upper()} {date_event.year}"

    story.append(Paragraph(f"{date_event}", styles['doc_subtitle']))

    ## Tableau style F1
    meta_data = [
        [Paragraph("<b>From</b>", inline()), Paragraph("StayOut", inline()),
         Paragraph("<b>Document</b>", inline()), Paragraph(f"Prediction_R{round_num}_{year}", inline())],
        [Paragraph("<b>To</b>", inline()),    Paragraph("All Users", inline()),
         Paragraph("<b>Type</b>", inline()),  Paragraph(doc_type, inline())],
    ]
    meta_table = Table(meta_data, colWidths=[2.5*cm, 7*cm, 3*cm, 5*cm])
    meta_table.setStyle(TableStyle([
        ('FONTSIZE',    (0, 0), (-1, -1), 9),
        ('TEXTCOLOR',   (0, 0), (-1, -1), F1_DARK),
        ('VALIGN',      (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWHEIGHT',   (0, 0), (-1, -1), 16),
        ('LINEBELOW',   (0, -1), (-1, -1), 0.5, F1_GREY),
        ('LINEABOVE',   (0, 0),  (-1, 0),  0.5, F1_GREY),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 0.3*cm))
    return story

def inline():
    return ParagraphStyle('inline', fontSize=9, textColor=F1_DARK, fontName='Helvetica')

# --- Footer ---
def draw_footer(canvas, doc, round_num, year):
    canvas.saveState()
    
    page_width = A4[0]
    footer_y = 1*cm
    
    ## Ligne grise
    canvas.setStrokeColor(F1_GREY)
    canvas.setLineWidth(0.5)
    canvas.line(1.5*cm, footer_y + 0.4*cm, page_width - 1.5*cm, footer_y + 0.4*cm)
    
    ## Texte footer
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(F1_GREY)
    canvas.drawCentredString(
        page_width / 2,
        footer_y,
        f"Stayout - Prediction Report  |  Round {round_num} - {year}  |  Generated {datetime.now().strftime('%d %b %Y - %H:%M')}"
    )
    canvas.restoreState()


# --- Style tableau de données ---
def data_table_style(num_rows=25):
    style = [
        ('BACKGROUND',  (0, 0), (-1, 0),  F1_RED),
        ('TEXTCOLOR',   (0, 0), (-1, 0),  WHITE),
        ('FONTNAME',    (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',    (0, 0), (-1, 0),  9),
        ('ALIGN',       (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',      (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME',    (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE',    (0, 1), (-1, -1), 8),
        ('TEXTCOLOR',   (0, 1), (-1, -1), F1_DARK),
        ('GRID',        (0, 0), (-1, -1), 0.4, F1_GREY),
        ('ROWHEIGHT',   (0, 0), (-1, -1), 16),
        ('TOPPADDING',    (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]
    for i in range(1, num_rows):
        bg = F1_LIGHT if i % 2 == 0 else WHITE
        style.append(('BACKGROUND', (0, i), (-1, i), bg))
    return style


# ================================================================
# PDF 1 — Prédictions avant la course
# ================================================================
def generate_prediction_pdf(results, df_importance, event_name, round_num, date_event, year):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=1.5*cm, leftMargin=1.5*cm, topMargin=0.8*cm, bottomMargin=0.8*cm
    )
    styles = base_styles()
    story = []

    ## Header
    story += build_header(styles, event_name, round_num, date_event, year, "Pre-Race Prediction", logo_path="./assets/Logo_StayoutW.png")

    ## Title 
    story.append(Paragraph("Prediction Report", styles['title']))

    ## Intro 
    story.append(Paragraph("1) Predicted Race Classification", styles['section_title']))
    story.append(Paragraph(
        f"The following classification has been generated by the StayOut ML engine for the {event_name}."
        f"The model was trained on the full 2026 season history, excluding race incidents, "
        f"using qualifying data, team performance, and weather forecasts as input features.",
        styles['body']
    ))
    story.append(Spacer(1, 0.3*cm))

    ## Tableau prédictions
    pred_data = [["Driver", "Starting Grid", "Predicted Pos", "Podium Proba"]]
    for i, (_, row) in enumerate(results.iterrows(), start=1):
        pred_data.append([
            str(row['Driver']),
            str(int(row['qualif_pos'])),
            str(i),
            f"{int(row['Podium_Proba_pct'])} %",
        ])

    pred_table = Table(pred_data, colWidths=[2.5*cm, 3*cm, 3*cm, 3.5*cm])
    ts = data_table_style(len(pred_data))
    ts += [('FONTNAME', (0, 1), (-1, 3), 'Helvetica-Bold')]
    pred_table.setStyle(TableStyle(ts))
    story.append(pred_table)

    story.append(Spacer(1, 0.3*cm))

    ## Graphique Feature Importance
    story.append(Paragraph("2) Features Weight", styles['section_title']))

    story.append(Paragraph(
        "The chart below ranks the input variables by their contribution to the model's decision.",
        styles['body']
    ))

    importance_sorted = df_importance.sort_values('Importance', ascending=False).reset_index(drop=True)

    ## Calcul des pourcentages
    importance_sorted['Importance_pct'] = (importance_sorted['Importance'] / importance_sorted['Importance'].sum() * 100).round(1)

    ## Génération du graphique
    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.bar(
        importance_sorted['Feature'],
        importance_sorted['Importance_pct'],
        color= F1_RED,
        edgecolor='none',
        width=0.6
    )

    ## Valeur % au dessus de chaque barre
    for bar, pct in zip(bars, importance_sorted['Importance_pct']):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.5,
            f"{pct:.1f}%",
            ha='center', va='bottom',
            fontsize=7, fontweight='bold',
            color='#15151e'
        )

    ax.set_xticks(range(len(importance_sorted['Feature'])))
    ax.set_xticklabels(
        importance_sorted['Feature'],
        rotation=20,
        ha='right',
        rotation_mode='anchor',
        fontsize=7
    )
    ax.set_ylabel('Decision Weight (%)', fontsize=8, color=F1_DARK)
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.set_ylim(0, importance_sorted['Importance_pct'].max() * 1.2)
    ax.tick_params(axis='x', labelsize=7, colors='#15151e') 
    ax.tick_params(axis='y', labelsize=7, colors='#38383f')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#38383f')
    ax.spines['bottom'].set_color('#38383f')
    ax.set_facecolor('#f5f5f5')
    fig.patch.set_facecolor('white')
    plt.tight_layout(pad=0.5)

    ## Sauvegarde en mémoire
    img_buffer = io.BytesIO()
    fig.savefig(img_buffer, format='PNG', dpi=150, bbox_inches='tight')
    plt.close(fig)
    img_buffer.seek(0)

    ## Insertion dans le PDF
    fig_w, fig_h = fig.get_size_inches()
    ratio = fig_h / fig_w

    img_width = 11*cm
    img_height = img_width * ratio 

    chart_img = RLImage(img_buffer, width=img_width, height=img_height)
    story.append(chart_img)

    ## Build Document
    doc.build(story,
        onFirstPage=lambda canvas, doc: draw_footer(canvas, doc, round_num, year),
        onLaterPages=lambda canvas, doc: draw_footer(canvas, doc, round_num, year),
    )
    buffer.seek(0)
    return buffer

# ================================================================
# PDF 2 — Comparaison prédiction vs réalité après la course
# ================================================================
def generate_comparison_pdf(df_compare, mae_rank, mae_raw, top1_check, event_name, round_num, date_event, year):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=1.5*cm, leftMargin=1.5*cm, topMargin=0.8*cm, bottomMargin=1.5*cm
    )
    styles = base_styles()
    story = []

    ## Header
    story += build_header(styles, event_name, round_num, date_event, year, "Post-Race Analysis", logo_path="./assets/Logo_StayoutW.png")

    ## Title
    story.append(Paragraph("Prediction Report", styles['title']))

    ## Métriques
    story.append(Paragraph("1) Model Performance Metrics", styles['section_title']))
    story.append(Paragraph(
        f"The StayOut prediction engine has been evaluated against the official {event_name} results. ",
        styles['body']
    ))
    story.append(Spacer(1, 0.3*cm))

    win_status = "CORRECT" if top1_check else "INCORRECT"
    win_color  = F1_GREEN if top1_check else F1_DARKRED

    metrics_data = [
        ["Metric", "Value", "Description"],
        ["MAE Rank",           f"{mae_rank:.2f}",  "Average positional error"],
        ["MAE Raw",            f"{mae_raw:.2f}",   "Raw model score deviation"],
        ["Winner Prediction",  win_status,         "Was the race winner correctly predicted ?"],
    ]
    metrics_table = Table(metrics_data, colWidths=[3.5*cm, 3*cm, 7*cm])
    mts = data_table_style(len(metrics_data))
    mts += [('TEXTCOLOR', (1, 3), (1, 3), win_color),
            ('FONTNAME',  (1, 3), (1, 3), 'Helvetica-Bold')]
    metrics_table.setStyle(TableStyle(mts))
    story.append(metrics_table)

    story.append(Spacer(1, 0.3*cm))

    ## Tableau comparaison
    story.append(Paragraph("2) Prediction vs Reality", styles['section_title']))
    story.append(Paragraph(
        "The table below compares the StayOut predicted finishing order against the official race results. ",
        styles['body']
    ))
    story.append(Spacer(1, 0.3*cm))

    comp_data = [["Driver", "Predicted", "Final", "Gap"]]
    for _, row in df_compare.iterrows():
        diff = int(row['race_finish_pos'] - row['Predicted_Rank'])
        if diff == 0:
            gap_str = "="
        elif diff > 0:
            gap_str = f"+{diff}"
        else:
            gap_str = str(diff)
        comp_data.append([
            str(row['Driver']),
            str(int(row['Predicted_Rank'])),
            str(int(row['race_finish_pos'])),
            gap_str,
        ])

    comp_table = Table(comp_data, colWidths=[3*cm, 3*cm, 3*cm, 3*cm])
    comp_table.setStyle(TableStyle(data_table_style(len(comp_data))))
    story.append(comp_table)

    ## Build Document
    doc.build(story,
        onFirstPage=lambda canvas, doc: draw_footer(canvas, doc, round_num, year),
        onLaterPages=lambda canvas, doc: draw_footer(canvas, doc, round_num, year),
    )
    buffer.seek(0)
    return buffer
