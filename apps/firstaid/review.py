"""
Dossier de relecture médicale : rendu PDF d'un protocole dans UNE langue.

Tout le texte affiché vient de Protocol.localized(lang). Les seuls éléments
hors langue sont les en-têtes de contrôle (id, version, statut…) et les
références de page, volontairement identiques dans les deux versions.

Police : DejaVu Sans (accents, guillemets français, case à cocher ☐). Si elle
est absente du système, repli sur Helvetica et case rendue « [ ] ».
"""

from __future__ import annotations

import datetime as _dt
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .schema import LANGS, Protocol

_DEJAVU = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
_DEJAVU_BOLD = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')

# Libellés fixes de l'interface du dossier, par langue (jamais mélangés).
_UI = {
    'fr': {
        'title': 'Dossier de relecture médicale',
        'protocol': 'Protocole', 'version': 'Version', 'updated': 'Mis à jour le',
        'status': 'Statut', 'validated_by': 'Validé par', 'not_validated': 'NON VALIDÉ',
        'emergency': "Numéro d'urgence affiché", 'incomplete': 'SQUELETTE INCOMPLET',
        'call_first': "Appel des secours affiché avant toute consigne",
        'yes': 'oui', 'no': 'non',
        'sources': 'Sources', 'edition': 'édition', 'pages': 'pages citées', 'licence': 'licence',
        'role_content': 'contenu', 'role_terminology': 'terminologie',
        'tree': 'Arbre de décision', 'entry': "Question d'entrée", 'answer': 'Réponse',
        'to_question': 'question', 'to_block': "bloc d'actions", 'to_switch': 'bascule vers le protocole',
        'blocks': "Blocs d'actions", 'variant': 'Variante', 'all_variants': 'Toutes variantes',
        'then': 'Puis question', 'timer': 'minuteur', 'seconds': 's', 'source': 'Source',
        'check': '☐ OK    ☐ À corriger : ______________________________________________',
        'red_flags': "Signes d'alerte (interrompent tout : « appelez les secours maintenant »)",
        'switch_to': 'puis bascule vers', 'do_not': 'Interdits',
        'notes': 'Points à trancher par le médecin', 'no_notes': 'Aucun point en suspens.',
        'footer': "Document généré le {date} depuis {file} version {version} — "
                  "toute correction se fait dans le fichier, jamais dans ce PDF.",
        'page': 'Page',
    },
    'en': {
        'title': 'Medical review file',
        'protocol': 'Protocol', 'version': 'Version', 'updated': 'Updated on',
        'status': 'Status', 'validated_by': 'Validated by', 'not_validated': 'NOT VALIDATED',
        'emergency': 'Emergency number displayed', 'incomplete': 'INCOMPLETE SKELETON',
        'call_first': 'Emergency call displayed before any instruction',
        'yes': 'yes', 'no': 'no',
        'sources': 'Sources', 'edition': 'edition', 'pages': 'cited pages', 'licence': 'licence',
        'role_content': 'content', 'role_terminology': 'terminology',
        'tree': 'Decision tree', 'entry': 'Entry question', 'answer': 'Answer',
        'to_question': 'question', 'to_block': 'action block', 'to_switch': 'switch to protocol',
        'blocks': 'Action blocks', 'variant': 'Variant', 'all_variants': 'All variants',
        'then': 'Then question', 'timer': 'timer', 'seconds': 's', 'source': 'Source',
        'check': '☐ OK    ☐ To correct: ______________________________________________',
        'red_flags': 'Red flags (interrupt everything: "call emergency services now")',
        'switch_to': 'then switch to', 'do_not': 'Do not',
        'notes': 'Points for the reviewing doctor to decide', 'no_notes': 'No open point.',
        'footer': 'Document generated on {date} from {file} version {version} — '
                  'any correction is made in the file, never in this PDF.',
        'page': 'Page',
    },
}

# Libellé court d'une source pour la colonne « page » (identique dans les deux langues).
_SOURCE_SHORT = {
    'ifrc_2025_en': 'IFRC 2025 EN',
    'ifrc_2020_fr': 'IFRC 2020 FR',
}


def _register_fonts() -> tuple[str, str, str]:
    """Retourne (police, police grasse, case à cocher)."""
    if _DEJAVU.exists() and _DEJAVU_BOLD.exists():
        if 'DejaVuSans' not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont('DejaVuSans', str(_DEJAVU)))
            pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', str(_DEJAVU_BOLD)))
        return 'DejaVuSans', 'DejaVuSans-Bold', '☐'
    return 'Helvetica', 'Helvetica-Bold', '[ ]'


def _source_label(sources: list[dict[str, Any]], key: str, page: int) -> str:
    short = _SOURCE_SHORT.get(key)
    if short is None:
        src = next((s for s in sources if s['key'] == key), None)
        short = f"{src['organisation']} {src['edition']}" if src else key
    return f'{short} p.{page}'


def render_protocol_pdf(protocol: Protocol, lang: str, out_path: Path) -> Path:
    """Écrit le PDF de relecture d'un protocole dans une seule langue."""
    if lang not in LANGS:
        raise ValueError(f"langue non supportée : {lang!r}")
    view = protocol.localized(lang)
    ui = _UI[lang]
    font, bold, box = _register_fonts()
    check_line = ui['check'] if box == '☐' else ui['check'].replace('☐', box)

    st_body = ParagraphStyle('body', fontName=font, fontSize=9.5, leading=12.5, alignment=TA_LEFT)
    st_small = ParagraphStyle('small', parent=st_body, fontSize=8, leading=10, textColor=colors.HexColor('#444444'))
    st_check = ParagraphStyle('check', parent=st_body, fontSize=8.5, leading=11, textColor=colors.HexColor('#555555'),
                              leftIndent=8 * mm, spaceAfter=3)
    st_h1 = ParagraphStyle('h1', parent=st_body, fontName=bold, fontSize=15, leading=19, spaceAfter=4)
    st_h2 = ParagraphStyle('h2', parent=st_body, fontName=bold, fontSize=12, leading=15, spaceBefore=10, spaceAfter=4)
    st_h3 = ParagraphStyle('h3', parent=st_body, fontName=bold, fontSize=10.5, leading=13, spaceBefore=6, spaceAfter=2)
    st_step = ParagraphStyle('step', parent=st_body, leftIndent=4 * mm)

    def P(text: str, style: ParagraphStyle = st_body) -> Paragraph:
        return Paragraph(escape(text), style)

    def B(label: str, value: str, style: ParagraphStyle = st_body) -> Paragraph:
        return Paragraph(f'<b>{escape(label)}</b> : {escape(value)}' if lang == 'fr'
                         else f'<b>{escape(label)}</b>: {escape(value)}', style)

    story: list[Any] = []

    # 1. En-tête -------------------------------------------------------------
    story.append(P(ui['title'], st_small))
    story.append(P(view['title'], st_h1))
    if protocol.incomplete:
        story.append(P(ui['incomplete'], ParagraphStyle('warn', parent=st_h3, textColor=colors.red)))
    head_rows = [
        [ui['protocol'], view['id']],
        [ui['version'], str(view['version'])],
        [ui['updated'], view['updated_at']],
        [ui['status'], view['status']],
    ]
    if protocol.validated_by:
        head_rows.append([ui['validated_by'], ' ; '.join(
            f'{v.name}, {v.qualification}, {v.organisation}, {v.date.isoformat()}' for v in protocol.validated_by)])
    else:
        head_rows.append([ui['validated_by'], ui['not_validated']])
    head_rows.append([ui['emergency'], str(settings.EMERGENCY_NUMBER)])
    head_rows.append([ui['call_first'], ui['yes'] if view['call_emergency_first'] else ui['no']])
    table = Table([[P(k, st_small), P(v)] for k, v in head_rows], colWidths=[55 * mm, 115 * mm])
    table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LINEBELOW', (0, 0), (-1, -1), 0.25, colors.HexColor('#cccccc')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3), ('TOPPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(table)
    story.append(Spacer(1, 4))
    story.append(P(view['description']))

    # 2. Sources -------------------------------------------------------------
    story.append(P(ui['sources'], st_h2))
    for s in view['sources']:
        role = ui['role_content'] if s['role'] == 'content' else ui['role_terminology']
        story.append(P(f"[{s['key']}] {s['organisation']} — {s['title']}, {ui['edition']} {s['edition']} ({role})", st_body))
        story.append(P(s['url'], st_small))
        story.append(P(f"{ui['licence']} : {s['licence']}" if lang == 'fr' else f"{ui['licence']}: {s['licence']}", st_small))
        story.append(P(f"{ui['pages']} : {', '.join(map(str, s['pages']))}" if lang == 'fr'
                       else f"{ui['pages']}: {', '.join(map(str, s['pages']))}", st_small))
        story.append(Spacer(1, 3))

    # 3. Arbre de décision ---------------------------------------------------
    tree = view['decision_tree']
    story.append(P(ui['tree'], st_h2))
    story.append(B(ui['entry'], tree['entry'], st_small))
    ordered = [tree['entry']] + [q for q in tree['questions'] if q != tree['entry']]
    for qid in ordered:
        q = tree['questions'][qid]
        block: list[Any] = [P(f"[{qid}] {q['text']}", st_h3)]
        for akey, a in q['answers'].items():
            if a['next_question']:
                target = f"{ui['to_question']} [{a['next_question']}]"
            elif a['action_block']:
                target = f"{ui['to_block']} [{a['action_block']}]"
            else:
                target = f"{ui['to_switch']} [{a['switch_to']}]"
            block.append(P(f"• {ui['answer']} « {a['label']} » ({akey}) → {target}", st_step))
        story.append(KeepTogether(block))

    # 4. Blocs d'action -------------------------------------------------------
    story.append(P(ui['blocks'], st_h2))

    def steps_flow(steps: list[dict[str, Any]]) -> list[Any]:
        flow: list[Any] = []
        for s in steps:
            extra = f"  [{ui['timer']} {s['timer_seconds']} {ui['seconds']}]" if s['timer_seconds'] else ''
            src = _source_label(view['sources'], s['source']['key'], s['source']['page'])
            flow.append(KeepTogether([
                P(f"{s['number']}. {s['text']}{extra}", st_step),
                P(f"{ui['source']} : {src}" if lang == 'fr' else f"{ui['source']}: {src}", st_check),
                P(check_line, st_check),
            ]))
        return flow

    for bid, b in view['action_blocks'].items():
        story.append(P(f"[{bid}] {b['title']}", st_h3))
        if b.get('next_question'):
            story.append(P(f"{ui['then']} [{b['next_question']}]", st_small))
        if 'variants' in b:
            for vname, steps in b['variants'].items():
                label = view['variants'].get(vname, vname)
                story.append(P(f"{ui['variant']} : {label}" if lang == 'fr' else f"{ui['variant']}: {label}",
                               ParagraphStyle('var', parent=st_body, fontName=bold, spaceBefore=4)))
                story.extend(steps_flow(steps))
        else:
            story.append(P(ui['all_variants'], ParagraphStyle('var', parent=st_body, fontName=bold, spaceBefore=4)))
            story.extend(steps_flow(b['steps']))

    # 5. Red flags et interdits -----------------------------------------------
    def flags_flow(title: str, flags: list[dict[str, Any]]) -> None:
        story.append(P(title, st_h2))
        for i, f in enumerate(flags, start=1):
            src = _source_label(view['sources'], f['source']['key'], f['source']['page'])
            text = f"{i}. {f['text']}"
            if f.get('switch_to'):
                text += f"  → {ui['switch_to']} [{f['switch_to']}]"
            story.append(KeepTogether([
                P(text, st_step),
                P(f"{ui['source']} : {src}" if lang == 'fr' else f"{ui['source']}: {src}", st_check),
                P(check_line, st_check),
            ]))

    flags_flow(ui['red_flags'], view['red_flags'])
    flags_flow(ui['do_not'], view['do_not'])

    # 6. Points à trancher ------------------------------------------------------
    story.append(PageBreak())
    story.append(P(ui['notes'], st_h2))
    if view['review_notes']:
        for i, n in enumerate(view['review_notes'], start=1):
            story.append(KeepTogether([P(f"{i}. {n}", st_step), P(check_line, st_check)]))
    else:
        story.append(P(ui['no_notes'], st_body))

    # 7. Pied de page -----------------------------------------------------------
    footer_text = ui['footer'].format(date=_dt.date.today().isoformat(),
                                      file=Path(protocol.file).name, version=protocol.version)

    def on_page(canvas, doc) -> None:
        canvas.saveState()
        canvas.setFont(font, 7.5)
        canvas.setFillColor(colors.HexColor('#555555'))
        width = A4[0] - doc.leftMargin - doc.rightMargin
        # numéro de page sur sa propre ligne, pied de page replié sous la largeur utile
        canvas.drawRightString(A4[0] - doc.rightMargin, 15 * mm, f"{ui['page']} {doc.page}")
        y = 11 * mm
        for line in simpleSplit(footer_text, font, 7.5, width):
            canvas.drawString(doc.leftMargin, y, line)
            y -= 9
        canvas.restoreState()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(out_path), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=24 * mm,
                            title=f"{view['title']} — {ui['title']}", author='Kendeya / apps.firstaid',
                            subject=f"{view['id']} v{view['version']} ({lang})")
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return out_path


def review_filename(protocol: Protocol, lang: str) -> str:
    return f'{protocol.id}_{lang}_v{protocol.version}.pdf'
