from io import BytesIO
from xml.sax.saxutils import escape

from django.core.files.base import ContentFile
from django.utils import timezone

from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from immo.models import Location


# -----------------------------------------------------------------------------
# PALETTE - inspiration Mali, sobre et professionnelle
# -----------------------------------------------------------------------------
VERT_MALI = colors.HexColor("#0B8F55")
OR_MALI = colors.HexColor("#F2C94C")
ROUGE_MALI = colors.HexColor("#D64545")
BLEU_NUIT = colors.HexColor("#10233F")
BLEU = colors.HexColor("#2563EB")
BLEU_CLAIR = colors.HexColor("#EFF6FF")
VERT_CLAIR = colors.HexColor("#ECFDF5")
OR_CLAIR = colors.HexColor("#FFFBEB")
ROUGE_CLAIR = colors.HexColor("#FEF2F2")
GRIS_TEXTE = colors.HexColor("#334155")
GRIS_MUTED = colors.HexColor("#64748B")
GRIS_BORDURE = colors.HexColor("#DCE5F0")
GRIS_FOND = colors.HexColor("#F8FAFC")
BLANC = colors.white


# -----------------------------------------------------------------------------
# OUTILS DE DONNEES
# -----------------------------------------------------------------------------
def valeur(objet, attribut, valeur_defaut="-"):
    """Retourne un attribut propre sans provoquer d'erreur."""
    if objet is None:
        return valeur_defaut

    resultat = getattr(objet, attribut, None)

    if callable(resultat):
        try:
            resultat = resultat()
        except Exception:
            resultat = None

    if resultat in (None, ""):
        return valeur_defaut

    return resultat


def premiere_valeur(objet, attributs, valeur_defaut="-"):
    """Cherche la première valeur disponible parmi plusieurs noms de champs."""
    for attribut in attributs:
        resultat = valeur(objet, attribut, None)
        if resultat not in (None, "", "-"):
            return resultat
    return valeur_defaut


def texte_pdf(valeur_texte):
    """Protège le texte interprété par ReportLab."""
    if valeur_texte in (None, ""):
        return "-"
    return escape(str(valeur_texte))


def formater_montant(montant):
    try:
        return f"{float(montant):,.0f}".replace(",", " ") + " FCFA"
    except (TypeError, ValueError):
        return "0 FCFA"


def formater_date(date_objet, valeur_defaut="-"):
    if not date_objet:
        return valeur_defaut
    try:
        return date_objet.strftime("%d/%m/%Y")
    except (AttributeError, ValueError):
        return texte_pdf(date_objet)


def nom_complet(personne, valeur_defaut="Non renseigné"):
    nom = str(valeur(personne, "nom", "")).strip()
    prenom = str(valeur(personne, "prenom", "")).strip()
    complet = f"{nom} {prenom}".strip()
    return complet or valeur_defaut


def appeler_methode(objet, nom_methode, valeur_defaut="-"):
    methode = getattr(objet, nom_methode, None)
    if callable(methode):
        try:
            resultat = methode()
            return resultat if resultat not in (None, "") else valeur_defaut
        except Exception:
            return valeur_defaut
    return valeur_defaut


def est_bail_professionnel(unite):
    return str(valeur(unite, "type_unite", "")).upper() == "MAGASIN"


def destination_unite(unite):
    if est_bail_professionnel(unite):
        usage = appeler_methode(
            unite,
            "get_usage_commercial_display",
            "activité professionnelle autorisée",
        )
        return f"Usage professionnel - {usage}"
    return "Usage exclusif d'habitation"


def description_unite(unite):
    type_unite = appeler_methode(unite, "get_type_unite_display", "Unité locative")
    numero = texte_pdf(valeur(unite, "numero", "-"))

    morceaux = [f"{texte_pdf(type_unite)} n° {numero}"]

    if str(valeur(unite, "type_unite", "")).upper() == "APPARTEMENT":
        morceaux.append(
            f"{texte_pdf(valeur(unite, 'nombre_chambres', 0))} chambre(s)"
        )

    toilette = appeler_methode(unite, "get_type_toilette_display", "-")
    if toilette != "-":
        morceaux.append(f"toilette : {texte_pdf(toilette)}")

    return " - ".join(morceaux)


# -----------------------------------------------------------------------------
# OUTILS GRAPHIQUES
# -----------------------------------------------------------------------------
def bandeau_mali(largeur=174 * mm, hauteur=4 * mm):
    dessin = Drawing(largeur, hauteur)
    tiers = largeur / 3
    dessin.add(Rect(0, 0, tiers, hauteur, fillColor=VERT_MALI, strokeColor=None))
    dessin.add(Rect(tiers, 0, tiers, hauteur, fillColor=OR_MALI, strokeColor=None))
    dessin.add(Rect(2 * tiers, 0, tiers, hauteur, fillColor=ROUGE_MALI, strokeColor=None))
    return dessin


def creer_qr_code(contenu, taille=28 * mm):
    widget = QrCodeWidget(contenu)
    bornes = widget.getBounds()
    largeur = bornes[2] - bornes[0]
    hauteur = bornes[3] - bornes[1]

    dessin = Drawing(taille, taille, transform=[taille / largeur, 0, 0, taille / hauteur, 0, 0])
    dessin.add(widget)
    return dessin


def style_tableau_carte(couleur_entete=BLEU_CLAIR):
    return TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), couleur_entete),
        ("BOX", (0, 0), (-1, -1), 0.8, GRIS_BORDURE),
        ("INNERGRID", (0, 0), (-1, -1), 0.45, GRIS_BORDURE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ])


def ajouter_numero_page(canvas, document):
    canvas.saveState()
    largeur_page, _ = A4

    canvas.setStrokeColor(GRIS_BORDURE)
    canvas.setLineWidth(0.5)
    canvas.line(18 * mm, 13 * mm, largeur_page - 18 * mm, 13 * mm)

    canvas.setFillColor(GRIS_MUTED)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(
        18 * mm,
        8.5 * mm,
        "Modèle automatisé de bail - validation juridique recommandée avant signature.",
    )

    canvas.drawRightString(
        largeur_page - 18 * mm,
        8.5 * mm,
        f"Page {canvas.getPageNumber()}",
    )
    canvas.restoreState()


# -----------------------------------------------------------------------------
# GENERATEUR PRINCIPAL
# -----------------------------------------------------------------------------
def generer_contrat_bail_numerique(location, forcer=False):
    """
    Génère un bail moderne adapté au Mali.

    - Appartement / studio : bail d'habitation.
    - Magasin : bail à usage professionnel, avec référence OHADA.
    """
    if not location:
        raise ValueError("La location est introuvable.")

    if not location.pk:
        raise ValueError("La location doit être enregistrée.")

    if not location.locataire_id:
        raise ValueError("Aucun locataire n'est associé au bail.")

    if not location.unite_id:
        raise ValueError("Aucune unité locative n'est associée au bail.")

    if location.contrat_bail_numerique and not forcer:
        return location.contrat_bail_numerique

    agence = location.agence
    batiment = location.batiment
    proprietaire = batiment.proprietaire
    locataire = location.locataire
    unite = location.unite

    professionnel = est_bail_professionnel(unite)
    titre_bail = (
        "CONTRAT DE BAIL A USAGE PROFESSIONNEL"
        if professionnel
        else "CONTRAT DE BAIL D'HABITATION"
    )

    reference_legale = (
        "Acte uniforme OHADA portant sur le droit commercial général - "
        "dispositions relatives au bail à usage professionnel"
        if professionnel
        else "Loi n°2015-036 du 16 juillet 2015 portant protection du consommateur "
        "et Décret n°2016-0482/P-RM du 7 juillet 2016"
    )

    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=14 * mm,
        bottomMargin=20 * mm,
        title=f"{titre_bail} - {location.numero_contrat}",
        author=str(valeur(agence, "nom", "Gestion immobilière")),
        subject="Contrat de bail - Mali",
        creator="Application de gestion immobilière",
    )

    styles = getSampleStyleSheet()

    style_coordonnees = ParagraphStyle(
        "Coordonnees",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.8,
        leading=11,
        textColor=GRIS_MUTED,
    )

    style_titre = ParagraphStyle(
        "TitreContratMali",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=19,
        leading=23,
        alignment=TA_LEFT,
        textColor=BLEU_NUIT,
        spaceAfter=5,
    )

    style_reference = ParagraphStyle(
        "Reference",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=GRIS_MUTED,
    )

    style_numero = ParagraphStyle(
        "Numero",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        alignment=TA_RIGHT,
        textColor=BLEU,
    )

    style_section = ParagraphStyle(
        "SectionMali",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=BLEU_NUIT,
        spaceBefore=8,
        spaceAfter=7,
        keepWithNext=True,
    )

    style_article = ParagraphStyle(
        "ArticleMali",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.1,
        leading=13.6,
        alignment=TA_JUSTIFY,
        textColor=GRIS_TEXTE,
        spaceAfter=7,
    )

    style_texte = ParagraphStyle(
        "TexteMali",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=GRIS_TEXTE,
    )

    style_texte_centre = ParagraphStyle(
        "TexteCentre",
        parent=style_texte,
        alignment=TA_CENTER,
    )

    style_table_header = ParagraphStyle(
        "TableHeaderMali",
        parent=style_texte_centre,
        fontName="Helvetica-Bold",
        textColor=BLANC,
    )

    style_label = ParagraphStyle(
        "LabelMali",
        parent=style_texte,
        fontName="Helvetica-Bold",
        textColor=BLEU_NUIT,
    )

    style_note = ParagraphStyle(
        "NoteMali",
        parent=style_texte,
        fontSize=8,
        leading=11,
        textColor=GRIS_MUTED,
        backColor=GRIS_FOND,
        borderColor=GRIS_BORDURE,
        borderWidth=0.7,
        borderPadding=7,
        spaceBefore=5,
        spaceAfter=5,
    )

    style_signature = ParagraphStyle(
        "SignatureMali",
        parent=style_texte,
        alignment=TA_CENTER,
        fontSize=8.5,
        leading=12,
    )

    elements = []

    # ------------------------------------------------------------------
    # EN-TETE MODERNE
    # ------------------------------------------------------------------
    elements.append(bandeau_mali())
    elements.append(Spacer(1, 5 * mm))

    nom_agence = texte_pdf(valeur(agence, "nom", "Agence immobilière"))
    telephone_agence = texte_pdf(
        premiere_valeur(agence, ["telephone", "phone"], "Non renseigné")
    )
    email_agence = texte_pdf(
        premiere_valeur(agence, ["email", "courriel"], "Non renseigné")
    )
    adresse_agence = texte_pdf(
        premiere_valeur(agence, ["adresse", "siege", "ville"], "Mali")
    )

    bloc_agence = Paragraph(
        f"<b>{nom_agence}</b><br/>"
        f"{adresse_agence}<br/>"
        f"Tél. : {telephone_agence} - Courriel : {email_agence}",
        style_coordonnees,
    )

    contenu_qr = (
        f"Contrat={location.numero_contrat};"
        f"Batiment={valeur(batiment, 'code_batiment', batiment.pk)};"
        f"Unite={valeur(unite, 'numero', '-')};"
        f"Locataire={nom_complet(locataire)};"
        f"Debut={formater_date(location.date_debut)}"
    )

    tableau_entete = Table(
        [
            [
                bloc_agence,
                creer_qr_code(contenu_qr, 25 * mm),
            ]
        ],
        colWidths=[145 * mm, 29 * mm],
    )
    tableau_entete.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ])
    )
    elements.append(tableau_entete)
    elements.append(Spacer(1, 4 * mm))
    elements.append(HRFlowable(width="100%", thickness=1.2, color=BLEU_NUIT))
    elements.append(Spacer(1, 4 * mm))

    tableau_titre = Table(
        [
            [
                Paragraph(titre_bail, style_titre),
                Paragraph(
                    f"N° {texte_pdf(location.numero_contrat)}<br/>"
                    f"Établi le {formater_date(timezone.localdate())}",
                    style_numero,
                ),
            ]
        ],
        colWidths=[125 * mm, 49 * mm],
    )
    tableau_titre.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ])
    )
    elements.append(tableau_titre)
    elements.append(Paragraph(texte_pdf(reference_legale), style_reference))
    elements.append(Spacer(1, 5 * mm))

    # ------------------------------------------------------------------
    # RESUME CONTRACTUEL
    # ------------------------------------------------------------------
    resume = Table(
        [
            [
                Paragraph("Unité", style_table_header),
                Paragraph("Loyer mensuel", style_table_header),
                Paragraph("Caution", style_table_header),
                Paragraph("Prise d'effet", style_table_header),
            ],
            [
                Paragraph(texte_pdf(description_unite(unite)), style_texte_centre),
                Paragraph(formater_montant(location.loyer), style_texte_centre),
                Paragraph(formater_montant(location.caution), style_texte_centre),
                Paragraph(formater_date(location.date_debut), style_texte_centre),
            ],
        ],
        colWidths=[54 * mm, 40 * mm, 40 * mm, 40 * mm],
    )
    resume.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BLEU_NUIT),
            ("TEXTCOLOR", (0, 0), (-1, 0), BLANC),
            ("BACKGROUND", (0, 1), (-1, 1), GRIS_FOND),
            ("BOX", (0, 0), (-1, -1), 0.8, GRIS_BORDURE),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, GRIS_BORDURE),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ])
    )
    elements.append(resume)
    elements.append(Spacer(1, 6 * mm))

    # ------------------------------------------------------------------
    # IDENTIFICATION DES PARTIES
    # ------------------------------------------------------------------
    elements.append(Paragraph("1. Identification des parties", style_section))

    identite_proprietaire = premiere_valeur(
        proprietaire,
        ["nina", "numero_nina", "numero_piece_identite", "piece_identite"],
        "Non renseignée",
    )
    identite_locataire = premiere_valeur(
        locataire,
        ["nina", "numero_nina", "numero_piece_identite", "piece_identite"],
        "Non renseignée",
    )

    telephone_proprietaire = premiere_valeur(
        proprietaire, ["telephone", "phone"], "Non renseigné"
    )
    telephone_locataire = premiere_valeur(
        locataire, ["telephone", "phone"], "Non renseigné"
    )

    parties = [
        [
            Paragraph("<b>BAILLEUR / PROPRIÉTAIRE</b>", style_label),
            Paragraph("<b>PRENEUR / LOCATAIRE</b>", style_label),
        ],
        [
            Paragraph(
                f"<b>{texte_pdf(nom_complet(proprietaire))}</b><br/>"
                f"Téléphone : {texte_pdf(telephone_proprietaire)}<br/>"
                f"Adresse : {texte_pdf(valeur(proprietaire, 'adresse', '-'))}<br/>"
                f"Pièce / NINA : {texte_pdf(identite_proprietaire)}",
                style_texte,
            ),
            Paragraph(
                f"<b>{texte_pdf(nom_complet(locataire))}</b><br/>"
                f"Téléphone : {texte_pdf(telephone_locataire)}<br/>"
                f"Adresse : {texte_pdf(valeur(locataire, 'adresse', '-'))}<br/>"
                f"Pièce / NINA : {texte_pdf(identite_locataire)}",
                style_texte,
            ),
        ],
    ]

    table_parties = Table(parties, colWidths=[87 * mm, 87 * mm])
    table_parties.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), VERT_CLAIR),
            ("BACKGROUND", (1, 0), (1, 0), BLEU_CLAIR),
            ("BOX", (0, 0), (-1, -1), 0.8, GRIS_BORDURE),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, GRIS_BORDURE),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 9),
            ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ])
    )
    elements.append(table_parties)
    elements.append(Spacer(1, 5 * mm))

    # ------------------------------------------------------------------
    # BIEN LOUE
    # ------------------------------------------------------------------
    elements.append(Paragraph("2. Désignation du bien loué", style_section))

    donnees_bien = [
        [Paragraph("<b>Bâtiment</b>", style_texte), Paragraph(texte_pdf(batiment.nom), style_texte)],
        [
            Paragraph("<b>Code bâtiment</b>", style_texte),
            Paragraph(texte_pdf(valeur(batiment, "code_batiment", "-")), style_texte),
        ],
        [
            Paragraph("<b>Adresse complète</b>", style_texte),
            Paragraph(
                texte_pdf(
                    f"{valeur(batiment, 'adresse', '-')} - {valeur(batiment, 'ville', '')}".strip(" -")
                ),
                style_texte,
            ),
        ],
        [Paragraph("<b>Unité</b>", style_texte), Paragraph(texte_pdf(description_unite(unite)), style_texte)],
        [Paragraph("<b>Destination</b>", style_texte), Paragraph(texte_pdf(destination_unite(unite)), style_texte)],
        [
            Paragraph("<b>Description complémentaire</b>", style_texte),
            Paragraph(texte_pdf(valeur(unite, "description", "Aucune")), style_texte),
        ],
    ]

    table_bien = Table(donnees_bien, colWidths=[48 * mm, 126 * mm])
    table_bien.setStyle(style_tableau_carte(BLEU_CLAIR))
    elements.append(table_bien)
    elements.append(Spacer(1, 5 * mm))

    # ------------------------------------------------------------------
    # CONDITIONS FINANCIERES
    # ------------------------------------------------------------------
    elements.append(Paragraph("3. Conditions financières", style_section))

    conditions = [
        [Paragraph("<b>Loyer mensuel</b>", style_texte), Paragraph(formater_montant(location.loyer), style_texte)],
        [
            Paragraph("<b>Modalité de paiement</b>", style_texte),
            Paragraph(
                "Paiement mensuel entre les mains du bailleur ou de son représentant dûment mandaté, contre quittance.",
                style_texte,
            ),
        ],
        [Paragraph("<b>Caution locative</b>", style_texte), Paragraph(formater_montant(location.caution), style_texte)],
        [
            Paragraph("<b>Caution déjà payée</b>", style_texte),
            Paragraph("Oui" if location.caution_payee else "Non", style_texte),
        ],
        [
            Paragraph("<b>Date de paiement de la caution</b>", style_texte),
            Paragraph(formater_date(location.date_caution), style_texte),
        ],
        [
            Paragraph("<b>Observation sur la caution</b>", style_texte),
            Paragraph(texte_pdf(valeur(location, "observation_caution", "Aucune")), style_texte),
        ],
    ]

    table_conditions = Table(conditions, colWidths=[56 * mm, 118 * mm])
    table_conditions.setStyle(style_tableau_carte(VERT_CLAIR))
    elements.append(table_conditions)
    elements.append(Spacer(1, 5 * mm))

    # ------------------------------------------------------------------
    # DUREE
    # ------------------------------------------------------------------
    elements.append(Paragraph("4. Durée du bail", style_section))

    if location.date_fin:
        texte_duree = (
            f"Le présent bail prend effet le <b>{formater_date(location.date_debut)}</b> "
            f"et prend fin le <b>{formater_date(location.date_fin)}</b>, sous réserve des règles "
            "légales relatives au renouvellement, au préavis et à la résiliation."
        )
    else:
        texte_duree = (
            f"Le présent bail prend effet le <b>{formater_date(location.date_debut)}</b> "
            "pour une durée indéterminée. Il peut prendre fin dans les conditions prévues au contrat "
            "et par les textes applicables."
        )

    elements.append(Paragraph(texte_duree, style_article))

    # ------------------------------------------------------------------
    # CLAUSES ET REGLES
    # ------------------------------------------------------------------
    elements.append(Spacer(1, 4 * mm))
    elements.append(HRFlowable(width="100%", thickness=1.0, color=GRIS_BORDURE))
    elements.append(Spacer(1, 4 * mm))
    elements.append(Paragraph("5. Clauses, droits et obligations", style_titre))
    elements.append(
        Paragraph(
            "Les règles ci-dessous complètent les conditions particulières du présent bail.",
            style_reference,
        )
    )
    elements.append(Spacer(1, 4 * mm))

    articles_communs = [
        (
            "Article 1 - Objet et destination",
            (
                f"Le bailleur donne à bail au locataire le bien décrit au présent contrat. "
                f"Le local est destiné à : <b>{texte_pdf(destination_unite(unite))}</b>. "
                "Tout changement de destination doit faire l'objet d'un accord écrit préalable du bailleur "
                "et respecter les autorisations administratives applicables."
            ),
        ),
        (
            "Article 2 - Délivrance et jouissance paisible",
            (
                "Le bailleur remet le local dans un état permettant l'usage convenu, garantit les vices "
                "ou défauts affectant son utilisation et assure au locataire une jouissance paisible pendant "
                "la durée du bail. Le locataire informe rapidement le bailleur de tout vice, sinistre ou "
                "réparation importante nécessitant son intervention."
            ),
        ),
        (
            "Article 3 - Paiement du loyer et quittance",
            (
                f"Le loyer mensuel est fixé à <b>{formater_montant(location.loyer)}</b>. "
                "Il est payé aux échéances convenues au bailleur ou à son représentant dûment mandaté. "
                "Chaque paiement donne lieu à une quittance ou à un reçu permettant d'en établir la preuve."
            ),
        ),
        (
            "Article 4 - Caution locative",
            (
                f"La caution est fixée à <b>{formater_montant(location.caution)}</b>. "
                "Elle ne constitue pas un paiement anticipé des derniers loyers. À la remise des clés en fin "
                "de bail, elle est restituée conformément aux textes applicables, après justification des "
                "sommes restant éventuellement dues et des dégradations imputables au locataire. Tout retard "
                "de restitution non justifié produit les effets prévus par la loi, notamment les intérêts au taux légal."
            ),
        ),
        (
            "Article 5 - Entretien et réparations",
            (
                "Les grosses réparations relevant traditionnellement du bailleur demeurent à sa charge. "
                "Les réparations locatives, l'entretien courant et les petites réparations sont à la charge "
                "du locataire, sauf lorsqu'elles résultent uniquement de la vétusté, d'un vice, d'une "
                "malfaçon ou d'un cas de force majeure."
            ),
        ),
        (
            "Article 6 - Obligations du locataire",
            (
                "Le locataire utilise les lieux avec soin, respecte le voisinage, les règles de sécurité, "
                "d'hygiène et le règlement intérieur éventuel. Il répond des dégradations causées par lui, "
                "les membres de son foyer, ses employés, clients, visiteurs ou toute personne introduite "
                "dans les lieux de son fait."
            ),
        ),
        (
            "Article 7 - Travaux et transformations",
            (
                "Aucun percement important, transformation, construction, changement de façade ou modification "
                "des installations principales ne peut être réalisé sans autorisation écrite préalable du "
                "bailleur et, lorsque nécessaire, des autorités compétentes."
            ),
        ),
        (
            "Article 8 - Sous-location et cession",
            (
                "La sous-location ou la cession du bail est interdite sans l'accord préalable et écrit du "
                "bailleur. Toute autorisation doit identifier le sous-locataire ou le cessionnaire et préciser "
                "les conditions financières convenues. Le locataire initial demeure responsable de ses obligations "
                "tant qu'il n'en est pas valablement libéré."
            ),
        ),
        (
            "Article 9 - État des lieux et remise des clés",
            (
                "Un état des lieux contradictoire est établi et signé lors de la remise des clés. Un état des "
                "lieux de sortie est également établi avant la restitution définitive des clés. Les photographies, "
                "relevés de compteurs et inventaires signés peuvent être annexés au présent contrat."
            ),
        ),
        (
            "Article 10 - Eau, électricité et charges",
            (
                "Sauf accord écrit contraire, les consommations individuelles d'eau, d'électricité, de téléphone, "
                "d'internet et les services personnels du locataire restent à sa charge. Les charges communes "
                "éventuelles doivent être clairement justifiées et réparties selon les modalités convenues."
            ),
        ),
        (
            "Article 11 - Résiliation et règlement des manquements",
            (
                "Tout manquement grave ou répété à une obligation contractuelle peut entraîner une mise en demeure "
                "puis une demande de résiliation selon les formes et délais prévus par les textes applicables. "
                "Aucune clause du présent contrat ne peut autoriser une expulsion de fait en dehors des procédures légales."
            ),
        ),
        (
            "Article 12 - Notifications et règlement des différends",
            (
                "Les notifications importantes sont faites par écrit et par un moyen permettant d'en prouver la "
                "réception. Les parties recherchent d'abord une solution amiable. À défaut, le différend relève de "
                "la juridiction territorialement et matériellement compétente au Mali."
            ),
        ),
    ]

    if professionnel:
        articles_specifiques = [
            (
                "Article 13 - Activité professionnelle",
                (
                    "Le preneur exerce uniquement l'activité indiquée au contrat, respecte les règles d'urbanisme, "
                    "de sécurité, d'hygiène, de voisinage et obtient à ses frais les autorisations, licences ou "
                    "immatriculations nécessaires à son activité."
                ),
            ),
            (
                "Article 14 - Renouvellement et résiliation du bail professionnel",
                (
                    "Le renouvellement, le droit au renouvellement, la révision du loyer et la résiliation sont "
                    "soumis aux dispositions impératives de l'Acte uniforme OHADA portant sur le droit commercial "
                    "général. La résiliation pour violation du bail doit respecter la mise en demeure et les délais "
                    "prévus par les textes applicables."
                ),
            ),
        ]
    else:
        articles_specifiques = [
            (
                "Article 13 - Préavis du locataire",
                (
                    "Le locataire qui souhaite libérer les lieux respecte le préavis prévu par les textes applicables. "
                    "Pour le bail d'habitation visé par le Décret n°2016-0482/P-RM, ce préavis est d'au moins trois mois "
                    "et doit être donné par un écrit laissant une trace certaine de sa réception."
                ),
            ),
            (
                "Article 14 - Reprise ou refus de renouvellement par le bailleur",
                (
                    "Toute reprise des lieux ou tout refus de renouvellement par le bailleur doit respecter les motifs, "
                    "formes et délais légaux applicables, notamment le préavis de six mois dans les cas prévus par le "
                    "Décret n°2016-0482/P-RM."
                ),
            ),
        ]

    for titre, contenu in articles_communs + articles_specifiques:
        elements.append(
            KeepTogether([
                Paragraph(f"<b>{texte_pdf(titre)}</b>", style_article),
                Paragraph(contenu, style_article),
            ])
        )

    # ------------------------------------------------------------------
    # REGLES PRATIQUES EN LISTE
    # ------------------------------------------------------------------
    elements.append(Spacer(1, 3 * mm))

    regles = [
        "Ne pas troubler la tranquillité du voisinage par des nuisances sonores, des activités dangereuses ou illicites.",
        "Maintenir l'unité, les couloirs et les parties communes utilisés dans un état propre et salubre.",
        "Ne pas entreposer de matières dangereuses, explosives ou interdites.",
        "Signaler sans délai les fuites, pannes majeures, risques électriques, incendies ou dommages structurels.",
        "Ne pas changer les serrures principales sans remettre un double au bailleur ou à son mandataire, sauf motif légitime de sécurité.",
        "Respecter les modalités convenues pour les déchets, l'accès, le stationnement et l'utilisation des parties communes.",
    ]

    liste_regles = ListFlowable(
        [
            ListItem(Paragraph(texte_pdf(regle), style_article), leftIndent=12)
            for regle in regles
        ],
        bulletType="bullet",
        start="circle",
        leftIndent=18,
        bulletFontName="Helvetica",
        bulletFontSize=7,
        bulletColor=VERT_MALI,
        spaceAfter=5,
    )
    elements.append(
        KeepTogether([
            Paragraph("Règles pratiques de l'immeuble", style_section),
            liste_regles,
        ])
    )

    # ------------------------------------------------------------------
    # ANNEXES ET SIGNATURES
    # ------------------------------------------------------------------
    elements.append(Spacer(1, 5 * mm))
    elements.append(HRFlowable(width="100%", thickness=1.0, color=GRIS_BORDURE))
    elements.append(Spacer(1, 4 * mm))
    elements.append(Paragraph("Annexes, déclarations et signatures", style_titre))

    annexes = [
        "État des lieux d'entrée signé par les parties.",
        "Copie de la pièce d'identité ou du document NINA des parties, lorsque disponible.",
        "Preuve du paiement de la caution et du premier loyer.",
        "Inventaire des équipements, photographies et relevés des compteurs, le cas échéant.",
        "Règlement intérieur de l'immeuble, lorsqu'il existe.",
    ]

    elements.append(
        ListFlowable(
            [ListItem(Paragraph(texte_pdf(item), style_article), leftIndent=12) for item in annexes],
            bulletType="bullet",
            leftIndent=18,
            bulletColor=BLEU,
        )
    )
    elements.append(Spacer(1, 5 * mm))

    declarations = Paragraph(
        "Les parties déclarent avoir lu le présent contrat, avoir reçu les explications nécessaires, "
        "avoir vérifié les informations qui y figurent et accepter ses clauses sous réserve des dispositions "
        "légales impératives. Le présent document est établi en autant d'exemplaires que de parties, chacune "
        "reconnaissant avoir reçu le sien.",
        style_note,
    )
    elements.append(declarations)
    elements.append(Spacer(1, 8 * mm))

    lieu_signature = texte_pdf(
        premiere_valeur(batiment, ["ville"], premiere_valeur(agence, ["ville"], "Mali"))
    )

    elements.append(
        Paragraph(
            f"Fait à <b>{lieu_signature}</b>, le <b>{formater_date(timezone.localdate())}</b>",
            style_article,
        )
    )
    elements.append(Spacer(1, 5 * mm))

    signatures = [
        [
            Paragraph("<b>LE BAILLEUR / PROPRIÉTAIRE</b>", style_signature),
            Paragraph("<b>LE LOCATAIRE / PRENEUR</b>", style_signature),
        ],
        [
            Paragraph(
                f"Nom : {texte_pdf(nom_complet(proprietaire))}<br/><br/><br/><br/>"
                "Signature précédée de la mention<br/><b>Lu et approuvé</b><br/><br/>"
                "____________________________",
                style_signature,
            ),
            Paragraph(
                f"Nom : {texte_pdf(nom_complet(locataire))}<br/><br/><br/><br/>"
                "Signature précédée de la mention<br/><b>Lu et approuvé</b><br/><br/>"
                "____________________________",
                style_signature,
            ),
        ],
        [
            Paragraph("<b>LE MANDATAIRE / L'AGENCE</b>", style_signature),
            Paragraph("<b>TÉMOIN OU CAUTION (FACULTATIF)</b>", style_signature),
        ],
        [
            Paragraph(
                f"{nom_agence}<br/><br/><br/>Cachet et signature<br/><br/>"
                "____________________________",
                style_signature,
            ),
            Paragraph(
                "Nom : __________________________<br/>"
                "Téléphone : ____________________<br/><br/>"
                "Signature<br/><br/>"
                "____________________________",
                style_signature,
            ),
        ],
    ]

    table_signatures = Table(signatures, colWidths=[87 * mm, 87 * mm])
    table_signatures.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BLEU_CLAIR),
            ("BACKGROUND", (0, 2), (-1, 2), VERT_CLAIR),
            ("BOX", (0, 0), (-1, -1), 0.8, GRIS_BORDURE),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, GRIS_BORDURE),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ])
    )
    elements.append(table_signatures)
    elements.append(Spacer(1, 5 * mm))

    document.build(
        elements,
        onFirstPage=ajouter_numero_page,
        onLaterPages=ajouter_numero_page,
    )

    contenu_pdf = buffer.getvalue()
    buffer.close()

    numero_unite_fichier = str(valeur(unite, "numero", "unite")).replace("/", "-").replace("\\", "-")
    nom_fichier = (
        f"contrat_bail_{location.pk:06d}_"
        f"unite_{numero_unite_fichier}.pdf"
    )

    if forcer and location.contrat_bail_numerique:
        try:
            location.contrat_bail_numerique.delete(save=False)
        except Exception:
            pass

    location.contrat_bail_numerique.save(
        nom_fichier,
        ContentFile(contenu_pdf),
        save=False,
    )

    maintenant = timezone.now()

    Location.objects.filter(pk=location.pk).update(
        contrat_bail_numerique=location.contrat_bail_numerique.name,
        date_generation_contrat=maintenant,
    )

    location.date_generation_contrat = maintenant

    return location.contrat_bail_numerique
