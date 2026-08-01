from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages

from .models import Agence, Batiment, ChambreLogement, Locataire, Location, Paiement, Proprietaire,Employe


def get_agence(user):
    agence, created = Agence.objects.get_or_create(
        proprietaire=user,
        defaults={
            "nom": f"Agence de {user.username}"
        }
    )
    return agence

from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.shortcuts import render, redirect

from .models import Employe

def login_view(request):

    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is None:
            messages.error(
                request,
                "Nom utilisateur ou mot de passe incorrect."
            )
            return redirect("login")

        login(request, user)

        if user.is_superuser:
            return redirect("dashboard")

        employe = Employe.objects.filter(
            utilisateur=user
        ).first()

        if employe:
            return redirect("espace_employe")

        messages.error(
            request,
            "Ce compte existe, mais il n'est lié à aucun agent ou secrétaire."
        )

        logout(request)
        return redirect("login")

    return render(request, "login.html")


def register_view(request):
    if request.method == "POST":
        nom_agence = request.POST.get("nom_agence")
        username = request.POST.get("username")
        email = request.POST.get("email")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")

        if password1 != password2:
            messages.error(request, "Les mots de passe ne correspondent pas.")
            return redirect("register")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Nom utilisateur déjà utilisé.")
            return redirect("register")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Cet email est déjà utilisé.")
            return redirect("register")

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1
        )

        Agence.objects.create(
            proprietaire=user,
            nom=nom_agence or f"Agence de {username}"
        )

        login(request, user)
        return redirect("dashboard")

    return render(request, "register.html")


def logout_view(request):
    logout(request)
    return redirect("login")


@login_required(login_url="login")
def dashboard(request):
    agence = get_agence(request.user)

    batiments = Batiment.objects.filter(agence=agence)
    locataires = Locataire.objects.filter(agence=agence)
    locations = Location.objects.filter(agence=agence)
    paiements = Paiement.objects.filter(agence=agence)

    total_loyers = sum(
        p.montant for p in paiements if p.statut == "paye"
    )

    paiements_retard = paiements.filter(statut="retard").count()

    context = {
        "agence": agence,
        "batiments": batiments,
        "locataires": locataires,
        "locations": locations,
        "paiements": paiements,
        "total_batiments": batiments.count(),
        "total_locataires": locataires.count(),
        "total_locations": locations.count(),
        "total_loyers": total_loyers,
        "paiements_retard": paiements_retard,
    }

    return render(request, "dashboard.html", context)


@login_required(login_url="login")
def proprietaires(request):
    agence = get_agence(request.user)

    q = request.GET.get("q", "")

    proprietaires = Proprietaire.objects.filter(
        agence=agence
    )

    if q:
        proprietaires = proprietaires.filter(
            nom__icontains=q
        ) | Proprietaire.objects.filter(
            agence=agence,
            prenom__icontains=q
        ) | Proprietaire.objects.filter(
            agence=agence,
            telephone__icontains=q
        ) | Proprietaire.objects.filter(
            agence=agence,
            code_client__icontains=q
        )

    context = {
        "agence": agence,
        "proprietaires": proprietaires,
        "q": q,
        "total_proprietaires": proprietaires.count(),
    }

    return render(
        request,
        "proprietaires.html",
        context
    )




from .models import (
    Batiment,
    Location,
    Proprietaire,
    UniteLocative,
   

)


from .services.contrat_bail import (
    generer_contrat_bail_numerique,
)

from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch, Q
from django.shortcuts import render

from .models import Batiment, Proprietaire, UniteLocative


@login_required(login_url="login")
def batiments(request):
    agence = get_agence(request.user)
    q = request.GET.get("q", "").strip()

    unites_prefetch = Prefetch(
        "unites_locatives",
        queryset=UniteLocative.objects.filter(
            actif=True,
        ).order_by(
            "type_unite",
            "numero",
        ),
        to_attr="unites_prefetched",
    )

    batiments_queryset = Batiment.objects.filter(
        agence=agence,
    ).select_related(
        "proprietaire",
        "agence",
    ).prefetch_related(
        unites_prefetch,
    )

    if q:
        batiments_queryset = batiments_queryset.filter(
            Q(code_batiment__icontains=q)
            | Q(nom__icontains=q)
            | Q(ville__icontains=q)
            | Q(adresse__icontains=q)
            | Q(proprietaire__nom__icontains=q)
            | Q(proprietaire__prenom__icontains=q)
            | Q(unites_locatives__numero__icontains=q)
            | Q(unites_locatives__description__icontains=q)
        ).distinct()

    batiments = list(batiments_queryset)

    total_unites = 0
    unites_occupees = 0
    unites_libres = 0
    unites_reservees = 0
    unites_maintenance = 0

    total_logements = 0
    logements_occupes = 0
    logements_libres = 0
    logements_reserves = 0
    logements_maintenance = 0

    total_appartements = 0
    total_studios = 0

    total_magasins = 0
    magasins_occupes = 0
    magasins_libres = 0
    magasins_reserves = 0
    magasins_maintenance = 0

    for batiment in batiments:
        unites = getattr(
            batiment,
            "unites_prefetched",
            [],
        )

        details_occupation = []

        batiment_total_unites = 0
        batiment_unites_occupees = 0
        batiment_unites_libres = 0
        batiment_unites_reservees = 0
        batiment_unites_maintenance = 0

        batiment_appartements = 0
        batiment_studios = 0
        batiment_magasins = 0

        batiment_logements = 0
        batiment_logements_occupes = 0
        batiment_logements_libres = 0

        for unite in unites:
            batiment_total_unites += 1
            total_unites += 1

            est_appartement = (
                unite.type_unite
                == UniteLocative.TypeUnite.APPARTEMENT
            )

            est_studio = (
                unite.type_unite
                == UniteLocative.TypeUnite.STUDIO
            )

            est_magasin = (
                unite.type_unite
                == UniteLocative.TypeUnite.MAGASIN
            )

            est_habitation = est_appartement or est_studio

            if est_appartement:
                batiment_appartements += 1
                total_appartements += 1

            elif est_studio:
                batiment_studios += 1
                total_studios += 1

            elif est_magasin:
                batiment_magasins += 1
                total_magasins += 1

            if est_habitation:
                batiment_logements += 1
                total_logements += 1

            # L’occupation est temporairement déterminée
            # à partir du statut de l’unité.
            if unite.statut == UniteLocative.Statut.OCCUPE:
                batiment_unites_occupees += 1
                unites_occupees += 1

                if est_habitation:
                    batiment_logements_occupes += 1
                    logements_occupes += 1

                if est_magasin:
                    magasins_occupes += 1

                details_occupation.append({
                    "unite": unite,
                    "location": None,
                    "locataire": None,
                })

            elif unite.statut == UniteLocative.Statut.RESERVE:
                batiment_unites_reservees += 1
                unites_reservees += 1

                if est_habitation:
                    logements_reserves += 1

                if est_magasin:
                    magasins_reserves += 1

            elif unite.statut == UniteLocative.Statut.MAINTENANCE:
                batiment_unites_maintenance += 1
                unites_maintenance += 1

                if est_habitation:
                    logements_maintenance += 1

                if est_magasin:
                    magasins_maintenance += 1

            else:
                batiment_unites_libres += 1
                unites_libres += 1

                if est_habitation:
                    batiment_logements_libres += 1
                    logements_libres += 1

                if est_magasin:
                    magasins_libres += 1

        batiment.details_occupation = details_occupation

        batiment.total_unites_affiche = batiment_total_unites
        batiment.unites_occupees_affiche = (
            batiment_unites_occupees
        )
        batiment.unites_libres_affiche = (
            batiment_unites_libres
        )
        batiment.unites_reservees_affiche = (
            batiment_unites_reservees
        )
        batiment.unites_maintenance_affiche = (
            batiment_unites_maintenance
        )

        batiment.appartements_affiche = (
            batiment_appartements
        )
        batiment.studios_affiche = (
            batiment_studios
        )
        batiment.magasins_affiche = (
            batiment_magasins
        )

        batiment.logements_affiche = batiment_logements
        batiment.logements_occupes_affiche = (
            batiment_logements_occupes
        )
        batiment.logements_libres_affiche = (
            batiment_logements_libres
        )

        if batiment_total_unites > 0:
            batiment.taux_occupation_affiche = round(
                (
                    batiment_unites_occupees
                    / batiment_total_unites
                )
                * 100
            )
        else:
            batiment.taux_occupation_affiche = 0

    context = {
        "batiments": batiments,
        "q": q,

        "total_batiments": len(batiments),

        "total_unites": total_unites,
        "unites_occupees": unites_occupees,
        "unites_libres": unites_libres,
        "unites_reservees": unites_reservees,
        "unites_maintenance": unites_maintenance,

        "total_logements": total_logements,
        "logements_occupes": logements_occupes,
        "logements_libres": logements_libres,
        "logements_reserves": logements_reserves,
        "logements_maintenance": logements_maintenance,

        "total_appartements": total_appartements,
        "total_studios": total_studios,

        "total_magasins": total_magasins,
        "magasins_occupes": magasins_occupes,
        "magasins_libres": magasins_libres,
        "magasins_reserves": magasins_reserves,
        "magasins_maintenance": magasins_maintenance,

        "total_proprietaires": Proprietaire.objects.filter(
            agence=agence,
        ).count(),
    }

    return render(
        request,
        "batiments.html",
        context,
    )
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404

from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render

from .models import Batiment, Proprietaire, UniteLocative


@login_required(login_url="login")
def ajouter_batiment(request):
    agence = get_agence(request.user)

    proprietaires = Proprietaire.objects.filter(
        agence=agence
    ).order_by(
        "nom",
        "prenom",
    )

    if request.method == "POST":
        proprietaire_id = request.POST.get(
            "proprietaire",
            ""
        ).strip()

        code_batiment = request.POST.get(
            "code_batiment",
            ""
        ).strip()

        nom = request.POST.get(
            "nom",
            ""
        ).strip()

        adresse = request.POST.get(
            "adresse",
            ""
        ).strip()

        ville = request.POST.get(
            "ville",
            ""
        ).strip()

        description = request.POST.get(
            "description",
            ""
        ).strip()

        actif = request.POST.get("actif") == "True"

        # Les indices sont envoyés par les champs :
        # <input name="unite_index" value="1">
        indices_unites = request.POST.getlist("unite_index")

        # -----------------------------------------------------
        # VALIDATION DU BÂTIMENT
        # -----------------------------------------------------

        if not proprietaire_id:
            messages.error(
                request,
                "Veuillez sélectionner un propriétaire.",
            )

            return render(
                request,
                "ajouter_batiment.html",
                {
                    "proprietaires": proprietaires,
                },
            )

        if not code_batiment:
            messages.error(
                request,
                "Le code du bâtiment est obligatoire.",
            )

            return render(
                request,
                "ajouter_batiment.html",
                {
                    "proprietaires": proprietaires,
                },
            )

        if not nom:
            messages.error(
                request,
                "Le nom du bâtiment est obligatoire.",
            )

            return render(
                request,
                "ajouter_batiment.html",
                {
                    "proprietaires": proprietaires,
                },
            )

        if not adresse:
            messages.error(
                request,
                "L’adresse du bâtiment est obligatoire.",
            )

            return render(
                request,
                "ajouter_batiment.html",
                {
                    "proprietaires": proprietaires,
                },
            )

        if not ville:
            messages.error(
                request,
                "La ville du bâtiment est obligatoire.",
            )

            return render(
                request,
                "ajouter_batiment.html",
                {
                    "proprietaires": proprietaires,
                },
            )

        if Batiment.objects.filter(
            code_batiment__iexact=code_batiment
        ).exists():
            messages.error(
                request,
                (
                    f"Un bâtiment ayant le code "
                    f"« {code_batiment} » existe déjà."
                ),
            )

            return render(
                request,
                "ajouter_batiment.html",
                {
                    "proprietaires": proprietaires,
                },
            )

        if not indices_unites:
            messages.error(
                request,
                (
                    "Ajoutez au moins un appartement, "
                    "un studio ou un magasin."
                ),
            )

            return render(
                request,
                "ajouter_batiment.html",
                {
                    "proprietaires": proprietaires,
                },
            )

        proprietaire = get_object_or_404(
            Proprietaire,
            id=proprietaire_id,
            agence=agence,
        )

        # -----------------------------------------------------
        # PRÉPARATION DES UNITÉS
        # -----------------------------------------------------

        types_unites_valides = {
            valeur
            for valeur, libelle
            in UniteLocative.TypeUnite.choices
        }

        types_toilettes_valides = {
            valeur
            for valeur, libelle
            in UniteLocative.TypeToilette.choices
        }

        usages_commerciaux_valides = {
            valeur
            for valeur, libelle
            in UniteLocative.UsageCommercial.choices
        }

        unites_preparees = []
        numeros_utilises = set()

        total_appartements = 0
        total_studios = 0
        total_magasins = 0

        try:
            for index in indices_unites:
                type_unite = request.POST.get(
                    f"type_unite_{index}",
                    "",
                ).strip()

                numero = request.POST.get(
                    f"numero_{index}",
                    "",
                ).strip()

                nombre_chambres_brut = request.POST.get(
                    f"nombre_chambres_{index}",
                    "0",
                ).strip()

                # Compatible avec les deux noms possibles :
                # type_toilette_1 ou type_toilettes_1
                type_toilette = request.POST.get(
                    f"type_toilette_{index}",
                    "",
                ).strip()

                if not type_toilette:
                    type_toilette = request.POST.get(
                        f"type_toilettes_{index}",
                        "",
                    ).strip()

                prix_brut = request.POST.get(
                    f"prix_mensuel_{index}",
                    "",
                ).strip()

                usage_commercial = request.POST.get(
                    f"usage_commercial_{index}",
                    "",
                ).strip()

                description_unite = request.POST.get(
                    f"description_unite_{index}",
                    "",
                ).strip()

                # -------------------------------------------------
                # TYPE D’UNITÉ
                # -------------------------------------------------

                if type_unite not in types_unites_valides:
                    raise ValueError(
                        "Un type d’unité sélectionné est invalide."
                    )

                if not numero:
                    raise ValueError(
                        (
                            "Chaque appartement, studio ou magasin "
                            "doit avoir un nom ou un numéro."
                        )
                    )

                numero_normalise = numero.casefold()

                if numero_normalise in numeros_utilises:
                    raise ValueError(
                        (
                            f"Le nom ou numéro « {numero} » "
                            f"est utilisé plusieurs fois."
                        )
                    )

                numeros_utilises.add(numero_normalise)

                # -------------------------------------------------
                # TOILETTES
                # -------------------------------------------------

                if type_toilette not in types_toilettes_valides:
                    raise ValueError(
                        (
                            f"Veuillez sélectionner le type de "
                            f"toilettes pour « {numero} »."
                        )
                    )

                # -------------------------------------------------
                # PRIX
                # -------------------------------------------------

                prix_nettoye = (
                    prix_brut
                    .replace(" ", "")
                    .replace(",", ".")
                )

                try:
                    prix_mensuel = Decimal(prix_nettoye)
                except InvalidOperation:
                    raise ValueError(
                        (
                            f"Le loyer mensuel de "
                            f"« {numero} » est invalide."
                        )
                    )

                if prix_mensuel < 0:
                    raise ValueError(
                        (
                            f"Le loyer mensuel de "
                            f"« {numero} » ne peut pas être négatif."
                        )
                    )

                # -------------------------------------------------
                # APPARTEMENT
                # -------------------------------------------------

                if (
                    type_unite
                    == UniteLocative.TypeUnite.APPARTEMENT
                ):
                    try:
                        nombre_chambres = int(
                            nombre_chambres_brut
                        )
                    except (TypeError, ValueError):
                        nombre_chambres = 0

                    if nombre_chambres < 1:
                        raise ValueError(
                            (
                                f"L’appartement « {numero} » "
                                f"doit avoir au moins une chambre."
                            )
                        )

                    toilettes_autorisees = {
                        UniteLocative.TypeToilette.COMMUNE_APPARTEMENT,
                        UniteLocative.TypeToilette.UNE_PAR_CHAMBRE,
                        UniteLocative.TypeToilette.COMMUNE_BATIMENT,
                        UniteLocative.TypeToilette.AUCUNE,
                    }

                    if type_toilette not in toilettes_autorisees:
                        raise ValueError(
                            (
                                f"Le type de toilettes choisi pour "
                                f"l’appartement « {numero} » "
                                f"n’est pas valide."
                            )
                        )

                    usage_commercial = ""
                    total_appartements += 1

                # -------------------------------------------------
                # STUDIO
                # -------------------------------------------------

                elif (
                    type_unite
                    == UniteLocative.TypeUnite.STUDIO
                ):
                    nombre_chambres = 0
                    usage_commercial = ""

                    toilettes_autorisees = {
                        UniteLocative.TypeToilette.PRIVEE_STUDIO,
                        UniteLocative.TypeToilette.COMMUNE_BATIMENT,
                        UniteLocative.TypeToilette.AUCUNE,
                    }

                    if type_toilette not in toilettes_autorisees:
                        raise ValueError(
                            (
                                f"Le type de toilettes choisi pour "
                                f"le studio « {numero} » "
                                f"n’est pas valide."
                            )
                        )

                    total_studios += 1

                # -------------------------------------------------
                # MAGASIN
                # -------------------------------------------------

                else:
                    nombre_chambres = 0

                    if (
                        usage_commercial
                        not in usages_commerciaux_valides
                    ):
                        raise ValueError(
                            (
                                f"Veuillez indiquer l’utilisation "
                                f"du magasin « {numero} »."
                            )
                        )

                    toilettes_autorisees = {
                        UniteLocative.TypeToilette.PRIVEE_MAGASIN,
                        UniteLocative.TypeToilette.COMMUNE_BATIMENT,
                        UniteLocative.TypeToilette.AUCUNE,
                    }

                    if type_toilette not in toilettes_autorisees:
                        raise ValueError(
                            (
                                f"Le type de toilettes choisi pour "
                                f"le magasin « {numero} » "
                                f"n’est pas valide."
                            )
                        )

                    total_magasins += 1

                unites_preparees.append({
                    "numero": numero,
                    "type_unite": type_unite,
                    "nombre_chambres": nombre_chambres,
                    "type_toilette": type_toilette,
                    "prix_mensuel": prix_mensuel,
                    "usage_commercial": usage_commercial,
                    "description": description_unite or None,
                    "statut": UniteLocative.Statut.LIBRE,
                    "actif": True,
                })

        except ValueError as erreur:
            messages.error(
                request,
                str(erreur),
            )

            return render(
                request,
                "ajouter_batiment.html",
                {
                    "proprietaires": proprietaires,
                },
            )

        # Appartements + studios seulement.
        # Les magasins ne sont pas des logements d’habitation.
        nombre_logements = (
            total_appartements
            + total_studios
        )

        # -----------------------------------------------------
        # ENREGISTREMENT
        # -----------------------------------------------------

        try:
            with transaction.atomic():
                batiment = Batiment.objects.create(
                    agence=agence,
                    proprietaire=proprietaire,
                    code_batiment=code_batiment,
                    nom=nom,
                    adresse=adresse,
                    ville=ville,

                    # Si votre champ est editable=False,
                    # Django permet quand même de lui attribuer
                    # une valeur depuis le code Python.
                    nombre_logements=nombre_logements,

                    description=description or None,
                    actif=actif,
                )

                for donnees_unite in unites_preparees:
                    UniteLocative.objects.create(
                        batiment=batiment,
                        **donnees_unite,
                    )

        except IntegrityError:
            messages.error(
                request,
                (
                    "Impossible d’enregistrer le bâtiment. "
                    "Vérifiez que son code et les numéros "
                    "des unités ne sont pas déjà utilisés."
                ),
            )

            return render(
                request,
                "ajouter_batiment.html",
                {
                    "proprietaires": proprietaires,
                },
            )

        except Exception as erreur:
            messages.error(
                request,
                (
                    "Une erreur est survenue pendant "
                    f"l’enregistrement : {erreur}"
                ),
            )

            return render(
                request,
                "ajouter_batiment.html",
                {
                    "proprietaires": proprietaires,
                },
            )

        total_unites = len(unites_preparees)

        messages.success(
            request,
            (
                f"Le bâtiment « {batiment.nom} » a été ajouté "
                f"avec succès : {total_appartements} appartement(s), "
                f"{total_studios} studio(s) et "
                f"{total_magasins} magasin(s), soit "
                f"{total_unites} unité(s) au total."
            ),
        )

        return redirect("batiments")

    return render(
        request,
        "ajouter_batiment.html",
        {
            "proprietaires": proprietaires,
        },
    )

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.db.models.deletion import ProtectedError
from django.views.decorators.http import require_POST


@login_required(login_url="login")
@require_POST
def supprimer_batiment(request, id):
    agence = get_agence(request.user)

    batiment = get_object_or_404(
        Batiment.objects.select_related(
            "proprietaire",
        ),
        id=id,
        agence=agence,
    )

    nom_batiment = batiment.nom

    locations_actives = Location.objects.filter(
        agence=agence,
        batiment=batiment,
        active=True,
    )

    if locations_actives.exists():
        total_baux_actifs = locations_actives.count()

        messages.error(
            request,
            (
                f"Impossible de supprimer le bâtiment « {nom_batiment} ». "
                f"Il contient encore {total_baux_actifs} bail(aux) actif(s). "
                "Libérez d’abord toutes les unités occupées."
            ),
        )

        return redirect("batiments")

    try:
        with transaction.atomic():
            batiment.delete()

        messages.success(
            request,
            (
                f"Le bâtiment « {nom_batiment} » et ses unités "
                "ont été supprimés avec succès."
            ),
        )

    except ProtectedError:
        messages.error(
            request,
            (
                f"Le bâtiment « {nom_batiment} » ne peut pas être supprimé, "
                "car certaines données liées sont protégées."
            ),
        )

    except Exception as erreur:
        messages.error(
            request,
            f"Impossible de supprimer le bâtiment : {erreur}",
        )

    return redirect("batiments")



from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, render

from .models import (
    Batiment,
    ChambreLogement,
    Location,
    UniteLocative,
)




@login_required(login_url="login")
def detail_batiment(request, id):
    agence = get_agence(request.user)

    # ---------------------------------------------------------
    # BÂTIMENT
    # ---------------------------------------------------------

    batiment = get_object_or_404(
        Batiment.objects.select_related(
            "proprietaire",
            "agence",
        ),
        id=id,
        agence=agence,
    )

    # ---------------------------------------------------------
    # BAUX ACTIFS DES UNITÉS
    # ---------------------------------------------------------

    baux_actifs_queryset = Location.objects.filter(
        agence=agence,
        batiment=batiment,
        active=True,
        unite__isnull=False,
    ).select_related(
        "locataire",
        "unite",
        "batiment",
    ).order_by(
        "-date_debut",
        "-id",
    )

    prefetch_baux_actifs = Prefetch(
        "locations",
        queryset=baux_actifs_queryset,
        to_attr="baux_actifs_prefetched",
    )

    # ---------------------------------------------------------
    # APPARTEMENTS, STUDIOS ET MAGASINS
    # ---------------------------------------------------------

    unites = list(
        UniteLocative.objects.filter(
            batiment=batiment,
            actif=True,
        ).prefetch_related(
            prefetch_baux_actifs,
        ).order_by(
            "type_unite",
            "numero",
        )
    )

    unites_occupees = []
    unites_libres = []
    unites_reservees = []
    unites_maintenance = []

    total_appartements = 0
    total_studios = 0
    total_magasins = 0
    total_chambres = 0

    revenus_mensuels_potentiels = 0
    revenus_mensuels_actifs = 0

    # ---------------------------------------------------------
    # ANALYSE DE CHAQUE UNITÉ
    # ---------------------------------------------------------

    for unite in unites:
        # Compatibilité temporaire avec un ancien template
        # qui utiliserait unite.nom.
        unite.nom = unite.numero

        revenus_mensuels_potentiels += (
            unite.prix_mensuel or 0
        )

        # Compter les types d’unités.
        if (
            unite.type_unite
            == UniteLocative.TypeUnite.APPARTEMENT
        ):
            total_appartements += 1
            total_chambres += unite.nombre_chambres or 0

        elif (
            unite.type_unite
            == UniteLocative.TypeUnite.STUDIO
        ):
            total_studios += 1

        elif (
            unite.type_unite
            == UniteLocative.TypeUnite.MAGASIN
        ):
            total_magasins += 1

        baux_actifs = getattr(
            unite,
            "baux_actifs_prefetched",
            [],
        )

        bail = (
            baux_actifs[0]
            if baux_actifs
            else None
        )

        # -----------------------------------------------------
        # UNITÉ OCCUPÉE
        # -----------------------------------------------------

        if bail:
            # Mettre automatiquement l’unité au statut occupé.
            if (
                unite.statut
                != UniteLocative.Statut.OCCUPE
            ):
                UniteLocative.objects.filter(
                    pk=unite.pk,
                ).update(
                    statut=UniteLocative.Statut.OCCUPE,
                )

                unite.statut = (
                    UniteLocative.Statut.OCCUPE
                )

            erreur_contrat = None

            # Génération automatique du contrat numérique.
            if not bail.contrat_bail_numerique:
                try:
                    generer_contrat_bail_numerique(
                        bail
                    )

                    bail.refresh_from_db(
                        fields=[
                            "contrat_bail_numerique",
                            "date_generation_contrat",
                        ]
                    )

                except Exception as erreur:
                    # Le bâtiment reste affiché même si le PDF
                    # rencontre temporairement une erreur.
                    erreur_contrat = str(erreur)

            montant_bail = (
                bail.loyer
                if bail.loyer is not None
                else unite.prix_mensuel
            )

            revenus_mensuels_actifs += (
                montant_bail or 0
            )

            contrat_disponible = bool(
                bail.contrat_bail_numerique
            )

            contrat_url = None

            if contrat_disponible:
                try:
                    contrat_url = (
                        bail.contrat_bail_numerique.url
                    )
                except ValueError:
                    contrat_url = None
                    contrat_disponible = False

            unites_occupees.append({
                "unite": unite,

                # Compatibilité avec l’ancien template.
                "chambre": unite,

                "bail": bail,
                "location": bail,
                "locataire": bail.locataire,

                "montant_loyer": montant_bail,

                "contrat_disponible": (
                    contrat_disponible
                ),
                "contrat_url": contrat_url,
                "erreur_contrat": erreur_contrat,
            })

        # -----------------------------------------------------
        # UNITÉ RÉSERVÉE
        # -----------------------------------------------------

        elif (
            unite.statut
            == UniteLocative.Statut.RESERVE
        ):
            unites_reservees.append(unite)

        # -----------------------------------------------------
        # UNITÉ EN MAINTENANCE
        # -----------------------------------------------------

        elif (
            unite.statut
            == UniteLocative.Statut.MAINTENANCE
        ):
            unites_maintenance.append(unite)

        # -----------------------------------------------------
        # UNITÉ LIBRE
        # -----------------------------------------------------

        else:
            # Une unité marquée occupée sans bail actif
            # doit redevenir libre.
            if (
                unite.statut
                == UniteLocative.Statut.OCCUPE
            ):
                UniteLocative.objects.filter(
                    pk=unite.pk,
                ).update(
                    statut=UniteLocative.Statut.LIBRE,
                )

                unite.statut = (
                    UniteLocative.Statut.LIBRE
                )

            unites_libres.append(unite)

    # ---------------------------------------------------------
    # ANCIENNES LOCATIONS BASÉES SUR CHAMBRELOGEMENT
    # ---------------------------------------------------------

    anciennes_locations_actives = list(
        Location.objects.filter(
            agence=agence,
            batiment=batiment,
            active=True,
            unite__isnull=True,
            chambre__isnull=False,
        ).select_related(
            "locataire",
            "chambre",
        ).order_by(
            "chambre__numero",
            "-date_debut",
        )
    )

    # ---------------------------------------------------------
    # STATISTIQUES
    # ---------------------------------------------------------

    total_unites = len(unites)
    total_occupees = len(unites_occupees)
    total_libres = len(unites_libres)
    total_reservees = len(unites_reservees)
    total_maintenance = len(unites_maintenance)

    if total_unites > 0:
        taux_occupation = round(
            (total_occupees / total_unites) * 100
        )
    else:
        taux_occupation = 0

    occupation_complete = (
        total_unites > 0
        and total_occupees == total_unites
    )

    occupation_partielle = (
        total_unites > 0
        and 0 < total_occupees < total_unites
    )

    batiment_libre = (
        total_unites > 0
        and total_occupees == 0
    )

    aucune_unite = total_unites == 0

    # ---------------------------------------------------------
    # CONTEXTE
    # ---------------------------------------------------------

    context = {
        "batiment": batiment,

        # Nouveau système
        "unites": unites,
        "unites_occupees": unites_occupees,
        "unites_libres": unites_libres,
        "unites_reservees": unites_reservees,
        "unites_maintenance": unites_maintenance,

        # Statistiques générales
        "total_unites_batiment": total_unites,
        "unites_occupees_batiment": total_occupees,
        "unites_libres_batiment": total_libres,
        "unites_reservees_batiment": total_reservees,
        "unites_maintenance_batiment": total_maintenance,

        # Types d’unités
        "total_appartements": total_appartements,
        "total_studios": total_studios,
        "total_magasins": total_magasins,
        "total_chambres": total_chambres,

        # Occupation
        "taux_occupation": taux_occupation,
        "occupation_complete": occupation_complete,
        "occupation_partielle": occupation_partielle,
        "batiment_libre": batiment_libre,
        "aucune_unite": aucune_unite,

        # Revenus
        "revenus_mensuels_potentiels": (
            revenus_mensuels_potentiels
        ),
        "revenus_mensuels_actifs": (
            revenus_mensuels_actifs
        ),

        # Anciennes locations
        "anciennes_locations_actives": (
            anciennes_locations_actives
        ),

        # -----------------------------------------------------
        # COMPATIBILITÉ AVEC VOTRE ANCIEN TEMPLATE
        # -----------------------------------------------------

        "chambres": unites,
        "chambres_occupees": unites_occupees,
        "chambres_libres": unites_libres,

        "logements_occupes_batiment": total_occupees,
        "logements_libres_batiment": total_libres,
        "total_logements_batiment": total_unites,
        "total_chambres_batiment": total_chambres,
    }

    return render(
        request,
        "detail_batiment.html",
        context,
    )
from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

from .models import ChambreLogement, Locataire, Location


# ============================================================
# MODIFIER LOGEMENT / CHAMBRE + LOCATAIRE + BAIL
# ============================================================

@login_required(login_url="login")
def modifier_chamb(request, id):

    agence = get_agence(request.user)

    chambre = get_object_or_404(
        ChambreLogement.objects.select_related("batiment"),
        id=id,
        batiment__agence=agence
    )

    batiment = chambre.batiment

    # Bail actif actuel
    bail = Location.objects.filter(
        chambre=chambre,
        batiment=batiment,
        active=True
    ).select_related(
        "locataire"
    ).first()

    # Tous les locataires de l'agence
    locataires = Locataire.objects.filter(
        agence=agence
    ).order_by(
        "nom",
        "prenom"
    )

    if request.method == "POST":

        numero = request.POST.get(
            "numero", ""
        ).strip()

        nom = request.POST.get(
            "nom", ""
        ).strip()

        locataire_id = request.POST.get(
            "locataire_id", ""
        ).strip()

        loyer_raw = request.POST.get(
            "loyer", ""
        ).strip()

        caution_raw = request.POST.get(
            "caution", ""
        ).strip()

        date_debut_raw = request.POST.get(
            "date_debut", ""
        ).strip()

        # --------------------------------------------
        # VALIDATION NUMÉRO
        # --------------------------------------------

        if not numero:
            messages.error(
                request,
                "Le numéro du logement / chambre est obligatoire."
            )

            return redirect(
                "modifier_chambre",
                id=chambre.id
            )

        # Vérifier doublon numéro
        doublon = ChambreLogement.objects.filter(
            batiment=batiment,
            numero=numero
        ).exclude(
            id=chambre.id
        ).exists()

        if doublon:
            messages.error(
                request,
                f"Le numéro {numero} existe déjà dans ce bâtiment."
            )

            return redirect(
                "modifier_chambre",
                id=chambre.id
            )

        # --------------------------------------------
        # CONVERSION LOYER
        # --------------------------------------------

        try:
            loyer = (
                Decimal(loyer_raw)
                if loyer_raw
                else Decimal("0")
            )

        except InvalidOperation:
            messages.error(
                request,
                "Le montant du loyer est invalide."
            )

            return redirect(
                "modifier_chambre",
                id=chambre.id
            )

        # --------------------------------------------
        # CONVERSION CAUTION
        # --------------------------------------------

        try:
            caution = (
                Decimal(caution_raw)
                if caution_raw
                else Decimal("0")
            )

        except InvalidOperation:
            messages.error(
                request,
                "Le montant de la caution est invalide."
            )

            return redirect(
                "modifier_chambre",
                id=chambre.id
            )

        # --------------------------------------------
        # MODIFIER LOGEMENT / CHAMBRE
        # --------------------------------------------

        chambre.numero = numero
        chambre.nom = nom or f"Logement / Chambre {numero}"

        chambre.save(
            update_fields=[
                "numero",
                "nom"
            ]
        )

        # --------------------------------------------
        # SI LOCATAIRE CHOISI
        # --------------------------------------------

        if locataire_id:

            locataire = get_object_or_404(
                Locataire,
                id=locataire_id,
                agence=agence
            )

            # Date début
            if date_debut_raw:
                try:
                    date_debut = date.fromisoformat(
                        date_debut_raw
                    )
                except ValueError:
                    messages.error(
                        request,
                        "La date de début est invalide."
                    )

                    return redirect(
                        "modifier_chambre",
                        id=chambre.id
                    )

            elif bail and bail.date_debut:
                date_debut = bail.date_debut

            else:
                date_debut = date.today()

            # ----------------------------------------
            # MODIFIER BAIL EXISTANT
            # ----------------------------------------

            if bail:

                bail.locataire = locataire
                bail.loyer = loyer
                bail.caution = caution
                bail.numero_appartement = numero
                bail.date_debut = date_debut
                bail.active = True

                bail.save()

            # ----------------------------------------
            # CRÉER NOUVEAU BAIL
            # ----------------------------------------

            else:

                bail = Location.objects.create(
                    agence=agence,
                    batiment=batiment,
                    chambre=chambre,
                    locataire=locataire,
                    numero_appartement=numero,
                    date_debut=date_debut,
                    loyer=loyer,
                    caution=caution,
                    active=True
                )

        # --------------------------------------------
        # AUCUN LOCATAIRE CHOISI
        # --------------------------------------------

        else:

            if bail:
                bail.active = False

                bail.save(
                    update_fields=[
                        "active"
                    ]
                )

        messages.success(
            request,
            "Logement / chambre modifié avec succès."
        )

        return redirect(
            "detail_batiment",
            id=batiment.id
        )

    return render(
        request,
        "modifier_chambre.html",
        {
            "chambre": chambre,
            "batiment": batiment,
            "bail": bail,
            "locataires": locataires,
            "date_aujourdhui": date.today(),
        }
    )


# ============================================================
# SUPPRIMER LOGEMENT / CHAMBRE
# ============================================================
@login_required(login_url="login")
def supprimer_chamb(request, id):

    agence = get_agence(request.user)

    chambre = get_object_or_404(
        ChambreLogement,
        id=id,
        batiment__agence=agence
    )

    batiment = chambre.batiment

    Location.objects.filter(
        chambre=chambre,
        batiment=batiment
    ).delete()

    chambre.delete()

    batiment.nombre_logements = ChambreLogement.objects.filter(
        batiment=batiment,
        actif=True
    ).count()
    batiment.save(update_fields=["nombre_logements"])

    messages.success(request, "Logement/chambre et bail supprimés avec succès.")
    return redirect("detail_batiment", id=batiment.id)





def convertir_decimal(valeur, valeur_par_defaut="0"):
    texte = str(valeur or valeur_par_defaut).strip().replace(" ", "")
    texte = texte.replace(",", ".")

    try:
        return Decimal(texte)
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("Montant invalide.")


def convertir_date(valeur):
    if not valeur:
        return None

    try:
        return date.fromisoformat(valeur)
    except (TypeError, ValueError):
        raise ValueError("Date invalide.")


@login_required(login_url="login")
def ajouter_chambre(request, id):
    """
    Le nom est conservé pour ne pas casser l'ancienne URL.
    Cette vue crée maintenant un appartement, un studio ou un magasin.
    """
    agence = get_agence(request.user)

    batiment = get_object_or_404(
        Batiment.objects.select_related("proprietaire"),
        id=id,
        agence=agence,
    )

    locataires = Locataire.objects.filter(
        agence=agence,
    ).order_by("nom", "prenom")

    if request.method == "POST":
        type_unite = request.POST.get(
            "type_unite",
            UniteLocative.TypeUnite.APPARTEMENT,
        ).strip()

        numero = request.POST.get("numero", "").strip()
        nombre_chambres_brut = request.POST.get(
            "nombre_chambres",
            "1",
        ).strip()

        type_toilette = request.POST.get(
            "type_toilette",
            "",
        ).strip()

        usage_commercial = request.POST.get(
            "usage_commercial",
            "",
        ).strip()

        description = request.POST.get(
            "description",
            "",
        ).strip()

        locataire_id = request.POST.get(
            "locataire_id",
            "",
        ).strip()

        caution_payee = (
            request.POST.get("caution_payee") == "on"
        )

        observation_caution = request.POST.get(
            "observation_caution",
            "",
        ).strip()

        types_valides = {
            choix[0]
            for choix in UniteLocative.TypeUnite.choices
        }

        toilettes_valides = {
            choix[0]
            for choix in UniteLocative.TypeToilette.choices
        }

        usages_valides = {
            choix[0]
            for choix in UniteLocative.UsageCommercial.choices
        }

        erreurs = []

        if type_unite not in types_valides:
            erreurs.append(
                "Le type d'unité sélectionné est invalide."
            )

        if not numero:
            erreurs.append(
                "Veuillez saisir le numéro de l'unité."
            )

        if numero and UniteLocative.objects.filter(
            batiment=batiment,
            numero__iexact=numero,
        ).exists():
            erreurs.append(
                f"L'unité n° {numero} existe déjà dans ce bâtiment."
            )

        try:
            prix_mensuel = convertir_decimal(
                request.POST.get("prix_mensuel"),
            )
            if prix_mensuel < 0:
                erreurs.append(
                    "Le prix mensuel ne peut pas être négatif."
                )
        except ValueError:
            prix_mensuel = Decimal("0")
            erreurs.append(
                "Veuillez saisir un prix mensuel valide."
            )

        try:
            loyer = convertir_decimal(
                request.POST.get("loyer"),
                str(prix_mensuel),
            )
            if loyer < 0:
                erreurs.append(
                    "Le loyer ne peut pas être négatif."
                )
        except ValueError:
            loyer = prix_mensuel
            erreurs.append(
                "Veuillez saisir un loyer valide."
            )

        try:
            caution = convertir_decimal(
                request.POST.get("caution"),
                "0",
            )
            if caution < 0:
                erreurs.append(
                    "La caution ne peut pas être négative."
                )
        except ValueError:
            caution = Decimal("0")
            erreurs.append(
                "Veuillez saisir une caution valide."
            )

        if type_unite == UniteLocative.TypeUnite.APPARTEMENT:
            try:
                nombre_chambres = int(
                    nombre_chambres_brut or "1"
                )
            except (TypeError, ValueError):
                nombre_chambres = 0

            if nombre_chambres < 1:
                erreurs.append(
                    "Un appartement doit avoir au moins une chambre."
                )

            if not type_toilette:
                type_toilette = (
                    UniteLocative.TypeToilette.COMMUNE_APPARTEMENT
                )

        elif type_unite == UniteLocative.TypeUnite.STUDIO:
            nombre_chambres = 0
            usage_commercial = ""

            if not type_toilette:
                type_toilette = (
                    UniteLocative.TypeToilette.PRIVEE_STUDIO
                )

        elif type_unite == UniteLocative.TypeUnite.MAGASIN:
            nombre_chambres = 0

            if not type_toilette:
                type_toilette = (
                    UniteLocative.TypeToilette.PRIVEE_MAGASIN
                )

            if usage_commercial and usage_commercial not in usages_valides:
                erreurs.append(
                    "L'usage commercial sélectionné est invalide."
                )
        else:
            nombre_chambres = 0

        if type_toilette not in toilettes_valides:
            erreurs.append(
                "Le type de toilette sélectionné est invalide."
            )

        try:
            date_debut = convertir_date(
                request.POST.get("date_debut")
            )
            date_fin = convertir_date(
                request.POST.get("date_fin")
            )
            date_caution = convertir_date(
                request.POST.get("date_caution")
            )
        except ValueError as erreur:
            date_debut = None
            date_fin = None
            date_caution = None
            erreurs.append(str(erreur))

        if locataire_id and not date_debut:
            erreurs.append(
                "Veuillez indiquer la date de début du bail."
            )

        if date_debut and date_fin and date_fin < date_debut:
            erreurs.append(
                "La date de fin ne peut pas être antérieure "
                "à la date de début."
            )

        if caution_payee and not date_caution:
            erreurs.append(
                "Veuillez indiquer la date de paiement de la caution."
            )

        locataire = None

        if locataire_id:
            locataire = Locataire.objects.filter(
                id=locataire_id,
                agence=agence,
            ).first()

            if not locataire:
                erreurs.append(
                    "Le locataire sélectionné est invalide."
                )

        if erreurs:
            for erreur in erreurs:
                messages.error(request, erreur)
        else:
            location = None
            erreur_contrat = None

            try:
                with transaction.atomic():
                    unite = UniteLocative.objects.create(
                        batiment=batiment,
                        numero=numero,
                        type_unite=type_unite,
                        nombre_chambres=nombre_chambres,
                        type_toilette=type_toilette,
                        prix_mensuel=prix_mensuel,
                        usage_commercial=(
                            usage_commercial
                            if type_unite
                            == UniteLocative.TypeUnite.MAGASIN
                            else ""
                        ),
                        statut=UniteLocative.Statut.LIBRE,
                        description=description,
                        actif=True,
                    )

                    if locataire:
                        location = Location.objects.create(
                            agence=agence,
                            batiment=batiment,
                            locataire=locataire,
                            unite=unite,
                            chambre=None,
                            numero_appartement=unite.numero,
                            loyer=loyer,
                            caution=caution,
                            caution_payee=caution_payee,
                            date_caution=date_caution,
                            observation_caution=(
                                observation_caution or None
                            ),
                            date_debut=(
                                date_debut
                                or timezone.localdate()
                            ),
                            date_fin=date_fin,
                            active=True,
                        )

                    total_logements = UniteLocative.objects.filter(
                        batiment=batiment,
                        actif=True,
                        type_unite__in=[
                            UniteLocative.TypeUnite.APPARTEMENT,
                            UniteLocative.TypeUnite.STUDIO,
                        ],
                    ).count()

                    Batiment.objects.filter(
                        pk=batiment.pk
                    ).update(
                        nombre_logements=total_logements
                    )

                if location:
                    try:
                        generer_contrat_bail_numerique(
                            location
                        )
                    except Exception as erreur:
                        erreur_contrat = str(erreur)

                if location and erreur_contrat:
                    messages.warning(
                        request,
                        (
                            "L'unité et le bail ont été créés, "
                            "mais le contrat PDF n'a pas pu être "
                            f"généré : {erreur_contrat}"
                        ),
                    )
                elif location:
                    messages.success(
                        request,
                        (
                            "L'unité a été ajoutée, le locataire "
                            "a été affecté et le contrat de bail "
                            "numérique a été généré."
                        ),
                    )
                else:
                    messages.success(
                        request,
                        "L'unité locative a été ajoutée avec succès.",
                    )

                return redirect(
                    "detail_batiment",
                    id=batiment.id,
                )

            except Exception as erreur:
                messages.error(
                    request,
                    f"Impossible d'ajouter l'unité : {erreur}",
                )

    prochain_numero = (
        UniteLocative.objects.filter(
            batiment=batiment,
        ).count()
        + 1
    )

    return render(
        request,
        "ajouter_chambre.html",
        {
            "batiment": batiment,
            "prochain_numero": prochain_numero,
            "locataires": locataires,
            "types_unite": UniteLocative.TypeUnite.choices,
            "types_toilette": UniteLocative.TypeToilette.choices,
            "usages_commerciaux": (
                UniteLocative.UsageCommercial.choices
            ),
            "date_du_jour": timezone.localdate(),
        },
    )




def _decimal_formulaire(valeur, valeur_par_defaut="0"):
    """
    Convertit une valeur du formulaire en Decimal.
    Accepte les espaces, les virgules et les points.
    """
    texte = str(
        valeur if valeur not in (None, "") else valeur_par_defaut
    ).strip()

    texte = texte.replace(" ", "").replace(",", ".")

    try:
        return Decimal(texte)
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError("Veuillez saisir un montant valide.")


def _date_formulaire(valeur, obligatoire=False):
    """
    Convertit une date HTML YYYY-MM-DD en objet date.
    """
    if not valeur:
        if obligatoire:
            raise ValidationError(
                "Veuillez indiquer la date de début du bail."
            )
        return None

    try:
        return date.fromisoformat(valeur)
    except (TypeError, ValueError):
        raise ValidationError("Veuillez saisir une date valide.")


@login_required(login_url="login")
def affecter_unite_locataire(request, unite_id):
    agence = get_agence(request.user)

    unite = get_object_or_404(
        UniteLocative.objects.select_related(
            "batiment",
            "batiment__proprietaire",
        ),
        id=unite_id,
        batiment__agence=agence,
        actif=True,
    )

    batiment = unite.batiment

    bail_actif_existant = Location.objects.filter(
        unite=unite,
        active=True,
    ).select_related(
        "locataire",
    ).first()

    if bail_actif_existant:
        messages.warning(
            request,
            (
                f"L’unité n° {unite.numero} est déjà occupée par "
                f"{bail_actif_existant.locataire.nom} "
                f"{bail_actif_existant.locataire.prenom}."
            ),
        )
        return redirect(
            "detail_batiment",
            id=batiment.id,
        )

    if unite.statut != UniteLocative.Statut.LIBRE:
        messages.warning(
            request,
            (
                f"L’unité n° {unite.numero} n’est pas disponible. "
                f"Son statut actuel est : "
                f"{unite.get_statut_display()}."
            ),
        )
        return redirect(
            "detail_batiment",
            id=batiment.id,
        )

    locataires = Locataire.objects.filter(
        agence=agence,
    ).order_by(
        "nom",
        "prenom",
    )

    if request.method == "POST":
        locataire_id = request.POST.get(
            "locataire_id",
            "",
        ).strip()

        caution_payee = (
            request.POST.get("caution_payee") == "on"
        )

        observation_caution = request.POST.get(
            "observation_caution",
            "",
        ).strip()

        erreurs = []

        locataire = None

        if not locataire_id:
            erreurs.append(
                "Veuillez sélectionner un locataire."
            )
        else:
            locataire = Locataire.objects.filter(
                id=locataire_id,
                agence=agence,
            ).first()

            if not locataire:
                erreurs.append(
                    "Le locataire sélectionné est invalide."
                )

        try:
            loyer = _decimal_formulaire(
                request.POST.get("loyer"),
                unite.prix_mensuel,
            )

            if loyer < 0:
                erreurs.append(
                    "Le loyer ne peut pas être négatif."
                )

        except ValidationError as erreur:
            loyer = unite.prix_mensuel
            erreurs.extend(erreur.messages)

        try:
            caution = _decimal_formulaire(
                request.POST.get("caution"),
                "0",
            )

            if caution < 0:
                erreurs.append(
                    "La caution ne peut pas être négative."
                )

        except ValidationError as erreur:
            caution = Decimal("0")
            erreurs.extend(erreur.messages)

        try:
            date_debut = _date_formulaire(
                request.POST.get("date_debut"),
                obligatoire=True,
            )

            date_fin = _date_formulaire(
                request.POST.get("date_fin"),
            )

            date_caution = _date_formulaire(
                request.POST.get("date_caution"),
            )

        except ValidationError as erreur:
            date_debut = None
            date_fin = None
            date_caution = None
            erreurs.extend(erreur.messages)

        if (
            date_debut
            and date_fin
            and date_fin < date_debut
        ):
            erreurs.append(
                "La date de fin ne peut pas être antérieure "
                "à la date de début."
            )

        if caution_payee and not date_caution:
            erreurs.append(
                "Veuillez indiquer la date de paiement de la caution."
            )

        if erreurs:
            for erreur in erreurs:
                messages.error(request, erreur)

        else:
            location = None
            erreur_contrat = None

            try:
                with transaction.atomic():
                    unite_verrouillee = (
                        UniteLocative.objects
                        .select_for_update()
                        .select_related("batiment")
                        .get(
                            id=unite.id,
                            batiment__agence=agence,
                            actif=True,
                        )
                    )

                    bail_concurrent = Location.objects.filter(
                        unite=unite_verrouillee,
                        active=True,
                    ).exists()

                    if (
                        bail_concurrent
                        or unite_verrouillee.statut
                        != UniteLocative.Statut.LIBRE
                    ):
                        raise ValidationError(
                            (
                                "Cette unité vient d’être affectée "
                                "ou n’est plus disponible."
                            )
                        )

                    location = Location(
                        agence=agence,
                        batiment=batiment,
                        locataire=locataire,
                        unite=unite_verrouillee,
                        chambre=None,
                        numero_appartement=(
                            unite_verrouillee.numero
                        ),
                        loyer=loyer,
                        caution=caution,
                        caution_payee=caution_payee,
                        date_caution=date_caution,
                        observation_caution=(
                            observation_caution or None
                        ),
                        date_debut=date_debut,
                        date_fin=date_fin,
                        active=True,
                    )

                    location.full_clean()
                    location.save()

                    UniteLocative.objects.filter(
                        pk=unite_verrouillee.pk,
                    ).update(
                        statut=UniteLocative.Statut.OCCUPE,
                    )

                try:
                    generer_contrat_bail_numerique(
                        location
                    )

                    location.refresh_from_db(
                        fields=[
                            "contrat_bail_numerique",
                            "date_generation_contrat",
                        ]
                    )

                except Exception as erreur:
                    erreur_contrat = str(erreur)

                if erreur_contrat:
                    messages.warning(
                        request,
                        (
                            "Le locataire a été affecté et le bail "
                            "a été enregistré, mais le contrat PDF "
                            "n’a pas pu être généré : "
                            f"{erreur_contrat}"
                        ),
                    )
                else:
                    messages.success(
                        request,
                        (
                            f"{locataire.nom} {locataire.prenom} "
                            f"a été affecté à l’unité n° "
                            f"{unite.numero}. Le contrat de bail "
                            "numérique a été généré."
                        ),
                    )

                return redirect(
                    "detail_batiment",
                    id=batiment.id,
                )

            except ValidationError as erreur:
                for message in erreur.messages:
                    messages.error(request, message)

            except Exception as erreur:
                messages.error(
                    request,
                    (
                        "Impossible d’affecter le locataire : "
                        f"{erreur}"
                    ),
                )

    return render(
        request,
        "affecter_unite_locataire.html",
        {
            "agence": agence,
            "batiment": batiment,
            "unite": unite,
            "locataires": locataires,
            "date_du_jour": timezone.localdate(),
        },
    )








@login_required(login_url="login")
def supprimer_chambre(request, id):

    agence = get_agence(request.user)

    chambre = get_object_or_404(
        ChambreLogement,
        id=id,
        batiment__agence=agence
    )

    batiment = chambre.batiment

    if chambre.locations.filter(active=True).exists():
        messages.error(
            request,
            "Impossible de supprimer : ce logement/chambre a un bail actif."
        )
        return redirect("detail_batiment", id=batiment.id)

    chambre.delete()

    batiment.nombre_logements = ChambreLogement.objects.filter(
        batiment=batiment
    ).count()
    batiment.save(update_fields=["nombre_logements"])

    messages.success(request, "Logement / chambre supprimé avec succès.")
    return redirect("detail_batiment", id=batiment.id)



@login_required(login_url="login")
def modifier_chambre(request, id):

    agence = get_agence(request.user)

    chambre = get_object_or_404(
        ChambreLogement,
        id=id,
        batiment__agence=agence
    )

    batiment = chambre.batiment
    bail = chambre.locations.filter(active=True).first()

    locataires = Locataire.objects.filter(
        agence=agence
    ).order_by("nom", "prenom")

    if request.method == "POST":
        numero = request.POST.get("numero", "").strip()
        nom = request.POST.get("nom", "").strip()
        locataire_id = request.POST.get("locataire_id")
        loyer = request.POST.get("loyer") or 0
        caution = request.POST.get("caution") or 0

        if not numero:
            messages.error(request, "Le numéro est obligatoire.")
            return redirect("modifier_chambre", id=chambre.id)

        chambre.numero = numero
        chambre.nom = nom or f"Logement / Chambre {numero}"
        chambre.save()

        if locataire_id:
            locataire = get_object_or_404(
                Locataire,
                id=locataire_id,
                agence=agence
            )

            if bail:
                bail.locataire = locataire
                bail.loyer = loyer
                bail.caution = caution
                bail.numero_appartement = numero
                bail.active = True
                bail.save()
            else:
                Location.objects.create(
                    agence=agence,
                    batiment=batiment,
                    chambre=chambre,
                    locataire=locataire,
                    numero_appartement=numero,
                    loyer=loyer,
                    caution=caution,
                    active=True
                )

        else:
            if bail:
                bail.active = False
                bail.save(update_fields=["active"])

        messages.success(request, "Logement / chambre modifié avec succès.")
        return redirect("detail_batiment", id=batiment.id)

    return render(request, "modifier_chambre.html", {
        "chambre": chambre,
        "batiment": batiment,
        "bail": bail,
        "locataires": locataires,
    })


from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

from .models import ChambreLogement, Locataire, Location


@login_required(login_url="login")
def modifier_chambre(request, id):

    agence = get_agence(request.user)

    # ==========================================
    # RÉCUPÉRER LA CHAMBRE / LOGEMENT
    # ==========================================
    chambre = get_object_or_404(
        ChambreLogement.objects.select_related("batiment"),
        id=id,
        batiment__agence=agence
    )

    batiment = chambre.batiment

    # ==========================================
    # BAIL ACTIF ACTUEL
    # ==========================================
    bail = chambre.locations.filter(
        active=True
    ).select_related(
        "locataire"
    ).first()

    # ==========================================
    # TOUS LES LOCATAIRES DE L'AGENCE
    # ==========================================
    locataires = Locataire.objects.filter(
        agence=agence
    ).order_by(
        "nom",
        "prenom"
    )

    # ==========================================
    # POST
    # ==========================================
    if request.method == "POST":

        numero = request.POST.get(
            "numero", ""
        ).strip()

        nom = request.POST.get(
            "nom", ""
        ).strip()

        locataire_id = request.POST.get(
            "locataire_id", ""
        ).strip()

        loyer_raw = request.POST.get(
            "loyer", ""
        ).strip()

        caution_raw = request.POST.get(
            "caution", ""
        ).strip()

        date_debut_raw = request.POST.get(
            "date_debut", ""
        ).strip()

        # ======================================
        # VALIDATION NUMÉRO
        # ======================================
        if not numero:
            messages.error(
                request,
                "Le numéro du logement ou de la chambre est obligatoire."
            )

            return redirect(
                "modifier_chambre",
                id=chambre.id
            )

        # ======================================
        # VÉRIFIER DOUBLON NUMÉRO
        # ======================================
        numero_existe = ChambreLogement.objects.filter(
            batiment=batiment,
            numero=numero
        ).exclude(
            id=chambre.id
        ).exists()

        if numero_existe:
            messages.error(
                request,
                f"Le numéro {numero} existe déjà dans ce bâtiment."
            )

            return redirect(
                "modifier_chambre",
                id=chambre.id
            )

        # ======================================
        # CONVERSION LOYER
        # ======================================
        try:
            loyer = Decimal(loyer_raw) if loyer_raw else Decimal("0")
        except InvalidOperation:
            messages.error(
                request,
                "Le montant du loyer est invalide."
            )

            return redirect(
                "modifier_chambre",
                id=chambre.id
            )

        # ======================================
        # CONVERSION CAUTION
        # ======================================
        try:
            caution = Decimal(caution_raw) if caution_raw else Decimal("0")
        except InvalidOperation:
            messages.error(
                request,
                "Le montant de la caution est invalide."
            )

            return redirect(
                "modifier_chambre",
                id=chambre.id
            )

        # ======================================
        # MODIFIER CHAMBRE / LOGEMENT
        # ======================================
        chambre.numero = numero

        chambre.nom = (
            nom
            or f"Logement / Chambre {numero}"
        )

        chambre.save(
            update_fields=[
                "numero",
                "nom"
            ]
        )

        # ======================================
        # SI UN LOCATAIRE EST CHOISI
        # ======================================
        if locataire_id:

            locataire = get_object_or_404(
                Locataire,
                id=locataire_id,
                agence=agence
            )

            # ==================================
            # DATE DE DÉBUT OBLIGATOIRE
            # ==================================
            if date_debut_raw:
                date_debut = date.fromisoformat(
                    date_debut_raw
                )

            elif bail and bail.date_debut:
                date_debut = bail.date_debut

            else:
                date_debut = date.today()

            # ==================================
            # MODIFIER BAIL EXISTANT
            # ==================================
            if bail:

                bail.locataire = locataire
                bail.loyer = loyer
                bail.caution = caution
                bail.numero_appartement = numero
                bail.date_debut = date_debut
                bail.active = True

                bail.save()

            # ==================================
            # CRÉER NOUVEAU BAIL
            # ==================================
            else:

                bail = Location.objects.create(
                    agence=agence,
                    batiment=batiment,
                    chambre=chambre,
                    locataire=locataire,
                    numero_appartement=numero,
                    date_debut=date_debut,
                    loyer=loyer,
                    caution=caution,
                    active=True
                )

        # ======================================
        # AUCUN LOCATAIRE CHOISI
        # ======================================
        else:

            if bail:
                bail.active = False

                bail.save(
                    update_fields=[
                        "active"
                    ]
                )

        messages.success(
            request,
            "Logement / chambre et occupation modifiés avec succès."
        )

        return redirect(
            "detail_batiment",
            id=batiment.id
        )

    # ==========================================
    # AFFICHAGE GET
    # ==========================================
    return render(
        request,
        "modifier_chambre.html",
        {
            "chambre": chambre,
            "batiment": batiment,
            "bail": bail,
            "locataires": locataires,
            "date_aujourdhui": date.today(),
        }
    )






@login_required(login_url="login")
def modifier_batiment(request, id):
    agence = get_agence(request.user)

    batiment = get_object_or_404(
        Batiment.objects.select_related(
            "proprietaire",
            "agence",
        ),
        id=id,
        agence=agence,
    )

    proprietaires = Proprietaire.objects.filter(
        agence=agence,
    ).order_by(
        "nom",
        "prenom",
    )

    if request.method == "POST":
        proprietaire_id = request.POST.get(
            "proprietaire",
            "",
        ).strip()

        code_batiment = request.POST.get(
            "code_batiment",
            "",
        ).strip()

        nom = request.POST.get(
            "nom",
            "",
        ).strip()

        adresse = request.POST.get(
            "adresse",
            "",
        ).strip()

        ville = request.POST.get(
            "ville",
            "",
        ).strip()

        description = request.POST.get(
            "description",
            "",
        ).strip()

        actif = (
            request.POST.get("actif", "True")
            == "True"
        )

        erreurs = []

        # Vérification du propriétaire
        proprietaire = None

        if not proprietaire_id:
            erreurs.append(
                "Veuillez sélectionner un propriétaire."
            )
        else:
            proprietaire = Proprietaire.objects.filter(
                id=proprietaire_id,
                agence=agence,
            ).first()

            if not proprietaire:
                erreurs.append(
                    "Le propriétaire sélectionné est invalide."
                )

        # Vérification des champs obligatoires
        if not code_batiment:
            erreurs.append(
                "Veuillez saisir le code du bâtiment."
            )

        if not nom:
            erreurs.append(
                "Veuillez saisir le nom du bâtiment."
            )

        if not ville:
            erreurs.append(
                "Veuillez saisir la ville du bâtiment."
            )

        if not adresse:
            erreurs.append(
                "Veuillez saisir l’adresse du bâtiment."
            )

        # Vérifier si le code existe déjà dans l’agence
        if (
            code_batiment
            and Batiment.objects.filter(
                agence=agence,
                code_batiment__iexact=code_batiment,
            )
            .exclude(pk=batiment.pk)
            .exists()
        ):
            erreurs.append(
                (
                    f"Le code bâtiment « {code_batiment} » "
                    "est déjà utilisé dans cette agence."
                )
            )

        if erreurs:
            for erreur in erreurs:
                messages.error(
                    request,
                    erreur,
                )

        else:
            try:
                with transaction.atomic():
                    # Recalcul automatique du nombre d’unités
                    total_unites = UniteLocative.objects.filter(
                        batiment=batiment,
                        actif=True,
                    ).count()

                    batiment.proprietaire = proprietaire
                    batiment.code_batiment = code_batiment
                    batiment.nom = nom
                    batiment.adresse = adresse
                    batiment.ville = ville
                    batiment.nombre_logements = total_unites
                    batiment.description = description
                    batiment.actif = actif

                    # Vérifier les contraintes du modèle
                    batiment.full_clean()

                    batiment.save(
                        update_fields=[
                            "proprietaire",
                            "code_batiment",
                            "nom",
                            "adresse",
                            "ville",
                            "nombre_logements",
                            "description",
                            "actif",
                        ]
                    )

                messages.success(
                    request,
                    (
                        f"Le bâtiment « {batiment.nom} » "
                        "a été modifié avec succès."
                    ),
                )

                return redirect(
                    "detail_batiment",
                    id=batiment.id,
                )

            except ValidationError as erreur:
                if hasattr(erreur, "message_dict"):
                    for champ, messages_erreur in (
                        erreur.message_dict.items()
                    ):
                        for message_erreur in messages_erreur:
                            messages.error(
                                request,
                                message_erreur,
                            )
                else:
                    for message_erreur in erreur.messages:
                        messages.error(
                            request,
                            message_erreur,
                        )

            except Exception as erreur:
                messages.error(
                    request,
                    (
                        "Impossible de modifier le bâtiment : "
                        f"{erreur}"
                    ),
                )

    total_unites_actives = UniteLocative.objects.filter(
        batiment=batiment,
        actif=True,
    ).count()

    return render(
        request,
        "modifier_batiment.html",
        {
            "batiment": batiment,
            "proprietaires": proprietaires,
            "total_unites_actives": total_unites_actives,
        },
    )



@login_required(login_url="login")
def locataires(request):
    agence = get_agence(request.user)
    q = request.GET.get("q", "").strip()

    locataires = Locataire.objects.filter(
        agence=agence
    ).order_by("-date_creation")

    if q:
        locataires = locataires.filter(
            Q(nom__icontains=q) |
            Q(prenom__icontains=q) |
            Q(telephone__icontains=q) |
            Q(email__icontains=q) |
            Q(numero_piece_identite__icontains=q)
        )

    # Montant total des cautions payées
    total_cautions_payees = Locataire.objects.filter(
        agence=agence,
        caution_payee=True
    ).aggregate(
        total=Sum("caution")
    )["total"] or 0

    return render(request, "locataires.html", {
        "locataires": locataires,
        "q": q,
        "total_cautions_payees": total_cautions_payees,
    })



from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

from .models import Locataire


@login_required(login_url="login")
def locations(request):
    agence = get_agence(request.user)

    q = request.GET.get("q", "").strip()
    statut = request.GET.get("statut", "").strip()
    caution = request.GET.get("caution", "").strip()
    batiment_id = request.GET.get("batiment", "").strip()
    tri = request.GET.get("tri", "-date_debut").strip()

    queryset = (
        Location.objects
        .filter(agence=agence)
        .select_related(
            "locataire",
            "batiment",
            "unite",
            "chambre",
        )
    )

    if q:
        queryset = queryset.filter(
            Q(locataire__nom__icontains=q)
            | Q(locataire__prenom__icontains=q)
            | Q(locataire__telephone__icontains=q)
            | Q(locataire__email__icontains=q)
            | Q(batiment__nom__icontains=q)
            | Q(batiment__adresse__icontains=q)
            | Q(batiment__ville__icontains=q)
            | Q(numero_appartement__icontains=q)
            | Q(unite__numero__icontains=q)
        )

    if statut == "active":
        queryset = queryset.filter(active=True)

    elif statut == "terminee":
        queryset = queryset.filter(active=False)

    if caution == "payee":
        queryset = queryset.filter(caution_payee=True)

    elif caution == "non_payee":
        queryset = queryset.filter(caution_payee=False)

    if batiment_id.isdigit():
        queryset = queryset.filter(
            batiment_id=int(batiment_id),
        )

    tris_autorises = {
        "-date_debut": ("-date_debut", "-id"),
        "date_debut": ("date_debut", "id"),
        "locataire": (
            "locataire__nom",
            "locataire__prenom",
            "-date_debut",
        ),
        "batiment": (
            "batiment__nom",
            "-date_debut",
        ),
        "-loyer": (
            "-loyer",
            "-date_debut",
        ),
        "loyer": (
            "loyer",
            "-date_debut",
        ),
    }

    queryset = queryset.order_by(
        *tris_autorises.get(
            tri,
            tris_autorises["-date_debut"],
        )
    )

    stats_queryset = Location.objects.filter(
        agence=agence,
    )

    total_locations = stats_queryset.count()

    total_actives = stats_queryset.filter(
        active=True,
    ).count()

    total_terminees = (
        total_locations - total_actives
    )

    cautions_non_payees = stats_queryset.filter(
        active=True,
        caution_payee=False,
    ).count()

    revenus_mensuels_actifs = (
        stats_queryset
        .filter(active=True)
        .aggregate(total=Sum("loyer"))
        .get("total")
        or 0
    )

    paginator = Paginator(
        queryset,
        40,
    )

    page_obj = paginator.get_page(
        request.GET.get("page"),
    )

    batiments_filtre = (
        Batiment.objects
        .filter(
            agence=agence,
            actif=True,
        )
        .order_by("nom")
        .only(
            "id",
            "nom",
        )
    )

    return render(
        request,
        "locations.html",
        {
            "locations": page_obj.object_list,
            "page_obj": page_obj,
            "total_locations": total_locations,
            "total_actives": total_actives,
            "total_terminees": total_terminees,
            "cautions_non_payees": cautions_non_payees,
            "revenus_mensuels_actifs": revenus_mensuels_actifs,
            "batiments_filtre": batiments_filtre,
            "q": q,
            "statut": statut,
            "caution": caution,
            "batiment_id": batiment_id,
            "tri": tri,
        },
    )

@login_required(login_url="login")
def modifier_location(request, id):
    """
    Modifie une location existante.

    Sécurités incluses :
    - la location doit appartenir à l'agence connectée ;
    - le bâtiment, le locataire et l'unité doivent appartenir à la même agence ;
    - une unité ne peut pas avoir deux baux actifs ;
    - l'ancienne unité redevient libre lorsqu'elle est remplacée ;
    - l'unité sélectionnée devient occupée lorsque le bail est actif ;
    - le contrat PDF existant est régénéré après modification.
    """
    agence = get_agence(request.user)

    location = get_object_or_404(
        Location.objects.select_related(
            "agence",
            "batiment",
            "locataire",
            "unite",
            "chambre",
        ),
        id=id,
        agence=agence,
    )

    ancienne_unite_id = location.unite_id
    contrat_existant = bool(
        location.contrat_bail_numerique
    )

    batiments = Batiment.objects.filter(
        agence=agence,
        actif=True,
    ).order_by("nom")

    locataires = Locataire.objects.filter(
        agence=agence,
    ).order_by("nom", "prenom")

    if request.method == "POST":
        batiment_id = request.POST.get(
            "batiment",
            "",
        ).strip()

        locataire_id = request.POST.get(
            "locataire",
            "",
        ).strip()

        unite_id = request.POST.get(
            "unite",
            "",
        ).strip()

        numero_appartement = request.POST.get(
            "numero_appartement",
            "",
        ).strip()

        loyer_brut = request.POST.get(
            "loyer",
            "",
        ).strip()

        caution_brute = request.POST.get(
            "caution",
            "",
        ).strip()

        caution_payee = (
            request.POST.get("caution_payee")
            in {
                "on",
                "true",
                "True",
                "1",
                "oui",
            }
        )

        date_caution_brute = request.POST.get(
            "date_caution",
            "",
        ).strip()

        observation_caution = request.POST.get(
            "observation_caution",
            "",
        ).strip()

        date_debut_brute = request.POST.get(
            "date_debut",
            "",
        ).strip()

        date_fin_brute = request.POST.get(
            "date_fin",
            "",
        ).strip()

        active = (
            request.POST.get("active", "True")
            == "True"
        )

        erreurs = []

        # -------------------------------------------------
        # Vérification du bâtiment
        # -------------------------------------------------
        batiment = None

        if not batiment_id:
            erreurs.append(
                "Veuillez sélectionner un bâtiment."
            )
        else:
            batiment = Batiment.objects.filter(
                id=batiment_id,
                agence=agence,
            ).first()

            if not batiment:
                erreurs.append(
                    "Le bâtiment sélectionné est invalide."
                )

        # -------------------------------------------------
        # Vérification du locataire
        # -------------------------------------------------
        locataire = None

        if not locataire_id:
            erreurs.append(
                "Veuillez sélectionner un locataire."
            )
        else:
            locataire = Locataire.objects.filter(
                id=locataire_id,
                agence=agence,
            ).first()

            if not locataire:
                erreurs.append(
                    "Le locataire sélectionné est invalide."
                )

        # -------------------------------------------------
        # Vérification de l'unité
        # -------------------------------------------------
        unite = None

        if unite_id:
            unite = (
                UniteLocative.objects
                .select_related("batiment")
                .filter(
                    id=unite_id,
                    batiment__agence=agence,
                    actif=True,
                )
                .first()
            )

            if not unite:
                erreurs.append(
                    "L’unité sélectionnée est invalide."
                )

            elif (
                batiment
                and unite.batiment_id != batiment.id
            ):
                erreurs.append(
                    (
                        "L’unité sélectionnée n’appartient pas "
                        "au bâtiment choisi."
                    )
                )

        elif active and not location.chambre_id:
            erreurs.append(
                (
                    "Veuillez sélectionner une unité pour "
                    "un bail actif."
                )
            )

        # Empêcher deux locations actives sur la même unité.
        if unite and active:
            unite_deja_occupee = (
                Location.objects
                .filter(
                    agence=agence,
                    unite=unite,
                    active=True,
                )
                .exclude(pk=location.pk)
                .exists()
            )

            if unite_deja_occupee:
                erreurs.append(
                    (
                        f"L’unité n° {unite.numero} possède déjà "
                        "un bail actif."
                    )
                )

        # -------------------------------------------------
        # Vérification des montants
        # -------------------------------------------------
        loyer = Decimal("0")
        caution = Decimal("0")

        try:
            loyer = Decimal(
                loyer_brut.replace(" ", "")
                or "0"
            )

            if loyer <= 0:
                erreurs.append(
                    "Le loyer doit être supérieur à zéro."
                )

        except InvalidOperation:
            erreurs.append(
                "Le montant du loyer est invalide."
            )

        try:
            caution = Decimal(
                caution_brute.replace(" ", "")
                or "0"
            )

            if caution < 0:
                erreurs.append(
                    "La caution ne peut pas être négative."
                )

        except InvalidOperation:
            erreurs.append(
                "Le montant de la caution est invalide."
            )

        # -------------------------------------------------
        # Vérification des dates
        # -------------------------------------------------
        date_debut = parse_date(
            date_debut_brute
        )

        date_fin = (
            parse_date(date_fin_brute)
            if date_fin_brute
            else None
        )

        date_caution = (
            parse_date(date_caution_brute)
            if date_caution_brute
            else None
        )

        if not date_debut:
            erreurs.append(
                "La date de début est obligatoire."
            )

        if (
            date_debut
            and date_fin
            and date_fin < date_debut
        ):
            erreurs.append(
                (
                    "La date de fin ne peut pas être "
                    "antérieure à la date de début."
                )
            )

        if caution_payee and not date_caution:
            date_caution = timezone.localdate()

        if not caution_payee:
            date_caution = None

        # Un bail terminé doit avoir une date de fin.
        if not active and not date_fin:
            date_fin = timezone.localdate()

        # Un bail réactivé peut redevenir sans date de fin.
        if active and date_fin and date_fin < timezone.localdate():
            erreurs.append(
                (
                    "Un bail actif ne peut pas avoir une date "
                    "de fin déjà passée."
                )
            )

        if erreurs:
            for erreur in erreurs:
                messages.error(
                    request,
                    erreur,
                )

        else:
            try:
                with transaction.atomic():
                    location_verrouillee = (
                        Location.objects
                        .select_for_update()
                        .select_related(
                            "unite",
                            "batiment",
                            "locataire",
                        )
                        .get(
                            pk=location.pk,
                            agence=agence,
                        )
                    )

                    ancienne_unite = None

                    if location_verrouillee.unite_id:
                        ancienne_unite = (
                            UniteLocative.objects
                            .select_for_update()
                            .filter(
                                pk=location_verrouillee.unite_id,
                                batiment__agence=agence,
                            )
                            .first()
                        )

                    nouvelle_unite = None

                    if unite:
                        nouvelle_unite = (
                            UniteLocative.objects
                            .select_for_update()
                            .get(
                                pk=unite.pk,
                                batiment__agence=agence,
                            )
                        )

                        conflit = (
                            Location.objects
                            .select_for_update()
                            .filter(
                                agence=agence,
                                unite=nouvelle_unite,
                                active=True,
                            )
                            .exclude(
                                pk=location_verrouillee.pk
                            )
                            .exists()
                        )

                        if active and conflit:
                            raise ValidationError(
                                (
                                    f"L’unité n° "
                                    f"{nouvelle_unite.numero} "
                                    "vient d’être attribuée à "
                                    "un autre bail actif."
                                )
                            )

                    # Mettre à jour la location.
                    location_verrouillee.batiment = batiment
                    location_verrouillee.locataire = locataire
                    location_verrouillee.unite = nouvelle_unite

                    if nouvelle_unite:
                        location_verrouillee.chambre = None
                        location_verrouillee.numero_appartement = (
                            nouvelle_unite.numero
                        )
                    else:
                        location_verrouillee.numero_appartement = (
                            numero_appartement or None
                        )

                    location_verrouillee.loyer = loyer
                    location_verrouillee.caution = caution
                    location_verrouillee.caution_payee = (
                        caution_payee
                    )
                    location_verrouillee.date_caution = (
                        date_caution
                    )
                    location_verrouillee.observation_caution = (
                        observation_caution or None
                    )
                    location_verrouillee.date_debut = date_debut
                    location_verrouillee.date_fin = date_fin
                    location_verrouillee.active = active

                    location_verrouillee.full_clean()
                    location_verrouillee.save()

                    # Libérer l'ancienne unité lorsqu'elle change
                    # ou lorsque le bail devient inactif.
                    if ancienne_unite and (
                        ancienne_unite.pk
                        != getattr(
                            nouvelle_unite,
                            "pk",
                            None,
                        )
                        or not active
                    ):
                        UniteLocative.objects.filter(
                            pk=ancienne_unite.pk,
                        ).update(
                            statut=UniteLocative.Statut.LIBRE,
                        )

                    # Occuper la nouvelle unité si le bail est actif.
                    if nouvelle_unite:
                        nouveau_statut = (
                            UniteLocative.Statut.OCCUPE
                            if active
                            else UniteLocative.Statut.LIBRE
                        )

                        UniteLocative.objects.filter(
                            pk=nouvelle_unite.pk,
                        ).update(
                            statut=nouveau_statut,
                        )

                    location = location_verrouillee

                # Régénérer le contrat uniquement s'il existait déjà.
                if contrat_existant:
                    try:
                        generer_contrat_bail_numerique(
                            location,
                            forcer=True,
                        )

                    except Exception as erreur_contrat:
                        messages.warning(
                            request,
                            (
                                "La location a été modifiée, mais "
                                "le contrat PDF n’a pas pu être "
                                f"régénéré : {erreur_contrat}"
                            ),
                        )

                messages.success(
                    request,
                    (
                        "La location a été modifiée avec succès."
                    ),
                )

                return redirect(
                    "locations",
                )

            except ValidationError as erreur:
                if hasattr(erreur, "message_dict"):
                    for messages_erreur in (
                        erreur.message_dict.values()
                    ):
                        for message_erreur in messages_erreur:
                            messages.error(
                                request,
                                message_erreur,
                            )
                else:
                    for message_erreur in erreur.messages:
                        messages.error(
                            request,
                            message_erreur,
                        )

            except Exception as erreur:
                messages.error(
                    request,
                    (
                        "Impossible de modifier la location : "
                        f"{erreur}"
                    ),
                )

    # -------------------------------------------------
    # Unités affichées dans le formulaire
    # -------------------------------------------------
    batiment_selectionne_id = (
        request.POST.get("batiment")
        if request.method == "POST"
        else location.batiment_id
    )

    unites = UniteLocative.objects.none()

    if str(batiment_selectionne_id).isdigit():
        unites = (
            UniteLocative.objects
            .filter(
                batiment_id=int(
                    batiment_selectionne_id
                ),
                batiment__agence=agence,
                actif=True,
            )
            .filter(
                # Afficher les unités libres et l'unité actuelle.
                # Le filtrage précis est fait en Python ci-dessous.
            )
            .order_by(
                "type_unite",
                "numero",
            )
        )

        unites = [
            unite
            for unite in unites
            if (
                unite.statut
                == UniteLocative.Statut.LIBRE
                or unite.pk == location.unite_id
            )
        ]

    return render(
        request,
        "modifier_location.html",
        {
            "location": location,
            "batiments": batiments,
            "locataires": locataires,
            "unites": unites,
            "ancienne_unite_id": ancienne_unite_id,
        },
    )




from django.db.models import Sum
from django.utils import timezone
from django.core.paginator import Paginator


from django.db.models import Sum
from django.utils import timezone


@login_required(login_url="login")
def paiements(request):
    agence = get_agence(request.user)

    paiements = Paiement.objects.filter(
        agence=agence
    ).select_related(
        "location",
        "location__locataire",
        "location__batiment",
        "proprietaire",
        "employe"
    )

    total_paiements = paiements.count()

    montant_total = paiements.aggregate(
        total=Sum("montant")
    )["total"] or 0

    total_commission_agence = paiements.aggregate(
        total=Sum("commission_agence")
    )["total"] or 0

    total_proprietaires = paiements.aggregate(
        total=Sum("montant_proprietaire")
    )["total"] or 0

    now = timezone.now()

    paiements_mois = paiements.filter(
        date_paiement__month=now.month,
        date_paiement__year=now.year
    ).count()

    montant_mois = paiements.filter(
        date_paiement__month=now.month,
        date_paiement__year=now.year
    ).aggregate(
        total=Sum("montant")
    )["total"] or 0

    return render(request, "paiements.html", {
        "paiements": paiements,
        "total_paiements": total_paiements,
        "montant_total": montant_total,
        "total_commission_agence": total_commission_agence,
        "total_proprietaires": total_proprietaires,
        "paiements_mois": paiements_mois,
        "montant_mois": montant_mois,
    })




@login_required(login_url="login")
def versements(request):
    agence = get_agence(request.user)

    versements = Paiement.objects.filter(
        agence=agence,
        statut="paye"
    )

    total_versements = (
        versements.aggregate(
            total=Sum("montant")
        )["total"] or 0
    )

    return render(
        request,
        "versements.html",
        {
            "agence": agence,
            "versements": versements,
            "total_versements": total_versements,
        }
    )


@login_required(login_url="login")
def rapports(request):
    agence = get_agence(request.user)

    proprietaires = Proprietaire.objects.filter(
        agence=agence
    ).order_by(
        "nom",
        "prenom"
    )

    return render(request, "rapports.html", {
        "agence": agence,
        "proprietaires": proprietaires,
    })


@login_required(login_url="login")
def ajouter_proprietaire(request):
    agence = get_agence(request.user)

    if request.method == "POST":

        code_client = request.POST.get("code_client")
        nom = request.POST.get("nom")
        prenom = request.POST.get("prenom")
        telephone = request.POST.get("telephone")
        email = request.POST.get("email")
        adresse = request.POST.get("adresse")

        resident = request.POST.get("resident") == "True"

        if Proprietaire.objects.filter(
            code_client=code_client
        ).exists():

            messages.error(
                request,
                "Ce code client existe déjà."
            )

            return redirect("ajouter_proprietaire")

        Proprietaire.objects.create(
            agence=agence,
            code_client=code_client,
            nom=nom,
            prenom=prenom,
            telephone=telephone,
            email=email,
            adresse=adresse,
            resident=resident
        )

        messages.success(
            request,
            "Propriétaire ajouté avec succès."
        )

        return redirect("proprietaires")

    return render(
        request,
        "ajouter_proprietaire.html"
    )


@login_required(login_url="login")
def detail_proprietaire(request, id):

    agence = get_agence(request.user)

    proprietaire = get_object_or_404(
        Proprietaire,
        id=id,
        agence=agence
    )

    nombre_batiments = Batiment.objects.filter(
        proprietaire=proprietaire,
        agence=agence
    ).count()

    return render(request, "detail_proprietaire.html", {
        "proprietaire": proprietaire,
        "nombre_batiments": nombre_batiments,
    })


    
@login_required(login_url="login")
def modifier_proprietaire(request, id):

    agence = get_agence(request.user)

    proprietaire = get_object_or_404(
        Proprietaire,
        id=id,
        agence=agence
    )

    if request.method == "POST":

        proprietaire.code_client = request.POST.get("code_client")
        proprietaire.nom = request.POST.get("nom")
        proprietaire.prenom = request.POST.get("prenom")
        proprietaire.telephone = request.POST.get("telephone")
        proprietaire.email = request.POST.get("email")
        proprietaire.adresse = request.POST.get("adresse")

        proprietaire.resident = (
            request.POST.get("resident") == "True"
        )

        proprietaire.save()

        messages.success(
            request,
            "Propriétaire modifié avec succès."
        )

        return redirect(
            "detail_proprietaire",
            id=proprietaire.id
        )

    return render(
        request,
        "modifier_proprietaire.html",
        {
            "proprietaire": proprietaire
        }
   )



from django.shortcuts import get_object_or_404

@login_required(login_url="login")
def supprimer_proprietaire(request, id):

    agence = get_agence(request.user)

    proprietaire = get_object_or_404(
        Proprietaire,
        id=id,
        agence=agence
    )

    proprietaire.delete()

    messages.success(
        request,
        "Propriétaire supprimé avec succès."
    )

    return redirect("proprietaires")



@login_required(login_url="login")
def employes(request):

    agence = get_agence(request.user)

    employes = Employe.objects.filter(
        agence=agence
    )

    return render(
        request,
        "employes.html",
        {
            "employes": employes
        }
    )


from django.contrib.auth.models import User
from django.contrib.auth.models import User
from django.contrib import messages

@login_required(login_url="login")
def ajouter_employe(request):

    agence = get_agence(request.user)

    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Ce nom utilisateur existe déjà.")
            return redirect("ajouter_employe")

        if not password:
            messages.error(request, "Le mot de passe est obligatoire.")
            return redirect("ajouter_employe")

        user = User.objects.create_user(
            username=username,
            password=password
        )

        Employe.objects.create(
            agence=agence,
            utilisateur=user,
            type_employe=request.POST.get("type_employe"),
            nom=request.POST.get("nom"),
            prenom=request.POST.get("prenom"),
            telephone=request.POST.get("telephone"),
            adresse=request.POST.get("adresse"),
            ville=request.POST.get("ville"),
            numero_poste=request.POST.get("numero_poste"),
            salaire=request.POST.get("salaire") or 0,
            nationalite=request.POST.get("nationalite"),
            acte_naissance=request.POST.get("acte_naissance")
        )

        messages.success(request, "Employé créé avec succès.")
        return redirect("employes")

    return render(request, "ajouter_employe.html")



from django.shortcuts import (
    render,
    redirect,
    get_object_or_404
)

from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import Employe


@login_required(login_url="login")
def detail_employe(request, id):

    agence = get_agence(request.user)

    employe = get_object_or_404(
        Employe,
        id=id,
        agence=agence
    )

    return render(
        request,
        "detail_employe.html",
        {
            "employe": employe
        }
    )


@login_required(login_url="login")
def modifier_employe(request, id):

    agence = get_agence(request.user)

    employe = get_object_or_404(
        Employe,
        id=id,
        agence=agence
    )

    if request.method == "POST":

        employe.nom = request.POST.get(
            "nom"
        )

        employe.prenom = request.POST.get(
            "prenom"
        )

        employe.telephone = request.POST.get(
            "telephone"
        )

        employe.adresse = request.POST.get(
            "adresse"
        )

        employe.ville = request.POST.get(
            "ville"
        )

        employe.numero_poste = request.POST.get(
            "numero_poste"
        )

        employe.salaire = request.POST.get(
            "salaire"
        )

        employe.nationalite = request.POST.get(
            "nationalite"
        )

        employe.acte_naissance = request.POST.get(
            "acte_naissance"
        )

        employe.type_employe = request.POST.get(
            "type_employe"
        )

        employe.save()

        messages.success(
            request,
            "Employé modifié avec succès."
        )

        return redirect("employes")

    return render(
        request,
        "modifier_employe.html",
        {
            "employe": employe
        }
    )







@login_required(login_url="login")
def supprimer_employe(request, id):

    agence = get_agence(request.user)

    employe = get_object_or_404(
        Employe,
        id=id,
        agence=agence
    )

    if employe.utilisateur:
        employe.utilisateur.delete()

    employe.delete()

    messages.success(
        request,
        "Employé supprimé avec succès."
    )

    return redirect("employes")




from django.contrib import messages
from django.shortcuts import get_object_or_404

@login_required(login_url="login")
def reset_password_employe(request, id):

    agence = get_agence(request.user)

    employe = get_object_or_404(
        Employe,
        id=id,
        agence=agence
    )

    if request.method == "POST":

        nouveau_password = request.POST.get(
            "password"
        )

        employe.utilisateur.set_password(
            nouveau_password
        )

        employe.utilisateur.save()

        messages.success(
            request,
            "Mot de passe réinitialisé avec succès."
        )

        return redirect(
            "detail_employe",
            id=employe.id
        )

    return render(
        request,
        "reset_password_employe.html",
        {
            "employe": employe
        }
    )



@login_required(login_url="login")
def modifier_username_employe(request, id):

    agence = get_agence(request.user)

    employe = get_object_or_404(
        Employe,
        id=id,
        agence=agence
    )

    if request.method == "POST":

        nouveau_username = request.POST.get(
            "username"
        )

        employe.utilisateur.username = (
            nouveau_username
        )

        employe.utilisateur.save()

        messages.success(
            request,
            "Nom utilisateur modifié avec succès."
        )

        return redirect(
            "detail_employe",
            id=employe.id
        )

    return render(
        request,
        "modifier_username_employe.html",
        {
            "employe": employe
        }
    )





from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.shortcuts import get_object_or_404, render


# =========================================================
# VÉRIFICATION DU RÔLE DE L'EMPLOYÉ
# =========================================================
def get_employe_autorise(request):

    employe = get_object_or_404(
        Employe.objects.select_related(
            "utilisateur",
            "agence"
        ),
        utilisateur=request.user
    )

    roles_autorises = [
        "agent",
        "secretaire",
    ]

    if employe.type not in roles_autorises:
        raise PermissionDenied(
            "Vous n'avez pas l'autorisation d'accéder à cet espace."
        )

    return employe

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.shortcuts import get_object_or_404, render


# =========================================================
# VÉRIFIER L'EMPLOYÉ CONNECTÉ
# =========================================================
def get_employe_autorise(request):

    employe = get_object_or_404(
        Employe.objects.select_related(
            "utilisateur",
            "agence"
        ),
        utilisateur=request.user
    )

    # Valeurs enregistrées dans le champ type_employe
    roles_autorises = [
        "agent",
        "secretaire",
    ]

    if employe.type_employe not in roles_autorises:
        raise PermissionDenied(
            "Vous n'avez pas l'autorisation d'accéder à cet espace."
        )

    if not employe.agence_id:
        raise PermissionDenied(
            "Cet employé n'est rattaché à aucune agence."
        )

    return employe


# =========================================================
# ESPACE AGENT / SECRÉTAIRE
# =========================================================
@login_required(login_url="login")
def espace_employe(request):

    # =====================================================
    # 1. EMPLOYÉ CONNECTÉ
    # =====================================================
    employe = get_employe_autorise(request)

    agence = employe.agence


    # =====================================================
    # 2. BÂTIMENTS DE L'AGENCE
    # =====================================================
    batiments = list(
        Batiment.objects.filter(
            agence=agence
        ).select_related(
            "proprietaire"
        ).order_by(
            "-date_creation"
        )
    )


    # =====================================================
    # 3. CHAMBRES / LOGEMENTS ACTIFS
    # =====================================================
    chambres = ChambreLogement.objects.filter(
        batiment__agence=agence,
        actif=True
    )


    # =====================================================
    # 4. LOCATAIRES DE L'AGENCE
    # =====================================================
    locataires = Locataire.objects.filter(
        agence=agence
    ).order_by(
        "-date_creation"
    )


    # =====================================================
    # 5. LOCATIONS DE L'AGENCE
    # =====================================================
    locations = Location.objects.filter(
        agence=agence
    ).select_related(
        "locataire",
        "batiment"
    ).order_by(
        "-id"
    )

    locations_actives = locations.filter(
        active=True
    )


    # =====================================================
    # 6. PAIEMENTS ENREGISTRÉS PAR L'EMPLOYÉ
    # Le champ du modèle Paiement s'appelle "employe"
    # =====================================================
    paiements_employe = Paiement.objects.filter(
        agence=agence,
        employe=employe
    ).select_related(
        "location",
        "location__locataire",
        "location__batiment"
    ).order_by(
        "-date_paiement",
        "-id"
    )


    # =====================================================
    # 7. NOMBRE DE CHAMBRES PAR BÂTIMENT
    # =====================================================
    chambres_par_batiment = dict(
        chambres.values(
            "batiment_id"
        ).annotate(
            total=Count("id")
        ).values_list(
            "batiment_id",
            "total"
        )
    )


    # =====================================================
    # 8. LOCATIONS ACTIVES PAR BÂTIMENT
    # Une location active correspond à un logement occupé
    # =====================================================
    occupations_par_batiment = dict(
        locations_actives.values(
            "batiment_id"
        ).annotate(
            total=Count("id")
        ).values_list(
            "batiment_id",
            "total"
        )
    )


    # =====================================================
    # 9. STATISTIQUES DE CHAQUE BÂTIMENT
    # =====================================================
    for batiment in batiments:

        nombre_chambres = chambres_par_batiment.get(
            batiment.id,
            0
        )

        nombre_occupees = occupations_par_batiment.get(
            batiment.id,
            0
        )

        # Évite d'afficher plus de logements occupés
        # que de logements enregistrés
        nombre_occupees = min(
            nombre_occupees,
            nombre_chambres
        )

        nombre_libres = max(
            nombre_chambres - nombre_occupees,
            0
        )

        # Variables temporaires utilisables dans le HTML
        batiment.nombre_chambres = nombre_chambres
        batiment.nombre_chambres_occupees = nombre_occupees
        batiment.nombre_chambres_libres = nombre_libres

        if nombre_chambres == 0:
            batiment.statut_employe = "Aucun logement"

        elif nombre_occupees == 0:
            batiment.statut_employe = "Libre"

        elif nombre_libres == 0:
            batiment.statut_employe = "Complètement occupé"

        else:
            batiment.statut_employe = "Partiellement occupé"


    # =====================================================
    # 10. STATISTIQUES GÉNÉRALES
    # =====================================================
    total_batiments = len(batiments)

    total_chambres = sum(
        batiment.nombre_chambres
        for batiment in batiments
    )

    total_chambres_occupees = sum(
        batiment.nombre_chambres_occupees
        for batiment in batiments
    )

    total_chambres_libres = sum(
        batiment.nombre_chambres_libres
        for batiment in batiments
    )

    total_locataires = locataires.count()

    total_locations = locations.count()

    total_locations_actives = locations_actives.count()

    total_paiements_enregistres = paiements_employe.count()


    # =====================================================
    # 11. DERNIERS ENREGISTREMENTS
    # =====================================================
    derniers_locataires = locataires[:10]

    dernieres_locations = locations[:10]

    derniers_paiements = paiements_employe[:10]


    # =====================================================
    # 12. CONTEXTE
    # =====================================================
    context = {

        # Employé et agence
        "employe": employe,
        "agence": agence,

        # Listes autorisées
        "batiments": batiments,
        "locataires": locataires,
        "locations": locations,
        "locations_actives": locations_actives,

        # Effectifs
        "total_batiments": total_batiments,
        "total_chambres": total_chambres,
        "total_chambres_occupees": total_chambres_occupees,
        "total_chambres_libres": total_chambres_libres,
        "total_locataires": total_locataires,
        "total_locations": total_locations,
        "total_locations_actives": total_locations_actives,
        "total_paiements_enregistres": total_paiements_enregistres,

        # Dernières activités
        "derniers_locataires": derniers_locataires,
        "dernieres_locations": dernieres_locations,
        "derniers_paiements": derniers_paiements,

        # Autorisations affichées dans le HTML
        "peut_ajouter_locataire": True,
        "peut_ajouter_paiement": True,
        "peut_voir_batiments": True,
        "peut_voir_locations": True,

        # Sections interdites
        "peut_voir_proprietaires": False,
        "peut_voir_terrains": False,
        "peut_voir_constructions": False,
        "peut_voir_rapports": False,
        "peut_voir_depenses": False,
    }

    return render(
        request,
        "espace_employe.html",
        context
    )



from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404


def get_employe_autorise(request):

    employe = get_object_or_404(
        Employe.objects.select_related(
            "utilisateur",
            "agence"
        ),
        utilisateur=request.user
    )

    roles_autorises = [
        "agent",
        "secretaire",
    ]

    if employe.type_employe not in roles_autorises:
        raise PermissionDenied(
            "Vous n'avez pas l'autorisation d'accéder à cet espace."
        )

    return employe




from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404


@login_required(login_url="login")
def ajouter_paiement(request):
    agence = get_agence(request.user)

    locataires = Locataire.objects.filter(
        agence=agence,
        actif=True
    ).order_by("nom", "prenom")

    batiments = Batiment.objects.filter(
        agence=agence,
        actif=True
    ).select_related("proprietaire").order_by("nom")

    employes = Employe.objects.filter(
        agence=agence
    ).order_by("nom")

    if request.method == "POST":
        locataire_id = request.POST.get("locataire")
        batiment_id = request.POST.get("batiment")
        employe_id = request.POST.get("employe")

        numero_recu = request.POST.get("numero_recu", "").strip()
        montant_raw = request.POST.get("montant", "0").strip()
        mois = request.POST.get("mois", "").strip()
        mode_paiement = request.POST.get("mode_paiement", "espece")
        statut = request.POST.get("statut", "attente")
        numero_appartement = request.POST.get("numero_appartement", "").strip() or "N/A"
        date_debut_raw = request.POST.get("date_debut", "").strip()

        if not locataire_id or not batiment_id:
            messages.error(request, "Sélectionne un locataire et un bâtiment.")
            return redirect("ajouter_paiement")

        if not numero_recu:
            messages.error(request, "Le numéro de reçu est obligatoire.")
            return redirect("ajouter_paiement")

        if not mois:
            messages.error(request, "Le mois du paiement est obligatoire.")
            return redirect("ajouter_paiement")

        try:
            montant = Decimal(montant_raw)
        except InvalidOperation:
            messages.error(request, "Le montant est invalide.")
            return redirect("ajouter_paiement")

        if montant <= 0:
            messages.error(request, "Le montant doit être supérieur à 0.")
            return redirect("ajouter_paiement")

        locataire = get_object_or_404(
            Locataire,
            id=locataire_id,
            agence=agence
        )

        batiment = get_object_or_404(
            Batiment,
            id=batiment_id,
            agence=agence
        )

        if date_debut_raw:
            try:
                date_debut = date.fromisoformat(date_debut_raw)
            except ValueError:
                messages.error(request, "La date de début est invalide.")
                return redirect("ajouter_paiement")
        else:
            date_debut = date.today()

        location = Location.objects.filter(
            agence=agence,
            locataire=locataire,
            batiment=batiment,
            active=True
        ).first()

        if not location:
            location = Location.objects.create(
                agence=agence,
                locataire=locataire,
                batiment=batiment,
                numero_appartement=numero_appartement,
                loyer=montant,
                date_debut=date_debut,
                active=True
            )

        Paiement.objects.create(
            agence=agence,
            proprietaire=batiment.proprietaire,
            location=location,
            employe_id=employe_id or None,
            numero_recu=numero_recu,
            montant=montant,
            mois=mois,
            mode_paiement=mode_paiement,
            statut=statut,
            signature_employe=request.POST.get("signature_employe"),
            signature_locataire=request.POST.get("signature_locataire"),
            commentaire=request.POST.get("commentaire"),
            justificatif=request.FILES.get("justificatif"),
        )

        messages.success(request, "Paiement enregistré avec succès.")
        return redirect("paiements")

    return render(request, "ajouter_paiement.html", {
        "locataires": locataires,
        "batiments": batiments,
        "employes": employes,
    })




@login_required(login_url="login")
def ajouter_locataire(request):
    agence = get_agence(request.user)

    if request.method == "POST":

        Locataire.objects.create(
            agence=agence,

            # Informations personnelles
            nom=request.POST.get("nom"),
            prenom=request.POST.get("prenom"),
            telephone=request.POST.get("telephone"),
            email=request.POST.get("email"),

            date_naissance=request.POST.get("date_naissance") or None,
            lieu_naissance=request.POST.get("lieu_naissance"),
            sexe=request.POST.get("sexe"),

            profession=request.POST.get("profession"),
            employeur=request.POST.get("employeur"),
            revenu_mensuel=request.POST.get("revenu_mensuel") or None,

            adresse_actuelle=request.POST.get("adresse_actuelle"),
            ville=request.POST.get("ville"),
            pays=request.POST.get("pays"),

            # Contact d'urgence
            contact_urgence_nom=request.POST.get("contact_urgence_nom"),
            contact_urgence_telephone=request.POST.get("contact_urgence_telephone"),
            contact_urgence_lien=request.POST.get("contact_urgence_lien"),

            # Pièce d'identité
            numero_piece_identite=request.POST.get("numero_piece_identite"),
            date_expiration_piece=request.POST.get("date_expiration_piece") or None,

            piece_identite=request.FILES.get("piece_identite"),
            acte_naissance=request.FILES.get("acte_naissance"),
            photo=request.FILES.get("photo"),

            # Caution
            caution=request.POST.get("caution") or 0,
            caution_payee=request.POST.get("caution_payee") == "on",
            date_caution=request.POST.get("date_caution") or None,
            observation_caution=request.POST.get("observation_caution"),

            # Début du contrat
            date_debut=request.POST.get("date_debut") or None,

            # Statut
            actif=request.POST.get("actif") == "on",
        )

        messages.success(request, "Le locataire a été ajouté avec succès.")
        return redirect("locataires")

    return render(request, "ajouter_locataire.html")


from django.shortcuts import get_object_or_404


@login_required(login_url="login")
def detail_locataire(request, id):
    locataire = get_object_or_404(Locataire, id=id)
    return render(
        request,
        "detail_locataire.html",
        {"locataire": locataire}
    )


@login_required(login_url="login")
def modifier_locataire(request, id):
    return redirect("locataires")


@login_required(login_url="login")
def supprimer_locataire(request, id):
    locataire = get_object_or_404(Locataire, id=id)
    locataire.delete()
    return redirect("locataires")



from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from .models import Paiement


@login_required(login_url="login")
def facture_paiement_pdf(request, paiement_id):
    paiement = get_object_or_404(
        Paiement.objects.select_related(
            "agence",
            "location",
            "location__locataire",
            "location__batiment",
            "location__batiment__proprietaire",
            "employe",
        ),
        id=paiement_id,
        agence=get_agence(request.user)
    )

    return render(request, "facture_paiement_pdf.html", {
        "paiement": paiement
    })


@login_required(login_url="login")
def recu_paiement_pdf(request, paiement_id):
    paiement = get_object_or_404(
        Paiement.objects.select_related(
            "agence",
            "location",
            "location__locataire",
            "location__batiment",
            "location__batiment__proprietaire",
            "employe",
        ),
        id=paiement_id,
        agence=get_agence(request.user)
    )

    return render(request, "recu_paiement_pdf.html", {
        "paiement": paiement
    })

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, render

from .models import Paiement, Employe


@login_required(login_url="login")
def imprimer_paiement(request, paiement_id):

    # =====================================================
    # 1. DÉTERMINER L'AGENCE DE L'UTILISATEUR CONNECTÉ
    # =====================================================
    employe = Employe.objects.select_related(
        "agence"
    ).filter(
        utilisateur=request.user
    ).first()

    if employe:
        # Agent ou secrétaire
        agence = employe.agence
    else:
        # Directeur ou administrateur
        agence = get_agence(request.user)

    # =====================================================
    # 2. RÉCUPÉRER LE PAIEMENT
    # =====================================================
    paiement = get_object_or_404(
        Paiement.objects.select_related(
            "agence",
            "location",
            "location__locataire",
            "location__batiment",
            "location__batiment__proprietaire",
            "location__chambre",
        ),
        id=paiement_id
    )

    # =====================================================
    # 3. SÉCURITÉ MULTI-AGENCE
    # =====================================================
    if paiement.agence_id != agence.id:
        raise PermissionDenied(
            "Vous n’avez pas accès à ce paiement."
        )

    # =====================================================
    # 4. AFFICHAGE DU REÇU
    # =====================================================
    return render(
        request,
        "imprimer_paiement.html",
        {
            "paiement": paiement,
            "agence": agence,
            "employe": employe,
        }
    )


@login_required(login_url="login")
def modifier_paiement(request, paiement_id):

    paiement = get_object_or_404(
        Paiement,
        id=paiement_id
    )

    if request.method == "POST":

        # Modifier locataire
        paiement.location.locataire.nom = request.POST.get(
            "locataire_nom"
        )
        paiement.location.locataire.save()

        # Modifier bâtiment
        paiement.location.batiment.nom = request.POST.get(
            "batiment_nom"
        )
        paiement.location.batiment.save()

        # Modifier paiement
        paiement.montant = request.POST.get("montant")
        paiement.mois = request.POST.get("mois")
        paiement.statut = request.POST.get("statut")
        paiement.mode_paiement = request.POST.get("mode_paiement")

        # Champs optionnels
        if hasattr(paiement, "numero_recu"):
            paiement.numero_recu = request.POST.get(
                "numero_recu"
            )

        if hasattr(paiement, "agent"):
            paiement.agent = request.POST.get(
                "agent"
            )

        if hasattr(paiement, "observation"):
            paiement.observation = request.POST.get(
                "observation"
            )

        paiement.save()

        return redirect("paiements")

    return render(
        request,
        "modifier_paiement.html",
        {
            "paiement": paiement
        }
    )



from django.contrib.auth.decorators import login_required
from django.shortcuts import render

@login_required(login_url="login")
def statistiques_locataires(request):
    return render(request, "statistiques_locataires.html")





from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

@login_required(login_url="login")
def modifier_locataire(request, locataire_id):
    agence = get_agence(request.user)

    locataire = get_object_or_404(
        Locataire,
        id=locataire_id,
        agence=agence
    )

    if request.method == "POST":
        locataire.nom = request.POST.get("nom")
        locataire.prenom = request.POST.get("prenom")
        locataire.telephone = request.POST.get("telephone")
        locataire.email = request.POST.get("email")

        locataire.date_naissance = request.POST.get("date_naissance") or None
        locataire.lieu_naissance = request.POST.get("lieu_naissance")
        locataire.sexe = request.POST.get("sexe")

        locataire.profession = request.POST.get("profession")
        locataire.employeur = request.POST.get("employeur")
        locataire.revenu_mensuel = request.POST.get("revenu_mensuel") or None

        locataire.adresse_actuelle = request.POST.get("adresse_actuelle")
        locataire.ville = request.POST.get("ville")
        locataire.pays = request.POST.get("pays")

        locataire.contact_urgence_nom = request.POST.get("contact_urgence_nom")
        locataire.contact_urgence_telephone = request.POST.get("contact_urgence_telephone")
        locataire.contact_urgence_lien = request.POST.get("contact_urgence_lien")

        locataire.numero_piece_identite = request.POST.get("numero_piece_identite")
        locataire.date_expiration_piece = request.POST.get("date_expiration_piece") or None

        locataire.caution = request.POST.get("caution") or 0
        locataire.caution_payee = request.POST.get("caution_payee") == "on"
        locataire.date_caution = request.POST.get("date_caution") or None
        locataire.date_debut = request.POST.get("date_debut") or None
        locataire.observation_caution = request.POST.get("observation_caution")
        locataire.actif = request.POST.get("actif") == "on"

        if request.FILES.get("piece_identite"):
            locataire.piece_identite = request.FILES.get("piece_identite")

        if request.FILES.get("acte_naissance"):
            locataire.acte_naissance = request.FILES.get("acte_naissance")

        if request.FILES.get("photo"):
            locataire.photo = request.FILES.get("photo")

        locataire.save()

        messages.success(request, "Le locataire a été modifié avec succès.")
        return redirect("detail_locataire", locataire.id)

    return render(request, "modifier_locataire.html", {
        "locataire": locataire
    })



from datetime import datetime
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, render

from .models import (
    Paiement,
    Proprietaire,
    Depense,
    RapportMensuelProprietaire,
)


DECIMAL_ZERO = Decimal("0.00")
TAUX_AGENCE = Decimal("0.10")


def convertir_mois(mois):
    """
    Convertit un mois au format YYYY-MM en année et numéro de mois.

    Exemple :
        2026-07 -> (2026, 7)

    Retourne None si le format est incorrect.
    """
    if not mois:
        return None

    try:
        date_mois = datetime.strptime(mois, "%Y-%m")
        return date_mois.year, date_mois.month
    except ValueError:
        return None



@login_required(login_url="login")
def rapports(request):
    agence = get_agence(request.user)

    mois = request.GET.get("mois", "").strip()

    proprietaires = Proprietaire.objects.filter(
        agence=agence
    ).order_by(
        "nom",
        "prenom"
    )

    context = {
        "agence": agence,
        "proprietaires": proprietaires,
        "mois": mois,
    }

    return render(
        request,
        "rapports.html",
        context
    )




@login_required(login_url="login")
def rapport_mensuel_proprietaire(request, proprietaire_id):
    agence = get_agence(request.user)

    proprietaire = get_object_or_404(
        Proprietaire,
        id=proprietaire_id,
        agence=agence
    )

    mois = request.GET.get("mois", "").strip()
    mois_converti = convertir_mois(mois)

    # =========================
    # PAIEMENTS DU PROPRIÉTAIRE
    # =========================

    paiements = Paiement.objects.filter(
        agence=agence,
        location__batiment__proprietaire=proprietaire,
        statut="paye"
    ).select_related(
        "location",
        "location__locataire",
        "location__batiment",
        "location__batiment__proprietaire",
        "agence"
    ).order_by(
        "-date_paiement"
    )

    if mois:
        paiements = paiements.filter(
            mois__icontains=mois
        )

    # =========================
    # TOTAL DES LOYERS
    # =========================

    total_loyers = paiements.aggregate(
        total=Sum("montant")
    )["total"] or DECIMAL_ZERO

    total_loyers = Decimal(total_loyers).quantize(
        Decimal("0.01")
    )

    # =========================
    # DÉPENSES DU PROPRIÉTAIRE
    # =========================

    depenses_proprietaire_queryset = Depense.objects.filter(
        agence=agence,
        proprietaire=proprietaire,
        type_depense="proprietaire"
    ).select_related(
        "agence",
        "proprietaire"
    ).order_by(
        "-date_depense"
    )

    if mois_converti:
        annee, numero_mois = mois_converti

        depenses_proprietaire_queryset = (
            depenses_proprietaire_queryset.filter(
                date_depense__year=annee,
                date_depense__month=numero_mois
            )
        )

    depenses_proprietaire = (
        depenses_proprietaire_queryset.aggregate(
            total=Sum("montant")
        )["total"]
        or DECIMAL_ZERO
    )

    depenses_proprietaire = Decimal(
        depenses_proprietaire
    ).quantize(
        Decimal("0.01")
    )

    # =========================
    # CALCULS
    # =========================

    part_agence = (
        total_loyers * TAUX_AGENCE
    ).quantize(
        Decimal("0.01")
    )

    part_proprietaire = (
        total_loyers - part_agence
    ).quantize(
        Decimal("0.01")
    )

    net_proprietaire = (
        part_proprietaire - depenses_proprietaire
    ).quantize(
        Decimal("0.01")
    )

    # =========================
    # PARTS SUR CHAQUE PAIEMENT
    # =========================

    for paiement in paiements:
        montant = paiement.montant or DECIMAL_ZERO

        paiement.part_agence = (
            montant * TAUX_AGENCE
        ).quantize(
            Decimal("0.01")
        )

        paiement.part_proprietaire = (
            montant - paiement.part_agence
        ).quantize(
            Decimal("0.01")
        )

    # =========================
    # ENREGISTREMENT DU RAPPORT
    # =========================

    rapport = None

    if mois:
        rapport, created = (
            RapportMensuelProprietaire.objects.update_or_create(
                agence=agence,
                proprietaire=proprietaire,
                mois=mois,
                defaults={
                    "total_loyers": total_loyers,
                    "depenses_proprietaire": depenses_proprietaire,
                    "depenses_agence": DECIMAL_ZERO,
                }
            )
        )

        # Le save() du modèle appelle automatiquement calculer().
        rapport.refresh_from_db()

    context = {
        "agence": agence,
        "proprietaire": proprietaire,
        "paiements": paiements,
        "mois": mois,

        "total_loyers": total_loyers,
        "part_agence": part_agence,
        "part_proprietaire": part_proprietaire,

        "depenses_proprietaire": depenses_proprietaire,
        "liste_depenses_proprietaire": (
            depenses_proprietaire_queryset
        ),

        "net_proprietaire": net_proprietaire,
        "rapport": rapport,
    }

    return render(
        request,
        "rapport_mensuel_proprietaire.html",
        context
    )





@login_required(login_url="login")
def rapport_mensuel_agence(request):
    agence = get_agence(request.user)

    mois = request.GET.get("mois", "").strip()
    mois_converti = convertir_mois(mois)

    # =========================
    # PAIEMENTS DE L’AGENCE
    # =========================

    paiements = Paiement.objects.filter(
        agence=agence,
        statut="paye"
    ).select_related(
        "location",
        "location__locataire",
        "location__batiment",
        "location__batiment__proprietaire"
    ).order_by(
        "-date_paiement"
    )

    if mois:
        paiements = paiements.filter(
            mois__icontains=mois
        )

    # =========================
    # TOTAL DES LOYERS
    # =========================

    total_loyers = paiements.aggregate(
        total=Sum("montant")
    )["total"] or DECIMAL_ZERO

    total_loyers = Decimal(total_loyers).quantize(
        Decimal("0.01")
    )

    # =========================
    # COMMISSION AGENCE
    # =========================

    commission_agence = (
        total_loyers * TAUX_AGENCE
    ).quantize(
        Decimal("0.01")
    )

    total_proprietaires = (
        total_loyers - commission_agence
    ).quantize(
        Decimal("0.01")
    )

    # =========================
    # DÉPENSES DE L’AGENCE
    # =========================

    depenses_agence_queryset = Depense.objects.filter(
        agence=agence,
        type_depense="agence",
        proprietaire__isnull=True
    ).order_by(
        "-date_depense"
    )

    if mois_converti:
        annee, numero_mois = mois_converti

        depenses_agence_queryset = (
            depenses_agence_queryset.filter(
                date_depense__year=annee,
                date_depense__month=numero_mois
            )
        )

    depenses_agence = (
        depenses_agence_queryset.aggregate(
            total=Sum("montant")
        )["total"]
        or DECIMAL_ZERO
    )

    depenses_agence = Decimal(
        depenses_agence
    ).quantize(
        Decimal("0.01")
    )

    # =========================
    # DÉPENSES PROPRIÉTAIRES
    # =========================

    depenses_proprietaires_queryset = Depense.objects.filter(
        agence=agence,
        type_depense="proprietaire",
        proprietaire__isnull=False
    ).select_related(
        "proprietaire"
    ).order_by(
        "-date_depense"
    )

    if mois_converti:
        annee, numero_mois = mois_converti

        depenses_proprietaires_queryset = (
            depenses_proprietaires_queryset.filter(
                date_depense__year=annee,
                date_depense__month=numero_mois
            )
        )

    depenses_proprietaires = (
        depenses_proprietaires_queryset.aggregate(
            total=Sum("montant")
        )["total"]
        or DECIMAL_ZERO
    )

    depenses_proprietaires = Decimal(
        depenses_proprietaires
    ).quantize(
        Decimal("0.01")
    )

    # =========================
    # NETS
    # =========================

    net_agence = (
        commission_agence - depenses_agence
    ).quantize(
        Decimal("0.01")
    )

    net_total_proprietaires = (
        total_proprietaires
        - depenses_proprietaires
    ).quantize(
        Decimal("0.01")
    )

    # =========================
    # PART SUR CHAQUE PAIEMENT
    # =========================

    for paiement in paiements:
        montant = paiement.montant or DECIMAL_ZERO

        paiement.part_agence = (
            montant * TAUX_AGENCE
        ).quantize(
            Decimal("0.01")
        )

        paiement.part_proprietaire = (
            montant - paiement.part_agence
        ).quantize(
            Decimal("0.01")
        )

    # =========================
    # PROPRIÉTAIRES
    # =========================

    proprietaires = Proprietaire.objects.filter(
        agence=agence
    ).order_by(
        "nom",
        "prenom"
    )

    # =========================
    # RAPPORT PAR PROPRIÉTAIRE
    # =========================

    rapports_proprietaires = []

    for proprietaire in proprietaires:
        paiements_proprietaire = paiements.filter(
            location__batiment__proprietaire=proprietaire
        )

        loyers_proprietaire = (
            paiements_proprietaire.aggregate(
                total=Sum("montant")
            )["total"]
            or DECIMAL_ZERO
        )

        loyers_proprietaire = Decimal(
            loyers_proprietaire
        ).quantize(
            Decimal("0.01")
        )

        commission_proprietaire = (
            loyers_proprietaire * TAUX_AGENCE
        ).quantize(
            Decimal("0.01")
        )

        part_brute_proprietaire = (
            loyers_proprietaire
            - commission_proprietaire
        ).quantize(
            Decimal("0.01")
        )

        depenses_du_proprietaire_queryset = (
            depenses_proprietaires_queryset.filter(
                proprietaire=proprietaire
            )
        )

        total_depenses_du_proprietaire = (
            depenses_du_proprietaire_queryset.aggregate(
                total=Sum("montant")
            )["total"]
            or DECIMAL_ZERO
        )

        total_depenses_du_proprietaire = Decimal(
            total_depenses_du_proprietaire
        ).quantize(
            Decimal("0.01")
        )

        net_du_proprietaire = (
            part_brute_proprietaire
            - total_depenses_du_proprietaire
        ).quantize(
            Decimal("0.01")
        )

        rapport_enregistre = None

        if mois:
            rapport_enregistre, created = (
                RapportMensuelProprietaire.objects.update_or_create(
                    agence=agence,
                    proprietaire=proprietaire,
                    mois=mois,
                    defaults={
                        "total_loyers": loyers_proprietaire,
                        "depenses_proprietaire": (
                            total_depenses_du_proprietaire
                        ),
                        "depenses_agence": DECIMAL_ZERO,
                    }
                )
            )

            rapport_enregistre.refresh_from_db()

        rapports_proprietaires.append({
            "proprietaire": proprietaire,
            "total_loyers": loyers_proprietaire,
            "part_agence": commission_proprietaire,
            "part_proprietaire": part_brute_proprietaire,
            "depenses_proprietaire": (
                total_depenses_du_proprietaire
            ),
            "net_proprietaire": net_du_proprietaire,
            "rapport": rapport_enregistre,
        })

    context = {
        "agence": agence,
        "paiements": paiements,
        "proprietaires": proprietaires,
        "rapports_proprietaires": rapports_proprietaires,
        "mois": mois,

        "total_loyers": total_loyers,
        "commission_agence": commission_agence,
        "total_proprietaires": total_proprietaires,

        "depenses_agence": depenses_agence,
        "depenses_proprietaires": depenses_proprietaires,

        "net_agence": net_agence,
        "net_total_proprietaires": net_total_proprietaires,

        "liste_depenses_agence": depenses_agence_queryset,
        "liste_depenses_proprietaires": (
            depenses_proprietaires_queryset
        ),
    }

    return render(
        request,
        "rapport_mensuel_agence.html",
        context
    )



from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render

from .models import Depense


@login_required(login_url="login")
def depenses_agence(request):

    agence = get_agence(request.user)

    depenses = Depense.objects.filter(
        agence=agence,
        type_depense="agence",
        proprietaire__isnull=True
    ).order_by(
        "-date_depense",
        "-date_creation"
    )

    total_depenses = depenses.aggregate(
        total=Sum("montant")
    )["total"] or Decimal("0.00")

    context = {
        "agence": agence,
        "depenses": depenses,
        "total_depenses": total_depenses,
    }

    return render(
        request,
        "depenses_agence.html",
        context
    )


@login_required(login_url="login")
def depenses_proprietaires(request):

    agence = get_agence(request.user)

    depenses = Depense.objects.filter(
        agence=agence,
        type_depense="proprietaire",
        proprietaire__isnull=False
    ).select_related(
        "proprietaire"
    ).order_by(
        "-date_depense",
        "-date_creation"
    )

    total_depenses = depenses.aggregate(
        total=Sum("montant")
    )["total"] or Decimal("0.00")

    context = {
        "agence": agence,
        "depenses": depenses,
        "total_depenses": total_depenses,
    }

    return render(
        request,
        "depenses_proprietaires.html",
        context
    )



from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

from .models import Depense, Proprietaire

from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect, get_object_or_404


@login_required(login_url="login")
def ajouter_depense(request):
    agence = get_agence(request.user)

    type_depense = request.GET.get(
        "type",
        "agence"
    ).strip().lower()

    types_valides = [
        "agence",
        "proprietaire",
    ]

    categories_valides = [
        choix[0]
        for choix in Depense.CATEGORIE_CHOICES
    ]

    if type_depense not in types_valides:
        type_depense = "agence"

    proprietaires = Proprietaire.objects.filter(
        agence=agence
    ).order_by(
        "nom",
        "prenom"
    )

    contexte = {
        "agence": agence,
        "proprietaires": proprietaires,
        "type_depense": type_depense,
    }

    if request.method == "POST":
        type_depense = request.POST.get(
            "type_depense",
            type_depense
        ).strip().lower()

        titre = request.POST.get(
            "titre",
            ""
        ).strip()

        montant_str = request.POST.get(
            "montant",
            ""
        ).strip()

        date_depense = request.POST.get(
            "date_depense",
            ""
        ).strip()

        categorie = request.POST.get(
            "categorie",
            "autre"
        ).strip().lower()

        description = request.POST.get(
            "description",
            ""
        ).strip()

        justificatif = request.FILES.get(
            "justificatif"
        )

        contexte["type_depense"] = type_depense

        # =========================
        # TYPE DE DÉPENSE
        # =========================
        if type_depense not in types_valides:
            messages.error(
                request,
                "Le type de dépense sélectionné est invalide."
            )

            return render(
                request,
                "ajouter_depense.html",
                contexte
            )

        # =========================
        # TITRE
        # =========================
        if not titre:
            messages.error(
                request,
                "Le titre de la dépense est obligatoire."
            )

            return render(
                request,
                "ajouter_depense.html",
                contexte
            )

        # =========================
        # MONTANT
        # =========================
        try:
            montant = Decimal(
                montant_str.replace(",", ".")
            )

            if montant <= 0:
                raise InvalidOperation

        except (
            InvalidOperation,
            ValueError,
            TypeError
        ):
            messages.error(
                request,
                "Le montant doit être un nombre supérieur à 0."
            )

            return render(
                request,
                "ajouter_depense.html",
                contexte
            )

        # =========================
        # DATE
        # =========================
        if not date_depense:
            messages.error(
                request,
                "La date de la dépense est obligatoire."
            )

            return render(
                request,
                "ajouter_depense.html",
                contexte
            )

        # =========================
        # CATÉGORIE
        # =========================
        if categorie not in categories_valides:
            categorie = "autre"

        # =========================
        # PROPRIÉTAIRE
        # =========================
        proprietaire = None

        if type_depense == "proprietaire":
            proprietaire_id = request.POST.get(
                "proprietaire",
                ""
            ).strip()

            if not proprietaire_id:
                messages.error(
                    request,
                    "Veuillez sélectionner un propriétaire."
                )

                return render(
                    request,
                    "ajouter_depense.html",
                    contexte
                )

            proprietaire = get_object_or_404(
                Proprietaire,
                id=proprietaire_id,
                agence=agence
            )

        # Pour une dépense agence,
        # aucun propriétaire ne doit être associé.
        if type_depense == "agence":
            proprietaire = None

        # =========================
        # UTILISATEUR
        # =========================
        nom_utilisateur = (
            request.user.get_full_name().strip()
            or request.user.username
        )

        # =========================
        # CRÉATION
        # =========================
        depense = Depense(
            agence=agence,
            proprietaire=proprietaire,
            type_depense=type_depense,
            categorie=categorie,
            titre=titre,
            description=description,
            montant=montant,
            date_depense=date_depense,
            justificatif=justificatif,
            ajoute_par=nom_utilisateur,
        )

        try:
            depense.save()

        except ValidationError as erreur:
            if hasattr(erreur, "message_dict"):
                for erreurs in erreur.message_dict.values():
                    for message in erreurs:
                        messages.error(
                            request,
                            message
                        )
            else:
                for message in erreur.messages:
                    messages.error(
                        request,
                        message
                    )

            return render(
                request,
                "ajouter_depense.html",
                contexte
            )

        messages.success(
            request,
            "Dépense ajoutée avec succès."
        )

        if type_depense == "proprietaire":
            return redirect("rapports")

        return redirect(
            "depenses_agence"
        )

    return render(
        request,
        "ajouter_depense.html",
        contexte
    )


from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render, redirect, get_object_or_404

from .models import Construction, EtatConstruction, Batiment



@login_required(login_url="login")
def constructions(request):
    agence = get_agence(request.user)

    constructions = (
        Construction.objects
        .filter(agence=agence)
        .select_related("batiment")
        .prefetch_related("etapes")
        .order_by("-date_creation")
    )

    total_budget = (
        constructions.aggregate(total=Sum("budget_total"))["total"]
        or Decimal("0.00")
    )

    total_depense = (
        EtatConstruction.objects
        .filter(construction__agence=agence)
        .aggregate(total=Sum("montant_depense"))["total"]
        or Decimal("0.00")
    )

    reste_global = total_budget - total_depense

    constructions_actives = constructions.filter(actif=True).count()

    context = {
        "constructions": constructions,
        "total_budget": total_budget,
        "total_depense": total_depense,
        "reste_global": reste_global,
        "constructions_actives": constructions_actives,
    }

    return render(request, "constructions.html", context)

@login_required(login_url="login")
def ajouter_construction(request):
    agence = get_agence(request.user)

    batiments = (
        Batiment.objects
        .filter(agence=agence)
        .order_by("nom")
    )

    if request.method == "POST":
        nom = request.POST.get("nom", "").strip()
        batiment_id = request.POST.get("batiment")
        budget_total = request.POST.get("budget_total", "0")
        description = request.POST.get("description", "").strip()
        date_debut = request.POST.get("date_debut") or None
        date_fin_prevue = request.POST.get("date_fin_prevue") or None

        if not nom:
            messages.error(
                request,
                "Le nom de la construction est obligatoire."
            )

            return render(
                request,
                "ajouter-construction.html",
                {
                    "batiments": batiments,
                }
            )

        try:
            budget_total = Decimal(budget_total or "0")
        except:
            budget_total = Decimal("0.00")

        batiment = None

        if batiment_id:
            batiment = get_object_or_404(
                Batiment,
                id=batiment_id,
                agence=agence
            )

        Construction.objects.create(
            agence=agence,
            nom=nom,
            batiment=batiment,
            budget_total=budget_total,
            description=description,
            date_debut=date_debut,
            date_fin_prevue=date_fin_prevue,
            actif=True
        )

        messages.success(
            request,
            "Construction ajoutée avec succès."
        )

        return redirect("constructions")

    return render(
        request,
        "ajouter-construction.html",
        {
            "batiments": batiments,
        }
    )

@login_required(login_url="login")
def detail_construction(request, construction_id):
    agence = get_agence(request.user)

    construction = get_object_or_404(
        Construction.objects.select_related("batiment"),
        id=construction_id,
        agence=agence
    )

    etapes = (
        construction.etapes
        .all()
        .order_by("date_debut", "id")
    )

    total_budget_etapes = (
        etapes.aggregate(total=Sum("budget_prevu"))["total"]
        or Decimal("0.00")
    )

    total_depense = (
        etapes.aggregate(total=Sum("montant_depense"))["total"]
        or Decimal("0.00")
    )

    reste_budget = construction.budget_total - total_depense

    budget_non_reparti = (
        construction.budget_total - total_budget_etapes
    )

    pourcentage_depense = Decimal("0.00")

    if construction.budget_total > 0:
        pourcentage_depense = (
            total_depense / construction.budget_total
        ) * 100

    context = {
        "construction": construction,
        "etapes": etapes,
        "total_budget_etapes": total_budget_etapes,
        "total_depense": total_depense,
        "reste_budget": reste_budget,
        "budget_non_reparti": budget_non_reparti,
        "pourcentage_depense": pourcentage_depense,
    }

    return render(
        request,
        "detail_construction.html",
        context
    )


@login_required(login_url="login")
def ajouter_etat_construction(request, construction_id):
    agence = get_agence(request.user)

    construction = get_object_or_404(
        Construction,
        id=construction_id,
        agence=agence
    )

    if request.method == "POST":
        nom = request.POST.get("nom", "").strip()
        description = request.POST.get("description", "").strip()

        budget_prevu = request.POST.get("budget_prevu", "0")
        montant_depense = request.POST.get("montant_depense", "0")

        statut = request.POST.get("statut", "attente")

        date_debut = request.POST.get("date_debut") or None
        date_fin = request.POST.get("date_fin") or None

        if not nom:
            messages.error(
                request,
                "Le nom de l'étape est obligatoire."
            )

            return redirect(
                "ajouter_etat_construction",
                construction_id=construction.id
            )

        try:
            budget_prevu = Decimal(budget_prevu or "0")
        except:
            budget_prevu = Decimal("0.00")

        try:
            montant_depense = Decimal(montant_depense or "0")
        except:
            montant_depense = Decimal("0.00")

        statuts_valides = [
            "attente",
            "cours",
            "termine",
            "bloque"
        ]

        if statut not in statuts_valides:
            statut = "attente"

        EtatConstruction.objects.create(
            construction=construction,
            nom=nom,
            description=description,
            budget_prevu=budget_prevu,
            montant_depense=montant_depense,
            statut=statut,
            date_debut=date_debut,
            date_fin=date_fin
        )

        messages.success(
            request,
            "État de construction ajouté avec succès."
        )

        return redirect(
            "detail_construction",
            construction_id=construction.id
        )

    return render(
        request,
        "ajouter_etat_construction.html",
        {
            "construction": construction,
            "statuts": EtatConstruction.STATUT_CHOICES,
        }
    )


@login_required(login_url="login")
def modifier_etat_construction(request, etat_id):
    agence = get_agence(request.user)

    etat = get_object_or_404(
        EtatConstruction.objects.select_related("construction"),
        id=etat_id,
        construction__agence=agence
    )

    if request.method == "POST":
        etat.nom = request.POST.get(
            "nom",
            etat.nom
        ).strip()

        etat.description = request.POST.get(
            "description",
            ""
        ).strip()

        try:
            etat.budget_prevu = Decimal(
                request.POST.get("budget_prevu", "0") or "0"
            )
        except:
            etat.budget_prevu = Decimal("0.00")

        try:
            etat.montant_depense = Decimal(
                request.POST.get("montant_depense", "0") or "0"
            )
        except:
            etat.montant_depense = Decimal("0.00")

        statut = request.POST.get("statut", "attente")

        if statut in [
            "attente",
            "cours",
            "termine",
            "bloque"
        ]:
            etat.statut = statut

        etat.date_debut = (
            request.POST.get("date_debut") or None
        )

        etat.date_fin = (
            request.POST.get("date_fin") or None
        )

        etat.save()

        messages.success(
            request,
            "État de construction modifié avec succès."
        )

        return redirect(
            "detail_construction",
            construction_id=etat.construction.id
        )

    return render(
        request,
        "modifier_etat_construction.html",
        {
            "etat": etat,
            "construction": etat.construction,
            "statuts": EtatConstruction.STATUT_CHOICES,
        }
    )



def get_agence(user):
    if hasattr(user, "agence"):
        return user.agence
    return None





from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.shortcuts import render, redirect, get_object_or_404

from .models import Terrain, Proprietaire, Agence





@login_required(login_url="login")
def terrains(request):
    agence = get_agence(request.user)

    q = request.GET.get("q", "").strip()
    statut = request.GET.get("statut", "").strip()
    type_operation = request.GET.get("type_operation", "").strip()

    terrains = Terrain.objects.filter(
        agence=agence
    ).select_related(
        "proprietaire"
    ).order_by("-date_creation")

    if q:
        terrains = terrains.filter(
            Q(titre__icontains=q) |
            Q(ville__icontains=q) |
            Q(quartier__icontains=q) |
            Q(adresse__icontains=q) |
            Q(proprietaire__nom__icontains=q) |
            Q(proprietaire__prenom__icontains=q)
        )

    if statut:
        terrains = terrains.filter(statut=statut)

    if type_operation:
        terrains = terrains.filter(type_operation=type_operation)

    total_terrains = terrains.count()
    terrains_libres = terrains.filter(statut="libre").count()
    terrains_construction = terrains.filter(statut="construction").count()

    valeur_totale = terrains.aggregate(
        total=Sum("prix")
    )["total"] or Decimal("0.00")

    return render(request, "terrains.html", {
        "terrains": terrains,
        "q": q,
        "statut": statut,
        "type_operation": type_operation,
        "total_terrains": total_terrains,
        "terrains_libres": terrains_libres,
        "terrains_construction": terrains_construction,
        "valeur_totale": valeur_totale,
    })


@login_required(login_url="login")
def ajouter_terrain(request):
    agence = get_agence(request.user)

    proprietaires = Proprietaire.objects.filter(
        agence=agence
    ).order_by("nom", "prenom")

    if request.method == "POST":
        proprietaire_id = request.POST.get("proprietaire")
        titre = request.POST.get("titre", "").strip()
        type_operation = request.POST.get("type_operation", "vente")
        statut = request.POST.get("statut", "libre")
        qualite = request.POST.get("qualite", "15/20")
        pays = request.POST.get("pays", "Mali").strip()
        ville = request.POST.get("ville", "").strip()
        quartier = request.POST.get("quartier", "").strip()
        adresse = request.POST.get("adresse", "").strip()
        superficie = request.POST.get("superficie", "0")
        prix = request.POST.get("prix", "0")
        description = request.POST.get("description", "").strip()
        document_disponible = request.POST.get("document_disponible") == "on"

        if not titre or not ville:
            messages.error(request, "Le titre et la ville sont obligatoires.")
            return redirect("ajouter_terrain")

        proprietaire = None
        if proprietaire_id:
            proprietaire = get_object_or_404(
                Proprietaire,
                id=proprietaire_id,
                agence=agence
            )

        try:
            superficie = Decimal(superficie or "0")
        except:
            superficie = Decimal("0.00")

        try:
            prix = Decimal(prix or "0")
        except:
            prix = Decimal("0.00")

        Terrain.objects.create(
            agence=agence,
            proprietaire=proprietaire,
            titre=titre,
            type_operation=type_operation,
            statut=statut,
            qualite=qualite,
            pays=pays,
            ville=ville,
            quartier=quartier,
            adresse=adresse,
            superficie=superficie,
            prix=prix,
            description=description,
            document_disponible=document_disponible,
            actif=True
        )

        messages.success(request, "Terrain ajouté avec succès.")
        return redirect("terrains")

    return render(request, "ajouter_terrain.html", {
        "proprietaires": proprietaires,
        "types": Terrain.TYPE_OPERATION,
        "statuts": Terrain.STATUT_TERRAIN,
        "qualites": Terrain.QUALITE_TERRAIN,
    })


@login_required(login_url="login")
def detail_terrain(request, terrain_id):
    agence = get_agence(request.user)

    terrain = get_object_or_404(
        Terrain.objects.select_related("proprietaire"),
        id=terrain_id,
        agence=agence
    )

    return render(request, "detail_terrain.html", {
        "terrain": terrain,
    })




@login_required(login_url="login")
def supprimer_depense(request, depense_id):
    agence = get_agence(request.user)

    depense = get_object_or_404(
        Depense,
        id=depense_id,
        agence=agence
    )

    type_depense = depense.type_depense

    depense.delete()

    if type_depense == "proprietaire":
        return redirect("depenses_proprietaires")

    return redirect("depenses_agence")






from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import NoReverseMatch

from .models import (
    Paiement,
    Location,
    Locataire,
    Batiment,
)

import base64
import binascii
import logging
import uuid

from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage
from django.core.validators import validate_email
from django.db import models, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import NoReverseMatch, reverse
from django.utils import timezone


logger = logging.getLogger(__name__)


# =========================================================
# CONVERTIR UNE SIGNATURE BASE64 EN IMAGE
# =========================================================
def convertir_signature_base64(
    signature_base64,
    prefixe
):

    if not signature_base64:
        raise ValueError(
            "La signature est vide."
        )

    if not signature_base64.startswith("data:image/"):
        raise ValueError(
            "Le format de la signature est invalide."
        )

    if ";base64," not in signature_base64:
        raise ValueError(
            "La signature n’est pas correctement encodée."
        )

    try:
        entete, contenu_base64 = signature_base64.split(
            ";base64,",
            1
        )

        type_mime = entete.replace(
            "data:",
            ""
        ).lower()

        extensions_autorisees = {
            "image/png": "png",
            "image/jpeg": "jpg",
            "image/jpg": "jpg",
            "image/webp": "webp",
        }

        extension = extensions_autorisees.get(
            type_mime
        )

        if not extension:
            raise ValueError(
                "Le type d’image de la signature n’est pas autorisé."
            )

        contenu_decode = base64.b64decode(
            contenu_base64,
            validate=True
        )

        # Maximum 5 Mo par signature
        if len(contenu_decode) > 5 * 1024 * 1024:
            raise ValueError(
                "La signature est trop volumineuse."
            )

        nom_fichier = (
            f"{prefixe}_{uuid.uuid4().hex}.{extension}"
        )

        return ContentFile(
            contenu_decode,
            name=nom_fichier
        )

    except (
        ValueError,
        TypeError,
        binascii.Error
    ) as erreur:

        raise ValueError(
            "Impossible de convertir la signature."
        ) from erreur


# =========================================================
# ENREGISTRER UNE SIGNATURE SUR LE PAIEMENT
# =========================================================
def enregistrer_signature_paiement(
    paiement,
    nom_champ,
    signature_base64,
    fichier_signature
):

    champ_modele = Paiement._meta.get_field(
        nom_champ
    )

    # ImageField et FileField
    if isinstance(
        champ_modele,
        models.FileField
    ):

        champ_fichier = getattr(
            paiement,
            nom_champ
        )

        champ_fichier.save(
            fichier_signature.name,
            fichier_signature,
            save=False
        )

        return

    # TextField pouvant conserver le Base64
    if isinstance(
        champ_modele,
        models.TextField
    ):

        setattr(
            paiement,
            nom_champ,
            signature_base64
        )

        return

    # CharField uniquement si la taille est suffisante
    if isinstance(
        champ_modele,
        models.CharField
    ):

        longueur_maximale = (
            champ_modele.max_length or 0
        )

        if longueur_maximale < len(signature_base64):
            raise ValueError(
                f"Le champ {nom_champ} est trop court. "
                "Utilisez plutôt un ImageField ou un TextField."
            )

        setattr(
            paiement,
            nom_champ,
            signature_base64
        )

        return

    raise ValueError(
        f"Le champ {nom_champ} doit être un "
        "ImageField, FileField ou TextField."
    )


# =========================================================
# ENVOYER LE REÇU AU LOCATAIRE
# =========================================================
def envoyer_recu_paiement_email(
    request,
    paiement,
    locataire,
    batiment,
    employe,
    destinataire
):

    nom_locataire = (
        f"{locataire.prenom} {locataire.nom}"
    ).strip()

    nom_employe = (
        f"{employe.prenom} {employe.nom}"
    ).strip()

    nom_batiment = getattr(
        batiment,
        "nom",
        str(batiment)
    )

    numero_recu = getattr(
        paiement,
        "numero_recu",
        ""
    )

    montant = getattr(
        paiement,
        "montant",
        Decimal("0")
    )

    mois = getattr(
        paiement,
        "mois",
        ""
    )

    statut = getattr(
        paiement,
        "statut",
        "paye"
    )

    try:
        url_recu = request.build_absolute_uri(
            reverse(
                "imprimer_paiement",
                args=[paiement.id]
            )
        )

    except NoReverseMatch:
        url_recu = ""

    sujet = (
        f"Confirmation de paiement – Reçu {numero_recu}"
    )

    contenu = [
        f"Bonjour {nom_locataire},",
        "",
        "Nous confirmons que votre paiement a été "
        "enregistré avec succès.",
        "",
        f"Numéro du reçu : {numero_recu}",
        f"Montant payé : {montant} FCFA",
        f"Mois concerné : {mois}",
        f"Bâtiment : {nom_batiment}",
        f"Statut : {statut}",
        f"Paiement enregistré par : {nom_employe}",
        f"Date d’enregistrement : "
        f"{timezone.localtime():%d/%m/%Y à %H:%M}",
    ]

    if url_recu:
        contenu.extend([
            "",
            "Vous pouvez consulter votre reçu ici :",
            url_recu,
        ])

    contenu.extend([
        "",
        "Les signatures du locataire et de l’employé "
        "ont été enregistrées avec le paiement.",
        "",
        "Cordialement,",
        f"{getattr(employe.agence, 'nom', 'Gestion immobilière')}",
    ])

    message = "\n".join(contenu)

    courriel = EmailMessage(
        subject=sujet,
        body=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[destinataire]
    )

    courriel.send(
        fail_silently=False
    )


# =========================================================
# AJOUTER UN PAIEMENT PAR UN EMPLOYÉ
# =========================================================
@login_required(login_url="login")
def ajouter_paiement_employe(request):

    # =====================================================
    # 1. EMPLOYÉ CONNECTÉ
    # =====================================================
    employe = get_employe_autorise(request)
    agence = employe.agence

    # =====================================================
    # 2. LOCATAIRES ET BÂTIMENTS DE SON AGENCE
    # =====================================================
    locataires = Locataire.objects.filter(
        agence=agence
    ).order_by(
        "nom",
        "prenom"
    )

    batiments = Batiment.objects.filter(
        agence=agence
    ).select_related(
        "proprietaire"
    ).order_by(
        "nom"
    )

    contexte = {
        "employe": employe,
        "agence": agence,
        "locataires": locataires,
        "batiments": batiments,
    }

    # =====================================================
    # 3. AFFICHAGE DU FORMULAIRE
    # =====================================================
    if request.method != "POST":

        return render(
            request,
            "ajouter_paiement_employe.html",
            contexte
        )

    # =====================================================
    # 4. RÉCUPÉRATION DES DONNÉES
    # =====================================================
    locataire_id = request.POST.get(
        "locataire",
        ""
    ).strip()

    batiment_id = request.POST.get(
        "batiment",
        ""
    ).strip()

    montant_str = request.POST.get(
        "montant",
        ""
    ).strip().replace(",", ".")

    mois = request.POST.get(
        "mois",
        ""
    ).strip()

    mode_paiement = request.POST.get(
        "mode_paiement",
        "espece"
    ).strip()

    statut = request.POST.get(
        "statut",
        "paye"
    ).strip()

    numero_recu = request.POST.get(
        "numero_recu",
        ""
    ).strip()

    numero_appartement = request.POST.get(
        "numero_appartement",
        ""
    ).strip()

    date_debut = request.POST.get(
        "date_debut",
        ""
    ).strip()

    signature_employe_base64 = request.POST.get(
        "signature_employe",
        ""
    ).strip()

    signature_locataire_base64 = request.POST.get(
        "signature_locataire",
        ""
    ).strip()

    commentaire = request.POST.get(
        "commentaire",
        ""
    ).strip()

    email_locataire_saisi = request.POST.get(
        "email_locataire",
        ""
    ).strip()

    envoyer_recu_email = (
        request.POST.get(
            "envoyer_recu_email"
        ) == "1"
    )

    confirmation_paiement = (
        request.POST.get(
            "confirmation_paiement"
        ) == "1"
    )

    justificatif = request.FILES.get(
        "justificatif"
    )

    # =====================================================
    # 5. VALIDATION DES CHAMPS OBLIGATOIRES
    # =====================================================
    if not locataire_id:

        messages.error(
            request,
            "Veuillez sélectionner un locataire."
        )

        return render(
            request,
            "ajouter_paiement_employe.html",
            contexte
        )

    if not batiment_id:

        messages.error(
            request,
            "Veuillez sélectionner un bâtiment."
        )

        return render(
            request,
            "ajouter_paiement_employe.html",
            contexte
        )

    if not montant_str:

        messages.error(
            request,
            "Veuillez saisir le montant payé."
        )

        return render(
            request,
            "ajouter_paiement_employe.html",
            contexte
        )

    if not mois:

        messages.error(
            request,
            "Veuillez indiquer le mois concerné."
        )

        return render(
            request,
            "ajouter_paiement_employe.html",
            contexte
        )

    if not numero_recu:

        messages.error(
            request,
            "Veuillez saisir le numéro du reçu."
        )

        return render(
            request,
            "ajouter_paiement_employe.html",
            contexte
        )

    if not signature_employe_base64:

        messages.error(
            request,
            "La signature dessinée de l’employé est obligatoire."
        )

        return render(
            request,
            "ajouter_paiement_employe.html",
            contexte
        )

    if not signature_locataire_base64:

        messages.error(
            request,
            "La signature dessinée du locataire est obligatoire."
        )

        return render(
            request,
            "ajouter_paiement_employe.html",
            contexte
        )

    if not confirmation_paiement:

        messages.error(
            request,
            "Vous devez confirmer que le paiement a été effectué."
        )

        return render(
            request,
            "ajouter_paiement_employe.html",
            contexte
        )

    # =====================================================
    # 6. VALIDATION DU MONTANT
    # =====================================================
    try:
        montant = Decimal(
            montant_str
        )

        if not montant.is_finite():
            raise InvalidOperation

        if montant <= Decimal("0"):
            raise InvalidOperation

    except (
        InvalidOperation,
        ValueError
    ):

        messages.error(
            request,
            "Le montant saisi est invalide."
        )

        return render(
            request,
            "ajouter_paiement_employe.html",
            contexte
        )

    # =====================================================
    # 7. VÉRIFICATION DU STATUT
    # =====================================================
    statuts_valides = [
        "paye",
        "attente",
        "retard",
    ]

    if statut not in statuts_valides:
        statut = "paye"

    # =====================================================
    # 8. LOCATAIRE ET BÂTIMENT
    # =====================================================
    locataire = get_object_or_404(
        Locataire,
        id=locataire_id,
        agence=agence
    )

    batiment = get_object_or_404(
        Batiment,
        id=batiment_id,
        agence=agence
    )

    contexte["locataire"] = locataire
    contexte["batiment_selectionne"] = batiment

    # =====================================================
    # 9. COURRIEL DU LOCATAIRE
    # =====================================================
    email_locataire = (
        email_locataire_saisi
        or getattr(
            locataire,
            "email",
            ""
        )
        or ""
    ).strip()

    if envoyer_recu_email:

        if not email_locataire:

            messages.error(
                request,
                "Veuillez saisir le courriel du locataire "
                "pour envoyer le reçu."
            )

            return render(
                request,
                "ajouter_paiement_employe.html",
                contexte
            )

        try:
            validate_email(
                email_locataire
            )

        except ValidationError:

            messages.error(
                request,
                "L’adresse courriel du locataire est invalide."
            )

            return render(
                request,
                "ajouter_paiement_employe.html",
                contexte
            )

    # =====================================================
    # 10. VALIDATION ET CONVERSION DES SIGNATURES
    # =====================================================
    try:
        fichier_signature_employe = (
            convertir_signature_base64(
                signature_employe_base64,
                "signature_employe"
            )
        )

        fichier_signature_locataire = (
            convertir_signature_base64(
                signature_locataire_base64,
                "signature_locataire"
            )
        )

    except ValueError as erreur:

        messages.error(
            request,
            str(erreur)
        )

        return render(
            request,
            "ajouter_paiement_employe.html",
            contexte
        )

    # =====================================================
    # 11. RECHERCHE DE LA LOCATION ACTIVE
    # =====================================================
    champs_location = {
        champ.name
        for champ in Location._meta.get_fields()
    }

    filtres_location = {
        "locataire": locataire,
    }

    if "batiment" in champs_location:

        filtres_location["batiment"] = batiment

    elif "chambre" in champs_location:

        filtres_location[
            "chambre__batiment"
        ] = batiment

    elif "logement" in champs_location:

        filtres_location[
            "logement__batiment"
        ] = batiment

    if "active" in champs_location:

        filtres_location["active"] = True

    elif "actif" in champs_location:

        filtres_location["actif"] = True

    location = Location.objects.filter(
        **filtres_location
    ).select_related(
        "locataire"
    ).first()

    if not location:

        messages.error(
            request,
            "Aucune location active ne correspond à ce locataire "
            "et à ce bâtiment."
        )

        return render(
            request,
            "ajouter_paiement_employe.html",
            contexte
        )

    # =====================================================
    # 12. CHAMPS DU MODÈLE PAIEMENT
    # =====================================================
    champs_paiement = {
        champ.name
        for champ in Paiement._meta.get_fields()
    }

    champs_signatures_manquants = []

    if "signature_employe" not in champs_paiement:
        champs_signatures_manquants.append(
            "signature_employe"
        )

    if "signature_locataire" not in champs_paiement:
        champs_signatures_manquants.append(
            "signature_locataire"
        )

    if champs_signatures_manquants:

        messages.error(
            request,
            (
                "Les champs suivants manquent dans le modèle "
                f"Paiement : {', '.join(champs_signatures_manquants)}."
            )
        )

        return render(
            request,
            "ajouter_paiement_employe.html",
            contexte
        )

    # =====================================================
    # 13. VÉRIFICATION DU NUMÉRO DE REÇU
    # =====================================================
    filtre_recu = {
        "numero_recu": numero_recu
    }

    if "agence" in champs_paiement:
        filtre_recu["agence"] = agence

    if Paiement.objects.filter(
        **filtre_recu
    ).exists():

        messages.error(
            request,
            "Ce numéro de reçu existe déjà."
        )

        return render(
            request,
            "ajouter_paiement_employe.html",
            contexte
        )

    # =====================================================
    # 14. CALCUL DE LA COMMISSION
    # =====================================================
    commission_agence = (
        montant * Decimal("0.10")
    ).quantize(
        Decimal("0.01")
    )

    montant_proprietaire = (
        montant * Decimal("0.90")
    ).quantize(
        Decimal("0.01")
    )

    # =====================================================
    # 15. PRÉPARATION DU PAIEMENT
    # =====================================================
    donnees_paiement = {
        "location": location,
        "montant": montant,
        "mois": mois,
        "statut": statut,
        "numero_recu": numero_recu,
    }

    if "agence" in champs_paiement:
        donnees_paiement["agence"] = agence

    # Mode de paiement
    if "mode_paiement" in champs_paiement:

        donnees_paiement[
            "mode_paiement"
        ] = mode_paiement

    elif "mode" in champs_paiement:

        donnees_paiement[
            "mode"
        ] = mode_paiement

    # Employé connecté
    if "agent" in champs_paiement:

        donnees_paiement[
            "agent"
        ] = employe

    elif "employe" in champs_paiement:

        donnees_paiement[
            "employe"
        ] = employe

    # Commission agence
    if "commission_agence" in champs_paiement:

        donnees_paiement[
            "commission_agence"
        ] = commission_agence

    elif "part_agence" in champs_paiement:

        donnees_paiement[
            "part_agence"
        ] = commission_agence

    # Part du propriétaire
    if "montant_proprietaire" in champs_paiement:

        donnees_paiement[
            "montant_proprietaire"
        ] = montant_proprietaire

    elif "part_proprietaire" in champs_paiement:

        donnees_paiement[
            "part_proprietaire"
        ] = montant_proprietaire

    # Champs facultatifs
    if "numero_appartement" in champs_paiement:

        donnees_paiement[
            "numero_appartement"
        ] = numero_appartement

    if (
        "date_debut" in champs_paiement
        and date_debut
    ):

        donnees_paiement[
            "date_debut"
        ] = date_debut

    if "commentaire" in champs_paiement:

        donnees_paiement[
            "commentaire"
        ] = commentaire

    if (
        "justificatif" in champs_paiement
        and justificatif
    ):

        donnees_paiement[
            "justificatif"
        ] = justificatif

    if "email_recu" in champs_paiement:

        donnees_paiement[
            "email_recu"
        ] = email_locataire

    elif "email_locataire" in champs_paiement:

        donnees_paiement[
            "email_locataire"
        ] = email_locataire

    if "recu_envoye_email" in champs_paiement:

        donnees_paiement[
            "recu_envoye_email"
        ] = False

    if "date_signature" in champs_paiement:

        donnees_paiement[
            "date_signature"
        ] = timezone.now()

    if "confirmation_paiement" in champs_paiement:

        donnees_paiement[
            "confirmation_paiement"
        ] = True

    # =====================================================
    # 16. ENREGISTREMENT DU PAIEMENT ET DES SIGNATURES
    # =====================================================
    try:
        with transaction.atomic():

            paiement = Paiement.objects.create(
                **donnees_paiement
            )

            enregistrer_signature_paiement(
                paiement=paiement,
                nom_champ="signature_employe",
                signature_base64=signature_employe_base64,
                fichier_signature=fichier_signature_employe
            )

            enregistrer_signature_paiement(
                paiement=paiement,
                nom_champ="signature_locataire",
                signature_base64=signature_locataire_base64,
                fichier_signature=fichier_signature_locataire
            )

            paiement.save()

    except Exception as erreur:

        logger.exception(
            "Erreur lors de l’enregistrement du paiement."
        )

        messages.error(
            request,
            f"Impossible d’enregistrer le paiement : {erreur}"
        )

        return render(
            request,
            "ajouter_paiement_employe.html",
            contexte
        )

    # =====================================================
    # 17. ENVOI DU REÇU PAR COURRIEL
    # =====================================================
    recu_envoye = False

    if envoyer_recu_email and email_locataire:

        try:
            envoyer_recu_paiement_email(
                request=request,
                paiement=paiement,
                locataire=locataire,
                batiment=batiment,
                employe=employe,
                destinataire=email_locataire
            )

            recu_envoye = True

            champs_mise_a_jour = {}

            if "recu_envoye_email" in champs_paiement:

                champs_mise_a_jour[
                    "recu_envoye_email"
                ] = True

            elif "recu_envoye" in champs_paiement:

                champs_mise_a_jour[
                    "recu_envoye"
                ] = True

            if champs_mise_a_jour:

                Paiement.objects.filter(
                    id=paiement.id
                ).update(
                    **champs_mise_a_jour
                )

        except Exception:

            logger.exception(
                "Le paiement est enregistré, mais le reçu "
                "n’a pas pu être envoyé."
            )

            messages.warning(
                request,
                (
                    "Le paiement et les signatures ont été "
                    "enregistrés, mais le courriel n’a pas pu "
                    "être envoyé au locataire."
                )
            )

    # =====================================================
    # 18. MESSAGE DE SUCCÈS
    # =====================================================
    message_succes = (
        f"Paiement enregistré avec succès. "
        f"Commission agence : {commission_agence} FCFA. "
        f"Part propriétaire : {montant_proprietaire} FCFA."
    )

    if recu_envoye:

        message_succes += (
            f" Le reçu a été envoyé à {email_locataire}."
        )

    messages.success(
        request,
        message_succes
    )

    # =====================================================
    # 19. OUVERTURE DU REÇU
    # =====================================================
    try:
        return redirect(
            "imprimer_paiement",
            paiement.id
        )

    except NoReverseMatch:
        return redirect(
            "espace_employe"
        )



from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
@login_required(login_url="login")
def espace_batiments_employe(request):

    employe = get_employe_autorise(request)
    agence = employe.agence

    batiments = list(
        Batiment.objects.filter(
            agence=agence
        ).select_related(
            "proprietaire"
        ).prefetch_related(
            "chambres",
            "chambres__locations",
            "chambres__locations__locataire",
        ).order_by(
            "nom"
        )
    )

    total_logements_general = 0
    total_occupes_general = 0
    total_libres_general = 0

    for batiment in batiments:

        chambres_actives = [
            chambre
            for chambre in batiment.chambres.all()
            if chambre.actif
        ]

        total_logements = len(chambres_actives)
        total_occupes = 0

        for chambre in chambres_actives:

            location_active = next(
                (
                    location
                    for location in chambre.locations.all()
                    if location.active
                ),
                None
            )

            if location_active:
                total_occupes += 1

        total_libres = max(
            total_logements - total_occupes,
            0
        )

        if total_logements > 0:
            taux_occupation = round(
                total_occupes * 100 / total_logements
            )
        else:
            taux_occupation = 0

        if total_logements == 0:
            statut_occupation = "Aucun logement"

        elif total_occupes == 0:
            statut_occupation = "Libre"

        elif total_occupes == total_logements:
            statut_occupation = "Complètement occupé"

        else:
            statut_occupation = "Partiellement occupé"

        batiment.total_logements_employe = total_logements
        batiment.total_occupes_employe = total_occupes
        batiment.total_libres_employe = total_libres
        batiment.taux_occupation_employe = taux_occupation
        batiment.statut_occupation_employe = statut_occupation

        total_logements_general += total_logements
        total_occupes_general += total_occupes
        total_libres_general += total_libres

    context = {
        "employe": employe,
        "agence": agence,
        "batiments": batiments,

        "total_batiments": len(batiments),
        "total_logements": total_logements_general,
        "total_occupes": total_occupes_general,
        "total_libres": total_libres_general,
    }

    return render(
        request,
        "espace_batiments_employe.html",  # PLURIEL
        context
    )

@login_required(login_url="login")
def espace_batiment_employe(request, batiment_id):

    employe = get_employe_autorise(request)
    agence = employe.agence

    batiment = get_object_or_404(
        Batiment.objects.select_related(
            "proprietaire",
            "agence",
        ),
        id=batiment_id,
        agence=agence,
    )

    chambres = ChambreLogement.objects.filter(
        batiment=batiment,
        actif=True,
    ).order_by(
        "numero"
    )

    chambres_occupees = []
    chambres_libres = []

    for chambre in chambres:

        bail = (
            Location.objects.filter(
                chambre=chambre,
                batiment=batiment,
                active=True,
            )
            .select_related(
                "locataire"
            )
            .first()
        )

        if bail:

            chambres_occupees.append(
                {
                    "chambre": chambre,
                    "bail": bail,
                    "location": bail,
                    "locataire": bail.locataire,
                }
            )

        else:

            chambres_libres.append(
                chambre
            )

    total_chambres = chambres.count()
    total_occupees = len(chambres_occupees)
    total_libres = len(chambres_libres)

    if total_chambres > 0:
        taux_occupation = round(
            total_occupees * 100 / total_chambres
        )
    else:
        taux_occupation = 0

    context = {
        "employe": employe,
        "agence": agence,
        "batiment": batiment,

        "chambres": chambres,
        "chambres_occupees": chambres_occupees,
        "chambres_libres": chambres_libres,

        "total_chambres_batiment": total_chambres,
        "total_logements_batiment": total_chambres,

        "logements_occupes_batiment": total_occupees,
        "logements_libres_batiment": total_libres,

        "taux_occupation": taux_occupation,

        "occupation_complete": (
            total_chambres > 0
            and total_occupees == total_chambres
        ),

        "occupation_partielle": (
            total_occupees > 0
            and total_occupees < total_chambres
        ),

        "batiment_libre": (
            total_occupees == 0
        ),
    }

    return render(
        request,
        "espace_batiment_employe.html",  # SINGULIER
        context
    )




from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date

from .models import (
    Locataire,
    Location,
    Batiment,
    ChambreLogement,
)


def convertir_decimal(valeur, valeur_defaut="0"):
    """
    Convertit proprement un montant provenant du formulaire.
    Accepte également les nombres contenant une virgule.
    """

    valeur = str(
        valeur if valeur not in [None, ""] else valeur_defaut
    ).strip().replace(",", ".")

    try:
        return Decimal(valeur)

    except InvalidOperation:
        return Decimal(valeur_defaut)


@login_required(login_url="login")
def ajouter_locataire_employe(request):

    # =====================================================
    # 1. EMPLOYÉ CONNECTÉ
    # =====================================================

    employe = get_employe_autorise(request)
    agence = employe.agence

    # =====================================================
    # 2. BÂTIMENTS DE L’AGENCE
    # =====================================================

    batiments = Batiment.objects.filter(
        agence=agence
    ).order_by(
        "nom"
    )

    # =====================================================
    # 3. LOGEMENTS DÉJÀ OCCUPÉS
    # =====================================================

    chambres_occupees_ids = Location.objects.filter(
        agence=agence,
        active=True,
        chambre__isnull=False
    ).values_list(
        "chambre_id",
        flat=True
    )

    # =====================================================
    # 4. LOGEMENTS DISPONIBLES
    # =====================================================

    chambres_disponibles = ChambreLogement.objects.select_related(
        "batiment"
    ).filter(
        batiment__agence=agence,
        actif=True
    ).exclude(
        id__in=chambres_occupees_ids
    ).order_by(
        "batiment__nom",
        "numero",
        "nom"
    )

    contexte = {
        "employe": employe,
        "agence": agence,
        "batiments": batiments,
        "chambres_disponibles": chambres_disponibles,
    }

    # =====================================================
    # 5. AFFICHAGE DU FORMULAIRE
    # =====================================================

    if request.method != "POST":

        return render(
            request,
            "ajouter_locataire_employe.html",
            contexte
        )

    # =====================================================
    # 6. INFORMATIONS DU LOCATAIRE
    # =====================================================

    nom = request.POST.get(
        "nom",
        ""
    ).strip()

    prenom = request.POST.get(
        "prenom",
        ""
    ).strip()

    telephone = request.POST.get(
        "telephone",
        ""
    ).strip()

    email = request.POST.get(
        "email",
        ""
    ).strip()

    date_naissance_str = request.POST.get(
        "date_naissance",
        ""
    ).strip()

    lieu_naissance = request.POST.get(
        "lieu_naissance",
        ""
    ).strip()

    sexe = request.POST.get(
        "sexe",
        ""
    ).strip()

    profession = request.POST.get(
        "profession",
        ""
    ).strip()

    employeur = request.POST.get(
        "employeur",
        ""
    ).strip()

    revenu_mensuel = convertir_decimal(
        request.POST.get("revenu_mensuel")
    )

    adresse_actuelle = request.POST.get(
        "adresse_actuelle",
        ""
    ).strip()

    ville = request.POST.get(
        "ville",
        ""
    ).strip()

    pays = request.POST.get(
        "pays",
        ""
    ).strip()

    contact_urgence_nom = request.POST.get(
        "contact_urgence_nom",
        ""
    ).strip()

    contact_urgence_telephone = request.POST.get(
        "contact_urgence_telephone",
        ""
    ).strip()

    contact_urgence_lien = request.POST.get(
        "contact_urgence_lien",
        ""
    ).strip()

    numero_piece_identite = request.POST.get(
        "numero_piece_identite",
        ""
    ).strip()

    date_expiration_piece_str = request.POST.get(
        "date_expiration_piece",
        ""
    ).strip()

    # =====================================================
    # 7. LOCATION ET CAUTION
    # =====================================================

    batiment_id = request.POST.get(
        "batiment",
        ""
    ).strip()

    chambre_id = request.POST.get(
        "chambre",
        ""
    ).strip()

    loyer = convertir_decimal(
        request.POST.get("loyer")
    )

    caution = convertir_decimal(
        request.POST.get("caution")
    )

    caution_payee = (
        request.POST.get("caution_payee") == "on"
    )

    date_debut_str = request.POST.get(
        "date_debut",
        ""
    ).strip()

    date_caution_str = request.POST.get(
        "date_caution",
        ""
    ).strip()

    observation_caution = request.POST.get(
        "observation_caution",
        ""
    ).strip()

    # =====================================================
    # 8. VALIDATIONS
    # =====================================================

    if not nom:

        messages.error(
            request,
            "Le nom du locataire est obligatoire."
        )

        return render(
            request,
            "ajouter_locataire_employe.html",
            contexte
        )

    if not telephone:

        messages.error(
            request,
            "Le numéro de téléphone est obligatoire."
        )

        return render(
            request,
            "ajouter_locataire_employe.html",
            contexte
        )

    if not batiment_id or not chambre_id:

        messages.error(
            request,
            "Veuillez sélectionner un bâtiment et un logement."
        )

        return render(
            request,
            "ajouter_locataire_employe.html",
            contexte
        )

    date_debut = parse_date(date_debut_str)

    if not date_debut:

        messages.error(
            request,
            "La date de début de la location est obligatoire."
        )

        return render(
            request,
            "ajouter_locataire_employe.html",
            contexte
        )

    if loyer <= 0:

        messages.error(
            request,
            "Le montant du loyer doit être supérieur à zéro."
        )

        return render(
            request,
            "ajouter_locataire_employe.html",
            contexte
        )

    # =====================================================
    # 9. BÂTIMENT DE LA BONNE AGENCE
    # =====================================================

    batiment = get_object_or_404(
        Batiment,
        id=batiment_id,
        agence=agence
    )

    # =====================================================
    # 10. LOGEMENT DU BON BÂTIMENT
    # =====================================================

    chambre = get_object_or_404(
        ChambreLogement,
        id=chambre_id,
        batiment=batiment,
        batiment__agence=agence,
        actif=True
    )

    # =====================================================
    # 11. VÉRIFIER QUE LE LOGEMENT EST LIBRE
    # =====================================================

    logement_deja_occupe = Location.objects.filter(
        agence=agence,
        chambre=chambre,
        active=True
    ).exists()

    if logement_deja_occupe:

        messages.error(
            request,
            "Ce logement est déjà occupé. "
            "Veuillez sélectionner un autre logement."
        )

        return render(
            request,
            "ajouter_locataire_employe.html",
            contexte
        )

    # =====================================================
    # 12. DATES OPTIONNELLES
    # =====================================================

    date_naissance = (
        parse_date(date_naissance_str)
        if date_naissance_str
        else None
    )

    date_expiration_piece = (
        parse_date(date_expiration_piece_str)
        if date_expiration_piece_str
        else None
    )

    if caution_payee:

        date_caution = (
            parse_date(date_caution_str)
            if date_caution_str
            else timezone.localdate()
        )

    else:

        date_caution = None

    # =====================================================
    # 13. ENREGISTREMENT
    # =====================================================

    try:

        with transaction.atomic():

            # Nouvelle vérification avec verrouillage
            chambre_verrouillee = ChambreLogement.objects.select_for_update().get(
                id=chambre.id,
                batiment__agence=agence,
                actif=True
            )

            if Location.objects.filter(
                agence=agence,
                chambre=chambre_verrouillee,
                active=True
            ).exists():

                messages.error(
                    request,
                    "Ce logement vient d’être occupé par un autre locataire."
                )

                return redirect(
                    "ajouter_locataire_employe"
                )

            # =============================================
            # CRÉER LE LOCATAIRE
            # =============================================

            locataire = Locataire.objects.create(
                agence=agence,

                nom=nom,
                prenom=prenom,
                telephone=telephone,
                email=email,

                date_naissance=date_naissance,
                lieu_naissance=lieu_naissance,
                sexe=sexe,

                profession=profession,
                employeur=employeur,
                revenu_mensuel=revenu_mensuel,

                adresse_actuelle=adresse_actuelle,
                ville=ville,
                pays=pays,

                contact_urgence_nom=contact_urgence_nom,
                contact_urgence_telephone=contact_urgence_telephone,
                contact_urgence_lien=contact_urgence_lien,

                numero_piece_identite=numero_piece_identite,
                date_expiration_piece=date_expiration_piece,

                piece_identite=request.FILES.get(
                    "piece_identite"
                ),

                acte_naissance=request.FILES.get(
                    "acte_naissance"
                ),

                photo=request.FILES.get(
                    "photo"
                ),

                actif=True
            )

            # =============================================
            # CRÉER LA LOCATION
            # =============================================

            Location.objects.create(
                agence=agence,
                locataire=locataire,
                batiment=batiment,
                chambre=chambre_verrouillee,

                numero_appartement=(
                    chambre_verrouillee.numero
                    or chambre_verrouillee.nom
                    or ""
                ),

                loyer=loyer,

                caution=caution,
                caution_payee=caution_payee,
                date_caution=date_caution,
                observation_caution=observation_caution,

                date_debut=date_debut,
                active=True
            )

        messages.success(
            request,
            (
                f"Le locataire {prenom} {nom} a été enregistré "
                f"avec succès dans le logement "
                f"{chambre.numero or chambre.nom}."
            )
        )

        return redirect(
            "espace_employe"
        )

    except Exception as erreur:

        messages.error(
            request,
            f"Impossible d’enregistrer le locataire : {erreur}"
        )

        return render(
            request,
            "ajouter_locataire_employe.html",
            contexte
        )





@login_required(login_url="login")
def locations_employe(request):

    # =====================================================
    # 1. EMPLOYÉ CONNECTÉ
    # =====================================================

    employe = get_employe_autorise(request)
    agence = employe.agence

    # =====================================================
    # 2. PARAMÈTRES DE RECHERCHE
    # =====================================================

    recherche = request.GET.get(
        "q",
        ""
    ).strip()

    statut = request.GET.get(
        "statut",
        "toutes"
    ).strip().lower()

    # =====================================================
    # 3. TOUTES LES LOCATIONS DE L’AGENCE
    # =====================================================

    toutes_locations = Location.objects.select_related(
        "locataire",
        "batiment"
    ).filter(
        agence=agence
    )

    # =====================================================
    # 4. STATISTIQUES GÉNÉRALES
    # =====================================================

    total_locations = toutes_locations.count()

    total_locations_actives = toutes_locations.filter(
        active=True
    ).count()

    total_locations_terminees = toutes_locations.filter(
        active=False
    ).count()

    total_loyers_actifs = toutes_locations.filter(
        active=True
    ).aggregate(
        total=Sum("loyer")
    )["total"] or Decimal("0")

    total_cautions_payees = toutes_locations.filter(
        caution_payee=True
    ).aggregate(
        total=Sum("caution")
    )["total"] or Decimal("0")

    # =====================================================
    # 5. FILTRAGE
    # =====================================================

    locations = toutes_locations

    if recherche:

        locations = locations.filter(

            Q(
                locataire__nom__icontains=recherche
            )

            |

            Q(
                locataire__prenom__icontains=recherche
            )

            |

            Q(
                locataire__telephone__icontains=recherche
            )

            |

            Q(
                locataire__email__icontains=recherche
            )

            |

            Q(
                batiment__nom__icontains=recherche
            )

            |

            Q(
                batiment__code_batiment__icontains=recherche
            )

            |

            Q(
                numero_appartement__icontains=recherche
            )
        )

    if statut == "actives":

        locations = locations.filter(
            active=True
        )

    elif statut == "terminees":

        locations = locations.filter(
            active=False
        )

    # =====================================================
    # 6. CLASSEMENT
    # =====================================================

    locations = locations.order_by(
        "-active",
        "-date_debut",
        "-id"
    )

    # =====================================================
    # 7. CONTEXTE
    # =====================================================

    contexte = {
        "employe": employe,
        "agence": agence,

        "locations": locations,

        "recherche": recherche,
        "statut_selectionne": statut,

        "total_locations": total_locations,
        "total_locations_actives": total_locations_actives,
        "total_locations_terminees": total_locations_terminees,

        "total_loyers_actifs": total_loyers_actifs,
        "total_cautions_payees": total_cautions_payees,

        "total_resultats": locations.count(),
    }

    return render(
        request,
        "locations_employe.html",
        contexte
    )




import base64
import io

import qrcode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.utils import timezone

from .forms import (
    CentreCommercialForm,
    ContratCommercialForm,
    LocalCommercialForm,
    OccupantCommercialForm,
    appliquer_style_formulaire,
)

from .models import (
    Batiment,
    CentreCommercial,
    ContratCommercial,
    LocalCommercial,
    Proprietaire,
)


# =========================================================
# LISTE DES CENTRES COMMERCIAUX
# =========================================================

@login_required(login_url="login")
def centres_commerciaux(request):

    agence = get_agence(request.user)

    recherche = request.GET.get(
        "q",
        ""
    ).strip()

    type_centre = request.GET.get(
        "type",
        ""
    ).strip()

    statut = request.GET.get(
        "statut",
        ""
    ).strip()

    # =====================================================
    # REQUÊTE PRINCIPALE
    # =====================================================

    centres_base = (
        CentreCommercial.objects
        .select_related(
            "proprietaire",
            "batiment",
        )
        .filter(
            agence=agence,
        )
        .annotate(

            total_locaux=Count(
                "locaux",
                filter=Q(
                    locaux__actif=True
                ),
                distinct=True,
            ),

            locaux_libres=Count(
                "locaux",
                filter=Q(
                    locaux__actif=True,
                    locaux__statut="libre",
                ),
                distinct=True,
            ),

            locaux_occupes=Count(
                "locaux",
                filter=Q(
                    locaux__actif=True,
                    locaux__statut="occupe",
                ),
                distinct=True,
            ),

            locaux_reserves=Count(
                "locaux",
                filter=Q(
                    locaux__actif=True,
                    locaux__statut="reserve",
                ),
                distinct=True,
            ),
        )
    )

    # =====================================================
    # STATISTIQUES
    # =====================================================

    total_centres = centres_base.count()

    total_locaux = LocalCommercial.objects.filter(
        centre__agence=agence,
        actif=True,
    ).count()

    total_locaux_libres = LocalCommercial.objects.filter(
        centre__agence=agence,
        actif=True,
        statut="libre",
    ).count()

    total_locaux_occupes = LocalCommercial.objects.filter(
        centre__agence=agence,
        actif=True,
        statut="occupe",
    ).count()

    centres = centres_base

    # =====================================================
    # RECHERCHE
    # =====================================================

    if recherche:

        centres = centres.filter(

            Q(
                nom__icontains=recherche
            )

            |

            Q(
                code__icontains=recherche
            )

            |

            Q(
                ville__icontains=recherche
            )

            |

            Q(
                quartier__icontains=recherche
            )

            |

            Q(
                adresse__icontains=recherche
            )

            |

            Q(
                proprietaire__nom__icontains=recherche
            )

            |

            Q(
                proprietaire__prenom__icontains=recherche
            )

            |

            Q(
                batiment__nom__icontains=recherche
            )
        )

    # =====================================================
    # FILTRE TYPE
    # =====================================================

    if type_centre:

        centres = centres.filter(
            type_centre=type_centre
        )

    # =====================================================
    # FILTRE STATUT
    # =====================================================

    if statut == "actifs":

        centres = centres.filter(
            actif=True
        )

    elif statut == "inactifs":

        centres = centres.filter(
            actif=False
        )

    # =====================================================
    # CLASSEMENT
    # =====================================================

    centres = centres.order_by(
        "-actif",
        "nom",
    )

    # =====================================================
    # CONTEXTE
    # =====================================================

    contexte = {
        "agence": agence,

        "centres": centres,

        "recherche": recherche,
        "type_selectionne": type_centre,
        "statut_selectionne": statut,

        "types_centres": CentreCommercial.TYPE_CHOICES,

        "total_centres": total_centres,
        "total_resultats": centres.count(),

        "total_locaux": total_locaux,
        "total_locaux_libres": total_locaux_libres,
        "total_locaux_occupes": total_locaux_occupes,
    }

    return render(
        request,
        "centre_commercial/centres_commerciaux.html",
        contexte,
    )


# =========================================================
# AJOUTER UN CENTRE COMMERCIAL
# =========================================================

@login_required(login_url="login")
def ajouter_centre_commercial(request):

    agence = get_agence(request.user)

    formulaire = CentreCommercialForm(
        request.POST or None
    )

    # =====================================================
    # PROPRIÉTAIRES DE L'AGENCE
    # =====================================================

    formulaire.fields["proprietaire"].queryset = (
        Proprietaire.objects
        .filter(
            agence=agence
        )
        .order_by(
            "nom",
            "prenom"
        )
    )

    # =====================================================
    # BÂTIMENTS DE L'AGENCE
    # =====================================================

    formulaire.fields["batiment"].queryset = (
        Batiment.objects
        .filter(
            agence=agence
        )
        .order_by(
            "nom"
        )
    )

    appliquer_style_formulaire(
        formulaire
    )

    # =====================================================
    # ENREGISTREMENT
    # =====================================================

    if (
        request.method == "POST"
        and formulaire.is_valid()
    ):

        centre = formulaire.save(
            commit=False
        )

        centre.agence = agence
        centre.save()

        messages.success(
            request,
            "Le centre commercial a été enregistré avec succès.",
        )

        return redirect(
            "detail_centre_commercial",
            centre_id=centre.id,
        )

    return render(
        request,
        "centre_commercial/formulaire.html",
        {
            "formulaire": formulaire,

            "titre": (
                "Ajouter un centre commercial"
            ),

            "description": (
                "Créer un centre commercial, une galerie, "
                "un marché, une station ou un immeuble commercial."
            ),

            "icone": "fa-store",
        },
    )


# =========================================================
# DÉTAIL D'UN CENTRE COMMERCIAL
# =========================================================

@login_required(login_url="login")
def detail_centre_commercial(request, centre_id):

    agence = get_agence(request.user)

    centre = get_object_or_404(
        CentreCommercial.objects.select_related(
            "proprietaire",
            "batiment",
        ),
        id=centre_id,
        agence=agence,
    )

    # =====================================================
    # LOCAUX
    # =====================================================

    locaux = (
        centre.locaux
        .filter(
            actif=True
        )
        .prefetch_related(
            "contrats",
            "contrats__occupant",
        )
        .order_by(
            "numero"
        )
    )

    # =====================================================
    # CONTRATS ACTIFS
    # =====================================================

    contrats_actifs = (
        ContratCommercial.objects
        .select_related(
            "occupant",
            "local",
        )
        .filter(
            agence=agence,
            local__centre=centre,
            actif=True,
        )
        .order_by(
            "-date_debut"
        )
    )

    # =====================================================
    # STATISTIQUES
    # =====================================================

    total_locaux = locaux.count()

    total_libres = locaux.filter(
        statut="libre"
    ).count()

    total_occupes = locaux.filter(
        statut="occupe"
    ).count()

    total_reserves = locaux.filter(
        statut="reserve"
    ).count()

    total_maintenance = locaux.filter(
        statut="maintenance"
    ).count()

    contexte = {
        "agence": agence,
        "centre": centre,

        "locaux": locaux,
        "contrats_actifs": contrats_actifs,

        "total_locaux": total_locaux,
        "total_libres": total_libres,
        "total_occupes": total_occupes,
        "total_reserves": total_reserves,
        "total_maintenance": total_maintenance,
    }

    return render(
        request,
        "centre_commercial/detail_centre_commercial.html",
        contexte,
    )


# =========================================================
# AJOUTER UN LOCAL COMMERCIAL
# =========================================================

@login_required(login_url="login")
def ajouter_local_commercial(request, centre_id):

    agence = get_agence(request.user)

    centre = get_object_or_404(
        CentreCommercial,
        id=centre_id,
        agence=agence,
        actif=True,
    )

    formulaire = LocalCommercialForm(
        request.POST or None
    )

    appliquer_style_formulaire(
        formulaire
    )

    # =====================================================
    # ENREGISTREMENT
    # =====================================================

    if (
        request.method == "POST"
        and formulaire.is_valid()
    ):

        local = formulaire.save(
            commit=False
        )

        local.centre = centre
        local.save()

        messages.success(
            request,
            "Le local commercial a été ajouté avec succès.",
        )

        return redirect(
            "detail_centre_commercial",
            centre_id=centre.id,
        )

    return render(
        request,
        "centre_commercial/formulaire.html",
        {
            "formulaire": formulaire,

            "titre": (
                "Ajouter un local commercial"
            ),

            "description": (
                f"Ajouter une boutique, un restaurant, "
                f"un bureau ou un autre local dans {centre.nom}."
            ),

            "icone": "fa-shop",
            "centre": centre,
        },
    )


# =========================================================
# ATTRIBUER UN LOCAL À UNE PERSONNE
# =========================================================

@login_required(login_url="login")
def occuper_local_commercial(request, local_id):

    agence = get_agence(request.user)

    local = get_object_or_404(
        LocalCommercial.objects.select_related(
            "centre",
            "centre__proprietaire",
            "centre__batiment",
        ),
        id=local_id,
        centre__agence=agence,
        actif=True,
    )

    # =====================================================
    # VÉRIFICATION AVANT AFFICHAGE
    # =====================================================

    contrat_actif_existant = (
        ContratCommercial.objects.filter(
            agence=agence,
            local=local,
            actif=True,
        ).exists()
    )

    if (
        contrat_actif_existant
        or local.statut == "occupe"
    ):

        messages.error(
            request,
            "Ce local est déjà occupé et possède un contrat actif.",
        )

        return redirect(
            "detail_centre_commercial",
            centre_id=local.centre_id,
        )

    # =====================================================
    # FORMULAIRE DE LA PERSONNE
    # =====================================================

    occupant_form = OccupantCommercialForm(
        request.POST or None,
        request.FILES or None,
        prefix="occupant",
    )

    # =====================================================
    # FORMULAIRE DU CONTRAT
    # =====================================================

    contrat_form = ContratCommercialForm(
        request.POST or None,
        prefix="contrat",
        initial={
            "prix_mensuel": local.prix_mensuel,
            "caution": local.caution,
            "date_debut": timezone.localdate(),
        },
    )

    appliquer_style_formulaire(
        occupant_form
    )

    appliquer_style_formulaire(
        contrat_form
    )

    # =====================================================
    # ENREGISTREMENT
    # =====================================================

    if request.method == "POST":

        occupant_valide = occupant_form.is_valid()
        contrat_valide = contrat_form.is_valid()

        if occupant_valide and contrat_valide:

            try:

                with transaction.atomic():

                    # =====================================
                    # VERROUILLER LE LOCAL
                    # =====================================

                    local_verrouille = get_object_or_404(
                        LocalCommercial.objects
                        .select_for_update()
                        .select_related(
                            "centre"
                        ),
                        id=local.id,
                        centre__agence=agence,
                        actif=True,
                    )

                    # =====================================
                    # REVÉRIFIER LE CONTRAT
                    # =====================================

                    contrat_existant = (
                        ContratCommercial.objects.filter(
                            agence=agence,
                            local=local_verrouille,
                            actif=True,
                        ).exists()
                    )

                    if (
                        contrat_existant
                        or local_verrouille.statut == "occupe"
                    ):

                        messages.error(
                            request,
                            (
                                "Ce local vient d’être attribué "
                                "à une autre personne. "
                                "Veuillez choisir un autre local."
                            ),
                        )

                        return redirect(
                            "detail_centre_commercial",
                            centre_id=local.centre_id,
                        )

                    # =====================================
                    # CRÉER LA PERSONNE OCCUPANTE
                    # =====================================

                    occupant = occupant_form.save(
                        commit=False
                    )

                    occupant.agence = agence
                    occupant.save()

                    # =====================================
                    # CRÉER LE CONTRAT
                    # =====================================

                    contrat = contrat_form.save(
                        commit=False
                    )

                    contrat.agence = agence
                    contrat.local = local_verrouille
                    contrat.occupant = occupant

                    contrat.actif = True
                    contrat.certifie_application = True

                    contrat.save()

                    # =====================================
                    # MARQUER LE LOCAL OCCUPÉ
                    # =====================================

                    LocalCommercial.objects.filter(
                        id=local_verrouille.id
                    ).update(
                        statut="occupe"
                    )

                messages.success(
                    request,
                    (
                        f"Le contrat {contrat.numero_contrat} "
                        f"a été créé avec succès."
                    ),
                )

                return redirect(
                    "detail_contrat_commercial",
                    contrat_id=contrat.id,
                )

            except Exception as erreur:

                messages.error(
                    request,
                    (
                        "Une erreur est survenue pendant "
                        f"l’enregistrement : {erreur}"
                    ),
                )

        else:

            messages.error(
                request,
                (
                    "Le formulaire contient des erreurs. "
                    "Veuillez vérifier les informations "
                    "de la personne et du contrat."
                ),
            )

    contexte = {
        "agence": agence,
        "local": local,
        "centre": local.centre,

        "occupant_form": occupant_form,
        "contrat_form": contrat_form,
    }

    return render(
         request,
        "centre_commercial/occuper_local.html",
        {
        "agence": agence,
        "local": local,
        "occupant_form": occupant_form,
        "contrat_form": contrat_form,
        },
    )

from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, render

from .models import (
    CentreCommercial,
    ContratCommercial,
    LocalCommercial,
)


# =========================================================
# DÉTAIL D'UN CENTRE COMMERCIAL
# =========================================================
@login_required(login_url="login")
def detail_centre_commercial(request, centre_id):

    agence = get_agence(request.user)

    # =====================================================
    # CENTRE COMMERCIAL
    # =====================================================
    centre = get_object_or_404(
        CentreCommercial.objects.select_related(
            "proprietaire",
            "batiment",
        ),
        id=centre_id,
        agence=agence,
    )

    # =====================================================
    # CONTRATS ACTIFS AVEC OCCUPANTS
    # =====================================================
    contrats_actifs_queryset = (
        ContratCommercial.objects
        .select_related(
            "occupant",
            "local",
            "local__centre",
        )
        .filter(
            agence=agence,
            actif=True,
        )
        .order_by(
            "-date_debut",
        )
    )

    # =====================================================
    # LOCAUX DU CENTRE
    # =====================================================
    locaux = list(
        LocalCommercial.objects
        .filter(
            centre=centre,
            actif=True,
        )
        .prefetch_related(
            Prefetch(
                "contrats",
                queryset=contrats_actifs_queryset,
                to_attr="liste_contrats_actifs",
            )
        )
        .order_by(
            "numero",
        )
    )

    # =====================================================
    # CONTRAT ACTIF DE CHAQUE LOCAL
    # =====================================================
    for local in locaux:

        if local.liste_contrats_actifs:
            local.contrat_actif = local.liste_contrats_actifs[0]
        else:
            local.contrat_actif = None

    # =====================================================
    # STATISTIQUES
    # =====================================================
    total_locaux = len(locaux)

    total_occupes = sum(
        1
        for local in locaux
        if local.contrat_actif is not None
    )

    total_libres = sum(
        1
        for local in locaux
        if (
            local.contrat_actif is None
            and local.statut == "libre"
        )
    )

    total_reserves = sum(
        1
        for local in locaux
        if (
            local.contrat_actif is None
            and local.statut == "reserve"
        )
    )

    total_maintenance = sum(
        1
        for local in locaux
        if (
            local.contrat_actif is None
            and local.statut == "maintenance"
        )
    )

    # =====================================================
    # TAUX D'OCCUPATION
    # =====================================================
    if total_locaux > 0:
        taux_occupation = round(
            total_occupes * 100 / total_locaux
        )
    else:
        taux_occupation = 0

    # =====================================================
    # CONTRATS ACTIFS DU CENTRE
    # =====================================================
    contrats_actifs = (
        ContratCommercial.objects
        .select_related(
            "occupant",
            "local",
            "local__centre",
        )
        .filter(
            agence=agence,
            local__centre=centre,
            actif=True,
        )
        .order_by(
            "-date_debut",
        )
    )

    contexte = {
        "agence": agence,
        "centre": centre,
        "locaux": locaux,
        "contrats_actifs": contrats_actifs,

        "total_locaux": total_locaux,
        "total_libres": total_libres,
        "total_occupes": total_occupes,
        "total_reserves": total_reserves,
        "total_maintenance": total_maintenance,
        "taux_occupation": taux_occupation,
    }

    return render(
        request,
        "centre_commercial/detail_centre_commercial.html",
        contexte,
    )


# =========================================================
# DÉTAIL D'UN CONTRAT COMMERCIAL
# =========================================================
@login_required(login_url="login")
def detail_contrat_commercial(request, contrat_id):

    agence = get_agence(request.user)

    contrat = get_object_or_404(
        ContratCommercial.objects.select_related(
            "agence",
            "occupant",
            "local",
            "local__centre",
            "local__centre__proprietaire",
            "local__centre__batiment",
        ),
        id=contrat_id,
        agence=agence,
    )

    verification_url = request.build_absolute_uri(
        contrat.get_verification_url()
    )

    contexte = {
        "agence": agence,
        "contrat": contrat,
        "occupant": contrat.occupant,
        "local": contrat.local,
        "centre": contrat.local.centre,
        "verification_url": verification_url,
    }

    return render(
        request,
        "centre_commercial/detail_contrat.html",
        contexte,
    )
# =========================================================
# CLÔTURER LE CONTRAT ET LIBÉRER LE LOCAL
# =========================================================

@login_required(login_url="login")
def liberer_local_commercial(request, contrat_id):

    agence = get_agence(request.user)

    contrat = get_object_or_404(
        ContratCommercial.objects.select_related(
            "local",
            "local__centre",
        ),
        id=contrat_id,
        agence=agence,
        actif=True,
    )

    # =====================================================
    # INTERDIRE LA CLÔTURE PAR GET
    # =====================================================

    if request.method != "POST":

        messages.error(
            request,
            (
                "La clôture du contrat doit être "
                "confirmée par le formulaire."
            ),
        )

        return redirect(
            "detail_contrat_commercial",
            contrat_id=contrat.id,
        )

    # =====================================================
    # CLÔTURE
    # =====================================================

    with transaction.atomic():

        contrat_verrouille = get_object_or_404(
            ContratCommercial.objects
            .select_for_update()
            .select_related(
                "local"
            ),
            id=contrat.id,
            agence=agence,
            actif=True,
        )

        contrat_verrouille.actif = False

        if not contrat_verrouille.date_fin:

            contrat_verrouille.date_fin = (
                timezone.localdate()
            )

        contrat_verrouille.save()

        # =================================================
        # VÉRIFIER S'IL RESTE UN AUTRE CONTRAT ACTIF
        # =================================================

        autre_contrat_actif = (
            ContratCommercial.objects.filter(
                agence=agence,
                local=contrat_verrouille.local,
                actif=True,
            )
            .exclude(
                id=contrat_verrouille.id
            )
            .exists()
        )

        # =================================================
        # LIBÉRER LE LOCAL
        # =================================================

        if not autre_contrat_actif:

            LocalCommercial.objects.filter(
                id=contrat_verrouille.local_id
            ).update(
                statut="libre"
            )

    messages.success(
        request,
        (
            "Le contrat a été clôturé et "
            "le local est maintenant libre."
        ),
    )

    return redirect(
        "detail_centre_commercial",
        centre_id=contrat.local.centre_id,
    )


# =========================================================
# CONTRAT À IMPRIMER OU TÉLÉCHARGER EN PDF
# =========================================================

@login_required(login_url="login")
def contrat_commercial_pdf(request, contrat_id):

    """
    Cette vue n'utilise pas WeasyPrint.

    Elle affiche le contrat officiel dans le navigateur
    avec la photo et le code QR.

    L'utilisateur clique ensuite sur :
    « Imprimer ou télécharger en PDF »

    Puis sélectionne :
    « Enregistrer au format PDF ».
    """

    agence = get_agence(request.user)

    contrat = get_object_or_404(
        ContratCommercial.objects.select_related(
            "agence",

            "local",
            "local__centre",
            "local__centre__proprietaire",
            "local__centre__batiment",

            "occupant",
        ),
        id=contrat_id,
        agence=agence,
    )

    # =====================================================
    # ADRESSE PUBLIQUE DE VÉRIFICATION
    # =====================================================

    verification_url = request.build_absolute_uri(
        contrat.get_verification_url()
    )

    # =====================================================
    # GÉNÉRER LE QR CODE
    # =====================================================

    qr_image = qrcode.make(
        verification_url
    )

    flux = io.BytesIO()

    qr_image.save(
        flux,
        format="PNG"
    )

    qr_base64 = base64.b64encode(
        flux.getvalue()
    ).decode(
        "utf-8"
    )

    # =====================================================
    # AFFICHAGE HTML IMPRIMABLE
    # =====================================================

    return render(
        request,
        "centre_commercial/contrat_pdf.html",
        {
            "agence": agence,
            "contrat": contrat,

            "verification_url": verification_url,
            "qr_base64": qr_base64,

            "mode_impression": True,
        },
    )


# =========================================================
# VÉRIFICATION PUBLIQUE DU CONTRAT
# =========================================================

def verifier_contrat_commercial(
    request,
    code_verification
):

    contrat = get_object_or_404(
        ContratCommercial.objects.select_related(
            "agence",

            "local",
            "local__centre",
            "local__centre__proprietaire",

            "occupant",
        ),
        code_verification=code_verification,
        certifie_application=True,
    )

    return render(
        request,
        "centre_commercial/verifier_contrat.html",
        {
            "contrat": contrat,
            "document_valide": True,
        },
    )




@login_required(login_url="login")
def support(request):
    return render(
        request,
        "support.html",
    )




from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST


@login_required(login_url="login")
@require_POST
def supprimer_centre_commercial(request, centre_id):
    agence = get_agence(request.user)

    centre = get_object_or_404(
        CentreCommercial,
        id=centre_id,
        agence=agence
    )

    nom_centre = centre.nom

    # Bloquer la suppression si des locaux sont enregistrés.
    if centre.locaux.exists():
        messages.error(
            request,
            (
                f"Impossible de supprimer le centre « {nom_centre} » "
                "car il contient encore des locaux. "
                "Supprimez d’abord les locaux associés."
            )
        )

        return redirect("centres_commerciaux")

    centre.delete()

    messages.success(
        request,
        f"Le centre commercial « {nom_centre} » a été supprimé avec succès."
    )

    return redirect("centres_commerciaux")



@login_required(login_url="login")
@require_POST
def supprimer_local_commercial(request, local_id):
    agence = get_agence(request.user)

    local = get_object_or_404(
        LocalCommercial.objects.select_related("centre"),
        id=local_id,
        centre__agence=agence
    )

    centre_id = local.centre_id
    numero_local = local.numero

    contrat_actif = ContratCommercial.objects.filter(
        local=local,
        actif=True
    ).exists()

    if contrat_actif:
        messages.error(
            request,
            (
                f"Le local N° {numero_local} ne peut pas être supprimé "
                "car il possède encore un contrat actif. "
                "Vous devez d’abord terminer ou supprimer le contrat."
            )
        )

        return redirect(
            "detail_centre_commercial",
            centre_id
        )

    local.delete()

    messages.success(
        request,
        f"Le local N° {numero_local} a été supprimé avec succès."
    )

    return redirect(
        "detail_centre_commercial",
        centre_id
    )



from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST


@login_required(login_url="login")
@require_POST
@transaction.atomic
def supprimer_contrat_commercial(request, contrat_id):
    agence = get_agence(request.user)

    contrat = get_object_or_404(
        ContratCommercial.objects.select_related(
            "local",
            "local__centre"
        ),
        id=contrat_id,
        agence=agence
    )

    local = contrat.local
    centre_id = local.centre_id

    numero_contrat = (
        getattr(contrat, "numero_contrat", None)
        or getattr(contrat, "numero", None)
        or contrat.id
    )

    contrat.delete()

    # Le local redevient libre après la suppression du contrat.
    local.statut = "libre"
    local.save(update_fields=["statut"])

    messages.success(
        request,
        (
            f"Le contrat N° {numero_contrat} a été supprimé. "
            f"Le local N° {local.numero} est maintenant libre."
        )
    )

    return redirect(
        "detail_centre_commercial",
        centre_id
    )





import base64
import uuid

from django.core.files.base import ContentFile


def convertir_signature_base64(signature, prefixe):

    if not signature:
        return None

    if ";base64," not in signature:
        return None

    try:
        entete, contenu = signature.split(";base64,", 1)

        extension = entete.split("/")[-1].lower()

        if extension == "jpeg":
            extension = "jpg"

        contenu_decode = base64.b64decode(contenu)

        nom_fichier = (
            f"{prefixe}_{uuid.uuid4().hex}.{extension}"
        )

        return ContentFile(
            contenu_decode,
            name=nom_fichier
        )

    except (
        ValueError,
        TypeError,
        base64.binascii.Error
    ):
        return None





from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import Proprietaire, Batiment


@login_required(login_url="login")
def attestation_proprietaire(request, proprietaire_id):

    # Agence de l'utilisateur connecté
    agence = get_agence(request.user)

    # Le propriétaire doit appartenir à cette agence
    proprietaire = get_object_or_404(
        Proprietaire,
        id=proprietaire_id,
        agence=agence
    )

    # Tous les bâtiments associés à ce propriétaire
    batiments = Batiment.objects.filter(
        agence=agence,
        proprietaire=proprietaire
    ).order_by(
        "nom"
    )

    # Ne pas produire une attestation sans bâtiment
    if not batiments.exists():

        messages.warning(
            request,
            "Impossible de produire l’attestation : "
            "aucun bâtiment n’est associé à ce propriétaire."
        )

        return redirect(
            "detail_proprietaire",
            proprietaire_id=proprietaire.id
        )

    date_emission = timezone.localtime()

    reference_document = (
        f"ATT-PROP-"
        f"{agence.id:03d}-"
        f"{proprietaire.id:05d}-"
        f"{date_emission:%Y%m%d}"
    )

    signataire = (
        request.user.get_full_name()
        or request.user.username
    )

    contexte = {
        "agence": agence,
        "proprietaire": proprietaire,
        "batiments": batiments,
        "nombre_batiments": batiments.count(),
        "date_emission": date_emission,
        "reference_document": reference_document,
        "signataire": signataire,
    }

    return render(
        request,
        "attestation_proprietaire.html",
        contexte
    )






@login_required(login_url="login")
@require_POST
def generer_contrat_bail(request, location_id):
    agence = get_agence(request.user)

    location = get_object_or_404(
        Location.objects.select_related(
            "agence",
            "batiment",
            "batiment__proprietaire",
            "locataire",
            "unite",
        ),
        id=location_id,
        agence=agence,
        active=True,
    )

    if not location.unite_id:
        messages.error(
            request,
            "Cette location n’est associée à aucune unité locative.",
        )

        return redirect(
            "detail_batiment",
            id=location.batiment_id,
        )

    try:
        generer_contrat_bail_numerique(
            location,
            forcer=True,
        )

        location.refresh_from_db(
            fields=[
                "contrat_bail_numerique",
                "date_generation_contrat",
            ]
        )

        if location.contrat_bail_numerique:
            messages.success(
                request,
                (
                    f"Le contrat de bail {location.numero_contrat} "
                    "a été généré avec succès."
                ),
            )
        else:
            messages.error(
                request,
                "Le contrat n’a pas pu être enregistré.",
            )

    except Exception as erreur:
        messages.error(
            request,
            (
                "Impossible de générer le contrat de bail : "
                f"{erreur}"
            ),
        )

    return redirect(
        "detail_batiment",
        id=location.batiment_id,
    )








from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Location, UniteLocative


@login_required(login_url="login")
@require_POST
def liberer_unite_locataire(request, location_id):
    agence = get_agence(request.user)

    location = get_object_or_404(
        Location.objects.select_related(
            "batiment",
            "locataire",
            "unite",
        ),
        id=location_id,
        agence=agence,
        active=True,
        unite__isnull=False,
    )

    batiment_id = location.batiment_id
    numero_unite = location.unite.numero

    nom_locataire = (
        f"{location.locataire.nom} "
        f"{location.locataire.prenom}"
    ).strip()

    try:
        with transaction.atomic():
            location_verrouillee = (
                Location.objects
                .select_for_update()
                .get(
                    id=location.id,
                    agence=agence,
                    active=True,
                )
            )

            unite_verrouillee = (
                UniteLocative.objects
                .select_for_update()
                .get(
                    id=location_verrouillee.unite_id,
                    batiment__agence=agence,
                )
            )

            Location.objects.filter(
                pk=location_verrouillee.pk,
            ).update(
                active=False,
                date_fin=timezone.localdate(),
                date_modification=timezone.now(),
            )

            UniteLocative.objects.filter(
                pk=unite_verrouillee.pk,
            ).update(
                statut=UniteLocative.Statut.LIBRE,
            )

        messages.success(
            request,
            (
                f"{nom_locataire} a été retiré de l’unité "
                f"n° {numero_unite}. L’unité est maintenant disponible."
            ),
        )

    except Exception as erreur:
        messages.error(
            request,
            f"Impossible de libérer l’unité : {erreur}",
        )

    return redirect(
        "detail_batiment",
        id=batiment_id,
    )


