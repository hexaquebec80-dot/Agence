from django.contrib import admin
from .models import (
    Agence,
    Proprietaire,
    Batiment,
    Locataire,
    Location,
    Paiement,
    ChambreLogement,
)
from django.utils.html import format_html

from .models import Batiment, UniteLocative

@admin.register(Agence)
class AgenceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "nom",
        "proprietaire",
    )

    search_fields = (
        "nom",
        "proprietaire__username",
    )


@admin.register(Proprietaire)
class ProprietaireAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "code_client",
        "nom",
        "prenom",
        "telephone",
        "email",
        "resident",
        "agence",
        "date_creation",
    )

    search_fields = (
        "code_client",
        "nom",
        "prenom",
        "telephone",
        "email",
    )

    list_filter = (
        "resident",
        "agence",
        "date_creation",
    )

 
class UniteLocativeInline(admin.StackedInline):
    model = UniteLocative
    extra = 0
    show_change_link = True

    fields = (
        "numero",
        "type_unite",
        "nombre_chambres",
        "type_toilette",
        "prix_mensuel",
        "usage_commercial",
        "statut",
        "actif",
        "description",
    )

    classes = (
        "collapse",
    )


@admin.register(Batiment)
class BatimentAdmin(admin.ModelAdmin):
    list_display = (
        "code_batiment",
        "nom",
        "proprietaire",
        "ville",
        "afficher_appartements",
        "afficher_studios",
        "afficher_magasins",
        "afficher_total_unites",
        "occupation",
        "actif",
    )

    search_fields = (
        "code_batiment",
        "nom",
        "ville",
        "adresse",
        "proprietaire__nom",
        "proprietaire__prenom",
        "unites_locatives__numero",
    )

    list_filter = (
        "ville",
        "actif",
        "unites_locatives__type_unite",
        "unites_locatives__statut",
    )

    # nombre_logements est editable=False dans le modèle.
    # Il doit donc obligatoirement être en lecture seule dans l'admin.
    readonly_fields = (
        "nombre_logements",
        "date_creation",
        "resume_unites",
        "resume_occupation",
    )

    fieldsets = (
        (
            "Identification du bâtiment",
            {
                "fields": (
                    "agence",
                    "proprietaire",
                    "code_batiment",
                    "nom",
                )
            },
        ),
        (
            "Localisation",
            {
                "fields": (
                    "adresse",
                    "ville",
                )
            },
        ),
        (
            "Informations générales",
            {
                "fields": (
                    "nombre_logements",
                    "description",
                    "actif",
                )
            },
        ),
        (
            "Résumé des unités",
            {
                "fields": (
                    "resume_unites",
                    "resume_occupation",
                ),
            },
        ),
        (
            "Informations système",
            {
                "fields": (
                    "date_creation",
                ),
                "classes": (
                    "collapse",
                ),
            },
        ),
    )

    ordering = (
        "nom",
    )

    inlines = (
        UniteLocativeInline,
    )

    list_select_related = (
        "agence",
        "proprietaire",
    )

    @admin.display(
        description="Appartements",
        ordering="nombre_logements",
    )
    def afficher_appartements(self, obj):
        return obj.appartements_total()

    @admin.display(description="Studios")
    def afficher_studios(self, obj):
        return obj.studios_total()

    @admin.display(description="Magasins")
    def afficher_magasins(self, obj):
        return obj.magasins_total()

    @admin.display(description="Total unités")
    def afficher_total_unites(self, obj):
        return obj.unites_total()

    @admin.display(description="Occupation")
    def occupation(self, obj):
        total = obj.unites_total()
        occupees = obj.unites_occupees()

        if total == 0:
            return format_html(
                (
                    '<span style="'
                    'display:inline-block;'
                    'padding:5px 10px;'
                    'border-radius:20px;'
                    'background:#f1f5f9;'
                    'color:#64748b;'
                    'font-weight:700;'
                    '">'
                    "{}"
                    "</span>"
                ),
                "Aucune unité",
            )

        if occupees == 0:
            return format_html(
                (
                    '<span style="'
                    'display:inline-block;'
                    'padding:5px 10px;'
                    'border-radius:20px;'
                    'background:#dcfce7;'
                    'color:#166534;'
                    'font-weight:700;'
                    '">'
                    "Libre (0/{})"
                    "</span>"
                ),
                total,
            )

        if occupees == total:
            return format_html(
                (
                    '<span style="'
                    'display:inline-block;'
                    'padding:5px 10px;'
                    'border-radius:20px;'
                    'background:#fee2e2;'
                    'color:#991b1b;'
                    'font-weight:700;'
                    '">'
                    "Tout occupé ({}/{})"
                    "</span>"
                ),
                occupees,
                total,
            )

        return format_html(
            (
                '<span style="'
                'display:inline-block;'
                'padding:5px 10px;'
                'border-radius:20px;'
                'background:#fef3c7;'
                'color:#92400e;'
                'font-weight:700;'
                '">'
                "Partiellement occupé ({}/{})"
                "</span>"
            ),
            occupees,
            total,
        )

    @admin.display(description="Résumé des unités")
    def resume_unites(self, obj):
        if not obj or not obj.pk:
            return "Enregistrez d’abord le bâtiment."

        appartements = obj.appartements_total()
        studios = obj.studios_total()
        magasins = obj.magasins_total()
        chambres = obj.chambres_total()
        total = obj.unites_total()

        return format_html(
            """
            <div style="
                display:grid;
                grid-template-columns:repeat(auto-fit, minmax(150px, 1fr));
                gap:12px;
                margin-top:8px;
            ">
                <div style="
                    padding:15px;
                    border-radius:12px;
                    background:#eff6ff;
                    border:1px solid #bfdbfe;
                ">
                    <strong style="display:block;color:#1e3a8a;">
                        Appartements
                    </strong>
                    <span style="font-size:24px;font-weight:800;">
                        {}
                    </span>
                </div>

                <div style="
                    padding:15px;
                    border-radius:12px;
                    background:#f5f3ff;
                    border:1px solid #ddd6fe;
                ">
                    <strong style="display:block;color:#6d28d9;">
                        Studios
                    </strong>
                    <span style="font-size:24px;font-weight:800;">
                        {}
                    </span>
                </div>

                <div style="
                    padding:15px;
                    border-radius:12px;
                    background:#fff7ed;
                    border:1px solid #fed7aa;
                ">
                    <strong style="display:block;color:#c2410c;">
                        Magasins
                    </strong>
                    <span style="font-size:24px;font-weight:800;">
                        {}
                    </span>
                </div>

                <div style="
                    padding:15px;
                    border-radius:12px;
                    background:#f8fafc;
                    border:1px solid #e2e8f0;
                ">
                    <strong style="display:block;color:#334155;">
                        Chambres
                    </strong>
                    <span style="font-size:24px;font-weight:800;">
                        {}
                    </span>
                </div>

                <div style="
                    padding:15px;
                    border-radius:12px;
                    background:#ecfdf5;
                    border:1px solid #a7f3d0;
                ">
                    <strong style="display:block;color:#047857;">
                        Total des unités
                    </strong>
                    <span style="font-size:24px;font-weight:800;">
                        {}
                    </span>
                </div>
            </div>
            """,
            appartements,
            studios,
            magasins,
            chambres,
            total,
        )

    @admin.display(description="Résumé de l’occupation")
    def resume_occupation(self, obj):
        if not obj or not obj.pk:
            return "Enregistrez d’abord le bâtiment."

        total = obj.unites_total()
        occupees = obj.unites_occupees()
        libres = obj.unites_libres()
        reservees = obj.unites_reservees()
        maintenance = obj.unites_en_maintenance()

        taux = round(
            (occupees / total) * 100
        ) if total else 0

        return format_html(
            """
            <div style="
                max-width:750px;
                padding:18px;
                border-radius:14px;
                background:#ffffff;
                border:1px solid #e2e8f0;
            ">
                <div style="
                    display:flex;
                    justify-content:space-between;
                    gap:15px;
                    margin-bottom:10px;
                ">
                    <strong>Occupation du bâtiment</strong>
                    <strong>{}%</strong>
                </div>

                <div style="
                    height:12px;
                    overflow:hidden;
                    border-radius:20px;
                    background:#e2e8f0;
                    margin-bottom:15px;
                ">
                    <div style="
                        width:{}%;
                        height:100%;
                        border-radius:20px;
                        background:#2563eb;
                    "></div>
                </div>

                <div style="
                    display:flex;
                    flex-wrap:wrap;
                    gap:10px;
                ">
                    <span style="
                        padding:6px 10px;
                        border-radius:20px;
                        background:#fee2e2;
                        color:#991b1b;
                        font-weight:700;
                    ">
                        Occupées : {}
                    </span>

                    <span style="
                        padding:6px 10px;
                        border-radius:20px;
                        background:#dcfce7;
                        color:#166534;
                        font-weight:700;
                    ">
                        Libres : {}
                    </span>

                    <span style="
                        padding:6px 10px;
                        border-radius:20px;
                        background:#fef3c7;
                        color:#92400e;
                        font-weight:700;
                    ">
                        Réservées : {}
                    </span>

                    <span style="
                        padding:6px 10px;
                        border-radius:20px;
                        background:#e2e8f0;
                        color:#334155;
                        font-weight:700;
                    ">
                        Maintenance : {}
                    </span>
                </div>
            </div>
            """,
            taux,
            taux,
            occupees,
            libres,
            reservees,
            maintenance,
        )


@admin.register(UniteLocative)
class UniteLocativeAdmin(admin.ModelAdmin):
    list_display = (
        "numero",
        "batiment",
        "type_unite",
        "afficher_details",
        "afficher_prix",
        "usage_commercial",
        "statut_colore",
        "actif",
    )

    search_fields = (
        "numero",
        "batiment__code_batiment",
        "batiment__nom",
        "batiment__proprietaire__nom",
        "batiment__proprietaire__prenom",
        "description",
    )

    list_filter = (
        "type_unite",
        "statut",
        "type_toilette",
        "usage_commercial",
        "actif",
        "batiment__ville",
    )

    readonly_fields = (
        "date_creation",
    )

    ordering = (
        "batiment",
        "type_unite",
        "numero",
    )

    list_select_related = (
        "batiment",
        "batiment__proprietaire",
    )

    autocomplete_fields = (
        "batiment",
    )

    fieldsets = (
        (
            "Unité locative",
            {
                "fields": (
                    "batiment",
                    "numero",
                    "type_unite",
                )
            },
        ),
        (
            "Caractéristiques",
            {
                "fields": (
                    "nombre_chambres",
                    "type_toilette",
                    "usage_commercial",
                )
            },
        ),
        (
            "Location",
            {
                "fields": (
                    "prix_mensuel",
                    "statut",
                    "actif",
                )
            },
        ),
        (
            "Informations supplémentaires",
            {
                "fields": (
                    "description",
                    "date_creation",
                )
            },
        ),
    )

    @admin.display(description="Caractéristiques")
    def afficher_details(self, obj):
        if obj.type_unite == UniteLocative.TypeUnite.APPARTEMENT:
            return (
                f"{obj.nombre_chambres} chambre(s) — "
                f"{obj.get_type_toilette_display()}"
            )

        return obj.get_type_toilette_display()

    @admin.display(
        description="Loyer mensuel",
        ordering="prix_mensuel",
    )
    def afficher_prix(self, obj):
        prix = f"{obj.prix_mensuel:,.0f}".replace(",", " ")

        return f"{prix} FCFA"

    @admin.display(description="Statut")
    def statut_colore(self, obj):
        configurations = {
            UniteLocative.Statut.LIBRE: (
                "#dcfce7",
                "#166534",
                "Libre",
            ),
            UniteLocative.Statut.OCCUPE: (
                "#fee2e2",
                "#991b1b",
                "Occupé",
            ),
            UniteLocative.Statut.RESERVE: (
                "#fef3c7",
                "#92400e",
                "Réservé",
            ),
            UniteLocative.Statut.MAINTENANCE: (
                "#e2e8f0",
                "#334155",
                "Maintenance",
            ),
        }

        fond, texte, libelle = configurations.get(
            obj.statut,
            (
                "#f1f5f9",
                "#475569",
                obj.get_statut_display(),
            ),
        )

        return format_html(
            '<span style="'
            'display:inline-block;'
            'padding:5px 10px;'
            'border-radius:20px;'
            'background:{};'
            'color:{};'
            'font-weight:700;'
            '">'
            "{}"
            "</span>",
            fond,
            texte,
            libelle,
        )


@admin.register(ChambreLogement)
class ChambreLogementAdmin(admin.ModelAdmin):

    list_display = (
        "numero",
        "nom",
        "batiment",
        "locataire_actuel",
        "statut",
        "actif",
    )

    search_fields = (
        "numero",
        "nom",
        "batiment__nom",
        "batiment__code_batiment",
    )

    list_filter = (
        "actif",
        "batiment",
    )

    readonly_fields = (
        "date_creation",
    )

    ordering = (
        "batiment",
        "numero",
    )

    def statut(self, obj):
        if obj.est_occupee():
            return "Occupée"
        return "Libre"

    statut.short_description = "Statut"

    def locataire_actuel(self, obj):
        locataire = obj.locataire_actif()

        if locataire:
            return f"{locataire.nom} {locataire.prenom}"

        return "-"

    locataire_actuel.short_description = "Locataire"


@admin.register(Locataire)
class LocataireAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "nom",
        "telephone",
        "email",
        "agence",
    )

    search_fields = (
        "nom",
        "telephone",
        "email",
    )

    list_filter = (
        "agence",
    )


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "locataire",
        "batiment",
        "numero_appartement",
        "loyer",
        "date_debut",
        "active",
        "agence",
    )

    search_fields = (
        "locataire__nom",
        "batiment__nom",
        "numero_appartement",
    )

    list_filter = (
        "active",
        "batiment",
        "agence",
    )

@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):

    list_display = (
        "numero_recu",
        "location",
        "montant",
        "mois",
        "mode_paiement",
        "statut",
        "employe",
        "date_paiement",
        "agence",
    )

    search_fields = (
        "numero_recu",
        "location__locataire__nom",
        "location__batiment__nom",
        "employe__nom",
    )

    list_filter = (
        "statut",
        "mode_paiement",
        "mois",
        "agence",
        "date_paiement",
    )

    list_editable = (
        "statut",
    )

    readonly_fields = (
        "date_paiement",
    )

    date_hierarchy = "date_paiement"

    list_per_page = 25


admin.site.site_header = "HexaQuébec Immobilier"
admin.site.site_title = "Administration Hexa Immo"
admin.site.index_title = "Gestion immobilière"


from django.contrib import admin
from .models import Employe


@admin.register(Employe)
class EmployeAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "nom",
        "prenom",
        "type_employe",
        "telephone",
        "ville",
        "salaire",
        "agence",
        "date_creation",
    )

    search_fields = (
        "nom",
        "prenom",
        "telephone",
        "ville",
        "nationalite",
        "utilisateur__username",
    )

    list_filter = (
        "type_employe",
        "ville",
        "nationalite",
        "agence",
        "date_creation",
    )

    readonly_fields = (
        "date_creation",
    )

    fieldsets = (

        ("Compte utilisateur", {
            "fields": (
                "utilisateur",
                "agence",
                "type_employe",
            )
        }),

        ("Informations personnelles", {
            "fields": (
                "nom",
                "prenom",
                "telephone",
                "adresse",
                "ville",
                "nationalite",
            )
        }),

        ("Informations professionnelles", {
            "fields": (
                "numero_poste",
                "salaire",
            )
        }),

        ("Documents", {
            "fields": (
                "acte_naissance",
            )
        }),

        ("Système", {
            "fields": (
                "date_creation",
            )
        }),

    )





from django.contrib import admin
from django.utils.html import format_html

from .models import Construction, EtatConstruction


# =========================================================
# INLINE : TRANCHES DE CONSTRUCTION
# =========================================================

class EtatConstructionInline(admin.TabularInline):
    model = EtatConstruction
    extra = 0

    fields = (
        "nom",
        "budget_prevu",
        "montant_depense",
        "afficher_reste",
        "statut",
        "date_debut",
        "date_fin",
    )

    readonly_fields = (
        "afficher_reste",
    )

    show_change_link = True

    def afficher_reste(self, obj):
        if not obj or not obj.pk:
            return "-"

        reste = obj.reste()

        if reste < 0:
            return format_html(
                '<strong style="color:{};">{} $</strong>',
                "#dc2626",
                f"{reste:,.2f}"
            )

        return format_html(
            '<strong style="color:{};">{} $</strong>',
            "#15803d",
            f"{reste:,.2f}"
        )

    afficher_reste.short_description = "Reste"


# =========================================================
# ADMIN CONSTRUCTION
# =========================================================

@admin.register(Construction)
class ConstructionAdmin(admin.ModelAdmin):

    list_display = (
        "nom",
        "agence",
        "batiment",
        "afficher_budget_total",
        "afficher_total_depense",
        "afficher_reste_budget",
        "nombre_tranches",
        "afficher_statut",
        "date_debut",
        "date_fin_prevue",
    )

    list_filter = (
        "actif",
        "agence",
        "date_debut",
        "date_fin_prevue",
        "date_creation",
    )

    search_fields = (
        "nom",
        "description",
        "agence__nom",
        "batiment__nom",
        "batiment__code_batiment",
    )

    ordering = (
        "-date_creation",
    )

    list_per_page = 25

    date_hierarchy = "date_creation"

    readonly_fields = (
        "date_creation",
        "afficher_total_depense_detail",
        "afficher_reste_budget_detail",
        "afficher_nombre_tranches_detail",
    )

    inlines = [
        EtatConstructionInline
    ]

    fieldsets = (

        (
            "Informations principales",
            {
                "fields": (
                    "agence",
                    "nom",
                    "batiment",
                    "description",
                    "actif",
                )
            }
        ),

        (
            "Gestion financière",
            {
                "fields": (
                    "budget_total",
                    "afficher_total_depense_detail",
                    "afficher_reste_budget_detail",
                    "afficher_nombre_tranches_detail",
                )
            }
        ),

        (
            "Planification",
            {
                "fields": (
                    "date_debut",
                    "date_fin_prevue",
                )
            }
        ),

        (
            "Informations système",
            {
                "fields": (
                    "date_creation",
                ),
                "classes": (
                    "collapse",
                )
            }
        ),

    )

    # =====================================================
    # BUDGET TOTAL
    # =====================================================

    def afficher_budget_total(self, obj):
        return format_html(
            '<strong style="color:{};">{} $</strong>',
            "#071a3d",
            f"{obj.budget_total:,.2f}"
        )

    afficher_budget_total.short_description = "Budget total"
    afficher_budget_total.admin_order_field = "budget_total"


    # =====================================================
    # TOTAL DÉPENSÉ
    # =====================================================

    def afficher_total_depense(self, obj):
        total = obj.total_depense()

        return format_html(
            '<strong style="color:{};">{} $</strong>',
            "#0057ff",
            f"{total:,.2f}"
        )

    afficher_total_depense.short_description = "Total dépensé"


    # =====================================================
    # BUDGET RESTANT
    # =====================================================

    def afficher_reste_budget(self, obj):
        reste = obj.reste_budget()

        if reste < 0:
            return format_html(
                '<strong style="color:{};">{} $</strong>',
                "#dc2626",
                f"{reste:,.2f}"
            )

        return format_html(
            '<strong style="color:{};">{} $</strong>',
            "#15803d",
            f"{reste:,.2f}"
        )

    afficher_reste_budget.short_description = "Budget restant"


    # =====================================================
    # NOMBRE DE TRANCHES
    # =====================================================

    def nombre_tranches(self, obj):
        nombre = obj.etapes.count()

        return format_html(
            '<span style="'
            'background:{};'
            'color:{};'
            'padding:5px 10px;'
            'border-radius:20px;'
            'font-weight:700;'
            '">'
            '{}'
            '</span>',
            "#eaf1ff",
            "#0057ff",
            nombre
        )

    nombre_tranches.short_description = "Tranches"


    # =====================================================
    # STATUT CONSTRUCTION
    # =====================================================

    def afficher_statut(self, obj):

        if obj.actif:
            return format_html(
                '<span style="'
                'background:{};'
                'color:{};'
                'padding:6px 10px;'
                'border-radius:20px;'
                'font-weight:700;'
                'display:inline-block;'
                '">'
                '{}'
                '</span>',
                "#dcfce7",
                "#15803d",
                "Actif"
            )

        return format_html(
            '<span style="'
            'background:{};'
            'color:{};'
            'padding:6px 10px;'
            'border-radius:20px;'
            'font-weight:700;'
            'display:inline-block;'
            '">'
            '{}'
            '</span>',
            "#fee2e2",
            "#b91c1c",
            "Inactif"
        )

    afficher_statut.short_description = "État"


    # =====================================================
    # TOTAL DÉPENSÉ DETAIL
    # =====================================================

    def afficher_total_depense_detail(self, obj):

        if not obj or not obj.pk:
            return "0.00 $"

        total = obj.total_depense()

        return format_html(
            '<div style="'
            'padding:12px 15px;'
            'background:{};'
            'border-radius:10px;'
            'color:{};'
            'font-weight:800;'
            'font-size:16px;'
            '">'
            '{} $'
            '</div>',
            "#eaf1ff",
            "#0057ff",
            f"{total:,.2f}"
        )

    afficher_total_depense_detail.short_description = "Total dépensé"


    # =====================================================
    # BUDGET RESTANT DETAIL
    # =====================================================

    def afficher_reste_budget_detail(self, obj):

        if not obj or not obj.pk:
            return "0.00 $"

        reste = obj.reste_budget()

        if reste < 0:
            fond = "#fee2e2"
            couleur = "#b91c1c"
        else:
            fond = "#dcfce7"
            couleur = "#15803d"

        return format_html(
            '<div style="'
            'padding:12px 15px;'
            'background:{};'
            'border-radius:10px;'
            'color:{};'
            'font-weight:800;'
            'font-size:16px;'
            '">'
            '{} $'
            '</div>',
            fond,
            couleur,
            f"{reste:,.2f}"
        )

    afficher_reste_budget_detail.short_description = "Budget restant"


    # =====================================================
    # NOMBRE DE TRANCHES DETAIL
    # =====================================================

    def afficher_nombre_tranches_detail(self, obj):

        if not obj or not obj.pk:
            return "0 tranche"

        nombre = obj.etapes.count()

        return format_html(
            '<div style="'
            'padding:12px 15px;'
            'background:{};'
            'border:1px solid {};'
            'border-radius:10px;'
            'font-weight:800;'
            'color:{};'
            '">'
            '{} tranche(s)'
            '</div>',
            "#f8faff",
            "#e8edf6",
            "#071a3d",
            nombre
        )

    afficher_nombre_tranches_detail.short_description = "Nombre de tranches"


# =========================================================
# ADMIN ÉTAT / TRANCHE DE CONSTRUCTION
# =========================================================

@admin.register(EtatConstruction)
class EtatConstructionAdmin(admin.ModelAdmin):

    list_display = (
        "nom",
        "construction",
        "afficher_budget_prevu",
        "afficher_montant_depense",
        "afficher_reste",
        "afficher_statut",
        "date_debut",
        "date_fin",
    )

    list_filter = (
        "statut",
        "construction__agence",
        "date_debut",
        "date_fin",
    )

    search_fields = (
        "nom",
        "description",
        "construction__nom",
        "construction__agence__nom",
    )

    ordering = (
        "construction",
        "date_debut",
        "id",
    )

    list_per_page = 30

    fieldsets = (

        (
            "Tranche de construction",
            {
                "fields": (
                    "construction",
                    "nom",
                    "description",
                    "statut",
                )
            }
        ),

        (
            "Gestion financière",
            {
                "fields": (
                    "budget_prevu",
                    "montant_depense",
                )
            }
        ),

        (
            "Planification",
            {
                "fields": (
                    "date_debut",
                    "date_fin",
                )
            }
        ),

    )

    # =====================================================
    # BUDGET PRÉVU
    # =====================================================

    def afficher_budget_prevu(self, obj):

        return format_html(
            '<strong style="color:{};">{} $</strong>',
            "#071a3d",
            f"{obj.budget_prevu:,.2f}"
        )

    afficher_budget_prevu.short_description = "Budget prévu"
    afficher_budget_prevu.admin_order_field = "budget_prevu"


    # =====================================================
    # MONTANT DÉPENSÉ
    # =====================================================

    def afficher_montant_depense(self, obj):

        return format_html(
            '<strong style="color:{};">{} $</strong>',
            "#0057ff",
            f"{obj.montant_depense:,.2f}"
        )

    afficher_montant_depense.short_description = "Dépensé"
    afficher_montant_depense.admin_order_field = "montant_depense"


    # =====================================================
    # RESTE
    # =====================================================

    def afficher_reste(self, obj):

        reste = obj.reste()

        if reste < 0:
            return format_html(
                '<strong style="color:{};">{} $</strong>',
                "#dc2626",
                f"{reste:,.2f}"
            )

        return format_html(
            '<strong style="color:{};">{} $</strong>',
            "#15803d",
            f"{reste:,.2f}"
        )

    afficher_reste.short_description = "Reste"


    # =====================================================
    # STATUT TRANCHE
    # =====================================================

    def afficher_statut(self, obj):

        styles = {
            "attente": (
                "#fef3c7",
                "#92400e",
                "En attente"
            ),

            "cours": (
                "#dbeafe",
                "#1d4ed8",
                "En cours"
            ),

            "termine": (
                "#dcfce7",
                "#15803d",
                "Terminé"
            ),

            "bloque": (
                "#fee2e2",
                "#b91c1c",
                "Bloqué"
            ),
        }

        fond, couleur, texte = styles.get(
            obj.statut,
            (
                "#f1f5f9",
                "#475569",
                obj.get_statut_display()
            )
        )

        return format_html(
            '<span style="'
            'background:{};'
            'color:{};'
            'padding:6px 10px;'
            'border-radius:20px;'
            'font-weight:700;'
            'display:inline-block;'
            '">'
            '{}'
            '</span>',
            fond,
            couleur,
            texte
        )

    afficher_statut.short_description = "Statut"





    from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Terrain,
    Depense,
    CentreCommercial,
    LocalCommercial,
    OccupantCommercial,
    ContratCommercial,
)


# =========================================================
# TERRAIN
# =========================================================
@admin.register(Terrain)
class TerrainAdmin(admin.ModelAdmin):

    list_display = (
        "titre",
        "agence",
        "proprietaire",
        "type_operation",
        "statut",
        "qualite",
        "ville",
        "superficie",
        "prix",
        "document_disponible",
        "actif",
        "date_creation",
    )

    list_filter = (
        "type_operation",
        "statut",
        "qualite",
        "pays",
        "ville",
        "document_disponible",
        "actif",
        "date_creation",
    )

    search_fields = (
        "titre",
        "ville",
        "quartier",
        "adresse",
        "description",
        "agence__nom",
        "proprietaire__nom",
        "proprietaire__prenom",
    )

    raw_id_fields = (
        "agence",
        "proprietaire",
    )

    readonly_fields = (
        "date_creation",
    )

    fieldsets = (
        (
            "Informations principales",
            {
                "fields": (
                    "agence",
                    "proprietaire",
                    "titre",
                    "type_operation",
                    "statut",
                    "qualite",
                )
            },
        ),
        (
            "Localisation",
            {
                "fields": (
                    "pays",
                    "ville",
                    "quartier",
                    "adresse",
                )
            },
        ),
        (
            "Informations financières et techniques",
            {
                "fields": (
                    "superficie",
                    "prix",
                    "document_disponible",
                )
            },
        ),
        (
            "Description",
            {
                "fields": (
                    "description",
                )
            },
        ),
        (
            "Administration",
            {
                "fields": (
                    "actif",
                    "date_creation",
                )
            },
        ),
    )

    actions = (
        "activer_terrains",
        "desactiver_terrains",
        "marquer_libres",
        "marquer_reserves",
        "marquer_vendus",
    )

    date_hierarchy = "date_creation"
    list_per_page = 30
    save_on_top = True
    list_select_related = (
        "agence",
        "proprietaire",
    )

    @admin.action(description="Activer les terrains sélectionnés")
    def activer_terrains(self, request, queryset):
        nombre = queryset.update(actif=True)

        self.message_user(
            request,
            f"{nombre} terrain(s) activé(s)."
        )

    @admin.action(description="Désactiver les terrains sélectionnés")
    def desactiver_terrains(self, request, queryset):
        nombre = queryset.update(actif=False)

        self.message_user(
            request,
            f"{nombre} terrain(s) désactivé(s)."
        )

    @admin.action(description="Marquer comme libres")
    def marquer_libres(self, request, queryset):
        nombre = queryset.update(statut="libre")

        self.message_user(
            request,
            f"{nombre} terrain(s) marqué(s) comme libre(s)."
        )

    @admin.action(description="Marquer comme réservés")
    def marquer_reserves(self, request, queryset):
        nombre = queryset.update(statut="reserve")

        self.message_user(
            request,
            f"{nombre} terrain(s) marqué(s) comme réservé(s)."
        )

    @admin.action(description="Marquer comme vendus")
    def marquer_vendus(self, request, queryset):
        nombre = queryset.update(statut="vendu")

        self.message_user(
            request,
            f"{nombre} terrain(s) marqué(s) comme vendu(s)."
        )


# =========================================================
# DÉPENSE
# =========================================================
@admin.register(Depense)
class DepenseAdmin(admin.ModelAdmin):

    list_display = (
        "titre",
        "type_depense",
        "categorie",
        "agence",
        "proprietaire",
        "montant",
        "date_depense",
        "ajoute_par",
        "justificatif_disponible",
        "date_creation",
    )

    list_filter = (
        "type_depense",
        "categorie",
        "agence",
        "date_depense",
        "date_creation",
    )

    search_fields = (
        "titre",
        "description",
        "ajoute_par",
        "agence__nom",
        "proprietaire__nom",
        "proprietaire__prenom",
    )

    raw_id_fields = (
        "agence",
        "proprietaire",
    )

    readonly_fields = (
        "date_creation",
        "lien_justificatif",
    )

    fieldsets = (
        (
            "Identification de la dépense",
            {
                "fields": (
                    "agence",
                    "type_depense",
                    "proprietaire",
                    "categorie",
                    "titre",
                )
            },
        ),
        (
            "Montant et date",
            {
                "fields": (
                    "montant",
                    "date_depense",
                )
            },
        ),
        (
            "Informations complémentaires",
            {
                "fields": (
                    "description",
                    "justificatif",
                    "lien_justificatif",
                    "ajoute_par",
                )
            },
        ),
        (
            "Administration",
            {
                "fields": (
                    "date_creation",
                )
            },
        ),
    )

    date_hierarchy = "date_depense"
    ordering = (
        "-date_depense",
        "-date_creation",
    )

    list_per_page = 30
    save_on_top = True

    list_select_related = (
        "agence",
        "proprietaire",
    )

    @admin.display(
        boolean=True,
        description="Justificatif"
    )
    def justificatif_disponible(self, obj):
        return bool(obj.justificatif)

    @admin.display(description="Consulter le justificatif")
    def lien_justificatif(self, obj):

        if not obj.justificatif:
            return "Aucun justificatif"

        try:
            return format_html(
                '<a href="{}" target="_blank" '
                'style="font-weight:700; color:#2563eb;">'
                "Ouvrir le justificatif"
                "</a>",
                obj.justificatif.url,
            )
        except ValueError:
            return "Fichier indisponible"


# =========================================================
# LOCAL COMMERCIAL INLINE
# Affiché directement dans un centre commercial
# =========================================================
class LocalCommercialInline(admin.TabularInline):

    model = LocalCommercial

    fields = (
        "numero",
        "nom",
        "type_local",
        "superficie",
        "prix_mensuel",
        "caution",
        "statut",
        "actif",
    )

    extra = 0
    show_change_link = True


# =========================================================
# CENTRE COMMERCIAL
# =========================================================
@admin.register(CentreCommercial)
class CentreCommercialAdmin(admin.ModelAdmin):

    list_display = (
        "code",
        "nom",
        "type_centre",
        "agence",
        "proprietaire",
        "batiment",
        "ville",
        "total_locaux",
        "locaux_libres",
        "locaux_occupes",
        "actif",
        "date_creation",
    )

    list_filter = (
        "type_centre",
        "ville",
        "actif",
        "date_creation",
    )

    search_fields = (
        "code",
        "nom",
        "adresse",
        "ville",
        "quartier",
        "description",
        "agence__nom",
        "proprietaire__nom",
        "proprietaire__prenom",
        "batiment__nom",
    )

    raw_id_fields = (
        "agence",
        "proprietaire",
        "batiment",
    )

    readonly_fields = (
        "date_creation",
        "total_locaux",
        "locaux_libres",
        "locaux_occupes",
    )

    fieldsets = (
        (
            "Identification du centre",
            {
                "fields": (
                    "agence",
                    "proprietaire",
                    "batiment",
                    "code",
                    "nom",
                    "type_centre",
                )
            },
        ),
        (
            "Localisation",
            {
                "fields": (
                    "adresse",
                    "ville",
                    "quartier",
                )
            },
        ),
        (
            "Description",
            {
                "fields": (
                    "description",
                )
            },
        ),
        (
            "Statistiques des locaux",
            {
                "fields": (
                    "total_locaux",
                    "locaux_libres",
                    "locaux_occupes",
                )
            },
        ),
        (
            "Administration",
            {
                "fields": (
                    "actif",
                    "date_creation",
                )
            },
        ),
    )

    inlines = (
        LocalCommercialInline,
    )

    actions = (
        "activer_centres",
        "desactiver_centres",
    )

    date_hierarchy = "date_creation"
    list_per_page = 30
    save_on_top = True

    list_select_related = (
        "agence",
        "proprietaire",
        "batiment",
    )

    @admin.display(description="Total locaux")
    def total_locaux(self, obj):
        return obj.nombre_locaux

    @admin.display(description="Locaux libres")
    def locaux_libres(self, obj):
        return obj.nombre_locaux_libres

    @admin.display(description="Locaux occupés")
    def locaux_occupes(self, obj):
        return obj.nombre_locaux_occupes

    @admin.action(description="Activer les centres sélectionnés")
    def activer_centres(self, request, queryset):
        nombre = queryset.update(actif=True)

        self.message_user(
            request,
            f"{nombre} centre(s) commercial(aux) activé(s)."
        )

    @admin.action(description="Désactiver les centres sélectionnés")
    def desactiver_centres(self, request, queryset):
        nombre = queryset.update(actif=False)

        self.message_user(
            request,
            f"{nombre} centre(s) commercial(aux) désactivé(s)."
        )


# =========================================================
# LOCAL COMMERCIAL
# =========================================================
@admin.register(LocalCommercial)
class LocalCommercialAdmin(admin.ModelAdmin):

    list_display = (
        "numero",
        "nom",
        "centre",
        "type_local",
        "superficie",
        "prix_mensuel",
        "caution",
        "statut",
        "disponibilite",
        "actif",
        "date_creation",
    )

    list_filter = (
        "type_local",
        "statut",
        "actif",
        "centre",
        "date_creation",
    )

    search_fields = (
        "numero",
        "nom",
        "description",
        "centre__nom",
        "centre__code",
        "centre__ville",
    )

    raw_id_fields = (
        "centre",
    )

    readonly_fields = (
        "date_creation",
        "disponibilite",
    )

    fieldsets = (
        (
            "Centre commercial",
            {
                "fields": (
                    "centre",
                )
            },
        ),
        (
            "Identification du local",
            {
                "fields": (
                    "numero",
                    "nom",
                    "type_local",
                )
            },
        ),
        (
            "Informations financières",
            {
                "fields": (
                    "superficie",
                    "prix_mensuel",
                    "caution",
                )
            },
        ),
        (
            "Description",
            {
                "fields": (
                    "description",
                )
            },
        ),
        (
            "Statut",
            {
                "fields": (
                    "statut",
                    "actif",
                    "disponibilite",
                    "date_creation",
                )
            },
        ),
    )

    actions = (
        "marquer_libres",
        "marquer_reserves",
        "marquer_maintenance",
        "marquer_fermes",
        "activer_locaux",
        "desactiver_locaux",
    )

    date_hierarchy = "date_creation"
    ordering = (
        "centre__nom",
        "numero",
    )

    list_per_page = 30
    save_on_top = True

    list_select_related = (
        "centre",
        "centre__agence",
    )

    @admin.display(
        boolean=True,
        description="Disponible"
    )
    def disponibilite(self, obj):
        return obj.est_disponible

    @admin.action(description="Marquer les locaux comme libres")
    def marquer_libres(self, request, queryset):
        nombre = queryset.update(statut="libre")

        self.message_user(
            request,
            f"{nombre} local/localaux marqué(s) comme libre(s)."
        )

    @admin.action(description="Marquer les locaux comme réservés")
    def marquer_reserves(self, request, queryset):
        nombre = queryset.update(statut="reserve")

        self.message_user(
            request,
            f"{nombre} local/localaux marqué(s) comme réservé(s)."
        )

    @admin.action(description="Marquer les locaux en maintenance")
    def marquer_maintenance(self, request, queryset):
        nombre = queryset.update(statut="maintenance")

        self.message_user(
            request,
            f"{nombre} local/localaux placé(s) en maintenance."
        )

    @admin.action(description="Marquer les locaux comme fermés")
    def marquer_fermes(self, request, queryset):
        nombre = queryset.update(statut="ferme")

        self.message_user(
            request,
            f"{nombre} local/localaux marqué(s) comme fermé(s)."
        )

    @admin.action(description="Activer les locaux sélectionnés")
    def activer_locaux(self, request, queryset):
        nombre = queryset.update(actif=True)

        self.message_user(
            request,
            f"{nombre} local/localaux activé(s)."
        )

    @admin.action(description="Désactiver les locaux sélectionnés")
    def desactiver_locaux(self, request, queryset):
        nombre = queryset.update(actif=False)

        self.message_user(
            request,
            f"{nombre} local/localaux désactivé(s)."
        )


# =========================================================
# OCCUPANT COMMERCIAL
# =========================================================
@admin.register(OccupantCommercial)
class OccupantCommercialAdmin(admin.ModelAdmin):

    list_display = (
        "nom_complet",
        "agence",
        "telephone",
        "email",
        "nom_entreprise",
        "activite_commerciale",
        "type_piece",
        "numero_piece",
        "photo_disponible",
        "piece_disponible",
        "date_creation",
    )

    list_filter = (
        "type_piece",
        "nationalite",
        "agence",
        "date_creation",
    )

    search_fields = (
        "nom",
        "prenom",
        "telephone",
        "email",
        "numero_piece",
        "nom_entreprise",
        "activite_commerciale",
        "registre_commerce",
        "profession",
        "nationalite",
        "agence__nom",
    )

    raw_id_fields = (
        "agence",
    )

    readonly_fields = (
        "date_creation",
        "apercu_photo",
        "lien_piece_identite",
    )

    fieldsets = (
        (
            "Agence",
            {
                "fields": (
                    "agence",
                )
            },
        ),
        (
            "Informations personnelles",
            {
                "fields": (
                    "nom",
                    "prenom",
                    "date_naissance",
                    "lieu_naissance",
                    "nationalite",
                    "profession",
                )
            },
        ),
        (
            "Coordonnées",
            {
                "fields": (
                    "telephone",
                    "email",
                    "adresse",
                )
            },
        ),
        (
            "Informations commerciales",
            {
                "fields": (
                    "nom_entreprise",
                    "activite_commerciale",
                    "registre_commerce",
                )
            },
        ),
        (
            "Pièce d’identité",
            {
                "fields": (
                    "type_piece",
                    "numero_piece",
                    "date_expiration_piece",
                    "piece_identite",
                    "lien_piece_identite",
                )
            },
        ),
        (
            "Photo",
            {
                "fields": (
                    "photo",
                    "apercu_photo",
                )
            },
        ),
        (
            "Administration",
            {
                "fields": (
                    "date_creation",
                )
            },
        ),
    )

    date_hierarchy = "date_creation"
    ordering = (
        "nom",
        "prenom",
    )

    list_per_page = 30
    save_on_top = True

    list_select_related = (
        "agence",
    )

    @admin.display(description="Occupant")
    def nom_complet(self, obj):
        return f"{obj.prenom} {obj.nom}"

    @admin.display(
        boolean=True,
        description="Photo"
    )
    def photo_disponible(self, obj):
        return bool(obj.photo)

    @admin.display(
        boolean=True,
        description="Pièce"
    )
    def piece_disponible(self, obj):
        return bool(obj.piece_identite)

    @admin.display(description="Aperçu de la photo")
    def apercu_photo(self, obj):

        if not obj.photo:
            return "Aucune photo"

        try:
            return format_html(
                '<img src="{}" '
                'style="width:140px; height:140px; '
                'object-fit:cover; border-radius:14px; '
                'border:1px solid #d1d5db;" />',
                obj.photo.url,
            )
        except ValueError:
            return "Photo indisponible"

    @admin.display(description="Consulter la pièce")
    def lien_piece_identite(self, obj):

        if not obj.piece_identite:
            return "Aucune pièce d’identité"

        try:
            return format_html(
                '<a href="{}" target="_blank" '
                'style="font-weight:700; color:#2563eb;">'
                "Ouvrir la pièce d’identité"
                "</a>",
                obj.piece_identite.url,
            )
        except ValueError:
            return "Pièce indisponible"


# =========================================================
# CONTRAT COMMERCIAL
# =========================================================
@admin.register(ContratCommercial)
class ContratCommercialAdmin(admin.ModelAdmin):

    list_display = (
        "numero_contrat",
        "agence",
        "local",
        "occupant",
        "nom_activite",
        "date_debut",
        "date_fin",
        "prix_mensuel",
        "caution",
        "caution_payee",
        "certificat_valide",
        "actif",
        "date_signature",
    )

    list_filter = (
        "actif",
        "caution_payee",
        "signe_par_occupant",
        "signe_par_gestionnaire",
        "certifie_application",
        "date_debut",
        "date_fin",
        "date_signature",
        "date_creation",
    )

    search_fields = (
        "numero_contrat",
        "nom_activite",
        "local__numero",
        "local__nom",
        "local__centre__nom",
        "occupant__nom",
        "occupant__prenom",
        "occupant__telephone",
        "occupant__email",
        "agence__nom",
    )

    raw_id_fields = (
        "agence",
        "local",
        "occupant",
    )

    readonly_fields = (
        "numero_contrat",
        "code_verification",
        "certificat_valide",
        "lien_verification",
        "lien_pdf",
        "date_creation",
        "date_modification",
    )

    fieldsets = (
        (
            "Identification du contrat",
            {
                "fields": (
                    "agence",
                    "numero_contrat",
                    "code_verification",
                    "local",
                    "occupant",
                    "nom_activite",
                )
            },
        ),
        (
            "Durée du contrat",
            {
                "fields": (
                    "date_debut",
                    "date_fin",
                    "date_signature",
                )
            },
        ),
        (
            "Informations financières",
            {
                "fields": (
                    "prix_mensuel",
                    "caution",
                    "caution_payee",
                )
            },
        ),
        (
            "Conditions",
            {
                "fields": (
                    "conditions",
                )
            },
        ),
        (
            "Signatures et certification",
            {
                "fields": (
                    "signe_par_occupant",
                    "signe_par_gestionnaire",
                    "certifie_application",
                    "certificat_valide",
                )
            },
        ),
        (
            "Documents et vérification",
            {
                "fields": (
                    "lien_verification",
                    "lien_pdf",
                )
            },
        ),
        (
            "Administration",
            {
                "fields": (
                    "actif",
                    "date_creation",
                    "date_modification",
                )
            },
        ),
    )

    actions = (
        "activer_contrats",
        "desactiver_contrats",
        "marquer_cautions_payees",
        "marquer_cautions_non_payees",
        "signer_par_occupant",
        "signer_par_gestionnaire",
    )

    date_hierarchy = "date_creation"
    ordering = (
        "-date_creation",
    )

    list_per_page = 30
    save_on_top = True

    list_select_related = (
        "agence",
        "local",
        "local__centre",
        "occupant",
    )

    @admin.display(
        boolean=True,
        description="Contrat certifié"
    )
    def certificat_valide(self, obj):
        return obj.est_certifie

    @admin.display(description="Vérification publique")
    def lien_verification(self, obj):

        if not obj.pk:
            return "Le contrat doit être enregistré."

        try:
            return format_html(
                '<a href="{}" target="_blank" '
                'style="font-weight:700; color:#16a34a;">'
                "Vérifier le contrat"
                "</a>",
                obj.get_verification_url(),
            )
        except Exception:
            return "URL de vérification indisponible"

    @admin.display(description="Document PDF")
    def lien_pdf(self, obj):

        if not obj.pk:
            return "Le contrat doit être enregistré."

        try:
            return format_html(
                '<a href="{}" target="_blank" '
                'style="font-weight:700; color:#dc2626;">'
                "Télécharger le contrat PDF"
                "</a>",
                obj.get_pdf_url(),
            )
        except Exception:
            return "URL PDF indisponible"

    @admin.action(description="Activer les contrats sélectionnés")
    def activer_contrats(self, request, queryset):

        nombre = 0

        for contrat in queryset:
            contrat.actif = True
            contrat.save(update_fields=["actif"])
            nombre += 1

        self.message_user(
            request,
            f"{nombre} contrat(s) activé(s)."
        )

    @admin.action(description="Désactiver les contrats sélectionnés")
    def desactiver_contrats(self, request, queryset):

        nombre = 0

        for contrat in queryset:
            contrat.actif = False
            contrat.save(update_fields=["actif"])
            nombre += 1

        self.message_user(
            request,
            f"{nombre} contrat(s) désactivé(s)."
        )

    @admin.action(description="Marquer les cautions comme payées")
    def marquer_cautions_payees(self, request, queryset):
        nombre = queryset.update(caution_payee=True)

        self.message_user(
            request,
            f"{nombre} caution(s) marquée(s) comme payée(s)."
        )

    @admin.action(description="Marquer les cautions comme non payées")
    def marquer_cautions_non_payees(self, request, queryset):
        nombre = queryset.update(caution_payee=False)

        self.message_user(
            request,
            f"{nombre} caution(s) marquée(s) comme non payée(s)."
        )

    @admin.action(description="Signer au nom des occupants")
    def signer_par_occupant(self, request, queryset):
        nombre = queryset.update(signe_par_occupant=True)

        self.message_user(
            request,
            f"{nombre} contrat(s) signé(s) par l’occupant."
        )

    @admin.action(description="Signer au nom du gestionnaire")
    def signer_par_gestionnaire(self, request, queryset):
        nombre = queryset.update(signe_par_gestionnaire=True)

        self.message_user(
            request,
            f"{nombre} contrat(s) signé(s) par le gestionnaire."
        )


# =========================================================
# PERSONNALISATION DE L’ADMINISTRATION
# =========================================================
admin.site.site_header = "Administration Gestion Immobilière"
admin.site.site_title = "Gestion immobilière"
admin.site.index_title = "Tableau de bord administratif"