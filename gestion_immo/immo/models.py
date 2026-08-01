from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone






class Agence(models.Model):
    nom = models.CharField(max_length=150)

    proprietaire = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="agence"
    )

    def __str__(self):
        return self.nom


class Proprietaire(models.Model):
    agence = models.ForeignKey(
        Agence,
        on_delete=models.CASCADE,
        related_name="proprietaires_immobiliers"
    )

    code_client = models.CharField(max_length=30, unique=True)

    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    telephone = models.CharField(max_length=30)

    email = models.EmailField(blank=True, null=True)
    adresse = models.CharField(max_length=255)
    resident = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nom} {self.prenom}"

from django.db import models





class Batiment(models.Model):
    agence = models.ForeignKey(
        "Agence",
        on_delete=models.CASCADE,
        related_name="batiments",
    )

    proprietaire = models.ForeignKey(
        "Proprietaire",
        on_delete=models.CASCADE,
        related_name="batiments",
    )

    code_batiment = models.CharField(
        max_length=30,
        unique=True,
    )

    nom = models.CharField(
        max_length=150,
    )

    adresse = models.CharField(
        max_length=255,
    )

    ville = models.CharField(
        max_length=100,
    )

    # Ce champ sera calculé automatiquement.
    # Il contient seulement les appartements et les studios.
    # Les magasins ne sont pas comptés comme logements d’habitation.
    nombre_logements = models.PositiveIntegerField(
        default=0,
        editable=False,
    )

    description = models.TextField(
        blank=True,
        null=True,
    )

    actif = models.BooleanField(
        default=True,
    )

    date_creation = models.DateTimeField(
        auto_now_add=True,
    )

    # ---------------------------------------------------------
    # UNITÉS DU BÂTIMENT
    # ---------------------------------------------------------

    def unites_actives(self):
        """
        Retourne toutes les unités actives :
        appartements, studios et magasins.
        """
        return self.unites_locatives.filter(actif=True)

    def unites_total(self):
        """
        Nombre total d’unités dans le bâtiment.
        """
        return self.unites_actives().count()

    def logements_habitation(self):
        """
        Retourne seulement les appartements et les studios.
        """
        return self.unites_actives().filter(
            type_unite__in=[
                UniteLocative.TypeUnite.APPARTEMENT,
                UniteLocative.TypeUnite.STUDIO,
            ]
        )

    def logements_total(self):
        """
        Nombre d’appartements et de studios.
        """
        return self.logements_habitation().count()

    def appartements_total(self):
        return self.unites_actives().filter(
            type_unite=UniteLocative.TypeUnite.APPARTEMENT
        ).count()

    def studios_total(self):
        return self.unites_actives().filter(
            type_unite=UniteLocative.TypeUnite.STUDIO
        ).count()

    def magasins_total(self):
        return self.unites_actives().filter(
            type_unite=UniteLocative.TypeUnite.MAGASIN
        ).count()

    # ---------------------------------------------------------
    # NOMBRE DE CHAMBRES
    # ---------------------------------------------------------

    def chambres_total(self):
        """
        Calcule le nombre total de chambres présentes
        dans tous les appartements.

        Les studios et les magasins ne sont pas comptés
        comme des chambres.
        """
        resultat = self.unites_actives().filter(
            type_unite=UniteLocative.TypeUnite.APPARTEMENT
        ).aggregate(
            total=Sum("nombre_chambres")
        )

        return resultat["total"] or 0

    def chambres_occupees(self):
        """
        Calcule le nombre total de chambres contenues
        dans les appartements actuellement occupés.
        """
        resultat = self.unites_actives().filter(
            type_unite=UniteLocative.TypeUnite.APPARTEMENT,
            statut=UniteLocative.Statut.OCCUPE,
        ).aggregate(
            total=Sum("nombre_chambres")
        )

        return resultat["total"] or 0

    # ---------------------------------------------------------
    # OCCUPATION DES UNITÉS
    # ---------------------------------------------------------

    def unites_occupees(self):
        return self.unites_actives().filter(
            statut=UniteLocative.Statut.OCCUPE
        ).count()

    def unites_libres(self):
        return self.unites_actives().filter(
            statut=UniteLocative.Statut.LIBRE
        ).count()

    def unites_reservees(self):
        return self.unites_actives().filter(
            statut=UniteLocative.Statut.RESERVE
        ).count()

    def unites_en_maintenance(self):
        return self.unites_actives().filter(
            statut=UniteLocative.Statut.MAINTENANCE
        ).count()

    def est_totalement_occupe(self):
        total = self.unites_total()

        return (
            total > 0
            and self.unites_occupees() == total
        )

    def est_partiellement_occupe(self):
        total = self.unites_total()
        occupees = self.unites_occupees()

        return (
            total > 0
            and 0 < occupees < total
        )

    def est_libre(self):
        return (
            self.unites_total() > 0
            and self.unites_occupees() == 0
        )

    def statut_occupation(self):
        if self.unites_total() == 0:
            return "Aucune unité"

        if self.est_totalement_occupe():
            return "Tout occupé"

        if self.est_partiellement_occupe():
            return "Partiellement occupé"

        return "Libre"

    def locataires_actifs(self):
        """
        Cette méthode reste compatible avec votre système actuel
        si Location contient toujours une relation vers Batiment.
        """
        return Locataire.objects.filter(
            locations__batiment=self,
            locations__active=True,
        ).distinct()

    def __str__(self):
        return f"{self.code_batiment} - {self.nom}"


class UniteLocative(models.Model):

    class TypeUnite(models.TextChoices):
        APPARTEMENT = "APPARTEMENT", "Appartement"
        STUDIO = "STUDIO", "Studio"
        MAGASIN = "MAGASIN", "Magasin / local commercial"

    class TypeToilette(models.TextChoices):
        COMMUNE_APPARTEMENT = (
            "COMMUNE_APPARTEMENT",
            "Toilette commune dans l’appartement",
        )

        UNE_PAR_CHAMBRE = (
            "UNE_PAR_CHAMBRE",
            "Une toilette dans chaque chambre",
        )

        PRIVEE_STUDIO = (
            "PRIVEE_STUDIO",
            "Toilette privée dans le studio",
        )

        PRIVEE_MAGASIN = (
            "PRIVEE_MAGASIN",
            "Toilette privée dans le magasin",
        )

        COMMUNE_BATIMENT = (
            "COMMUNE_BATIMENT",
            "Toilette commune au bâtiment",
        )

        AUCUNE = (
            "AUCUNE",
            "Aucune toilette",
        )

    class UsageCommercial(models.TextChoices):
        BOUTIQUE = "BOUTIQUE", "Boutique"
        SALON_COIFFURE = "SALON_COIFFURE", "Salon de coiffure"
        BUREAU = "BUREAU", "Bureau"
        RESTAURANT = "RESTAURANT", "Restaurant"
        ATELIER = "ATELIER", "Atelier"
        PHARMACIE = "PHARMACIE", "Pharmacie"
        ENTREPOT = "ENTREPOT", "Entrepôt"
        AUTRE = "AUTRE", "Autre activité"

    class Statut(models.TextChoices):
        LIBRE = "LIBRE", "Libre"
        OCCUPE = "OCCUPE", "Occupé"
        RESERVE = "RESERVE", "Réservé"
        MAINTENANCE = "MAINTENANCE", "En maintenance"

    batiment = models.ForeignKey(
        Batiment,
        on_delete=models.CASCADE,
        related_name="unites_locatives",
    )

    numero = models.CharField(
        max_length=100,
        verbose_name="Nom ou numéro de l’unité",
        help_text=(
            "Exemple : Appartement 1, Studio 1 ou Magasin 1."
        ),
    )

    type_unite = models.CharField(
        max_length=20,
        choices=TypeUnite.choices,
        default=TypeUnite.APPARTEMENT,
    )

    nombre_chambres = models.PositiveIntegerField(
        default=0,
        help_text=(
            "À renseigner uniquement pour les appartements."
        ),
    )

    type_toilette = models.CharField(
        max_length=30,
        choices=TypeToilette.choices,
        default=TypeToilette.COMMUNE_APPARTEMENT,
    )

    prix_mensuel = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        verbose_name="Loyer mensuel en FCFA",
    )

    usage_commercial = models.CharField(
        max_length=30,
        choices=UsageCommercial.choices,
        blank=True,
        default="",
        help_text=(
            "À renseigner uniquement pour un magasin."
        ),
    )

    statut = models.CharField(
        max_length=20,
        choices=Statut.choices,
        default=Statut.LIBRE,
    )

    description = models.TextField(
        blank=True,
        null=True,
    )

    actif = models.BooleanField(
        default=True,
    )

    date_creation = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "batiment",
            "type_unite",
            "numero",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "batiment",
                    "numero",
                ],
                name="numero_unite_unique_par_batiment",
            )
        ]

        verbose_name = "Unité locative"
        verbose_name_plural = "Unités locatives"

    def clean(self):
        erreurs = {}

        if self.prix_mensuel is not None and self.prix_mensuel < 0:
            erreurs["prix_mensuel"] = (
                "Le prix mensuel ne peut pas être négatif."
            )

        # Appartement
        if self.type_unite == self.TypeUnite.APPARTEMENT:
            if self.nombre_chambres < 1:
                erreurs["nombre_chambres"] = (
                    "Un appartement doit avoir au moins une chambre."
                )

            toilettes_autorisees = [
                self.TypeToilette.COMMUNE_APPARTEMENT,
                self.TypeToilette.UNE_PAR_CHAMBRE,
                self.TypeToilette.COMMUNE_BATIMENT,
                self.TypeToilette.AUCUNE,
            ]

            if self.type_toilette not in toilettes_autorisees:
                erreurs["type_toilette"] = (
                    "Ce type de toilette ne convient pas "
                    "à un appartement."
                )

            self.usage_commercial = ""

        # Studio
        elif self.type_unite == self.TypeUnite.STUDIO:
            self.nombre_chambres = 0
            self.usage_commercial = ""

            toilettes_autorisees = [
                self.TypeToilette.PRIVEE_STUDIO,
                self.TypeToilette.COMMUNE_BATIMENT,
                self.TypeToilette.AUCUNE,
            ]

            if self.type_toilette not in toilettes_autorisees:
                erreurs["type_toilette"] = (
                    "Un studio peut avoir une toilette privée, "
                    "une toilette commune au bâtiment ou aucune toilette."
                )

        # Magasin
        elif self.type_unite == self.TypeUnite.MAGASIN:
            self.nombre_chambres = 0

            if not self.usage_commercial:
                erreurs["usage_commercial"] = (
                    "Indiquez l’utilisation du magasin : boutique, "
                    "salon de coiffure, bureau, etc."
                )

            toilettes_autorisees = [
                self.TypeToilette.PRIVEE_MAGASIN,
                self.TypeToilette.COMMUNE_BATIMENT,
                self.TypeToilette.AUCUNE,
            ]

            if self.type_toilette not in toilettes_autorisees:
                erreurs["type_toilette"] = (
                    "Ce type de toilette ne convient pas "
                    "à un magasin."
                )

        if erreurs:
            raise ValidationError(erreurs)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def est_habitation(self):
        return self.type_unite in [
            self.TypeUnite.APPARTEMENT,
            self.TypeUnite.STUDIO,
        ]

    def est_commercial(self):
        return self.type_unite == self.TypeUnite.MAGASIN

    def __str__(self):
        return (
            f"{self.numero} - "
            f"{self.get_type_unite_display()} - "
            f"{self.batiment.nom}"
        )


@receiver([post_save, post_delete], sender=UniteLocative)
def synchroniser_nombre_logements(sender, instance, **kwargs):
    """
    Met automatiquement à jour nombre_logements dans Batiment.

    Seuls les appartements et les studios sont comptés.
    Les magasins ne sont pas des logements d’habitation.
    """
    nombre = UniteLocative.objects.filter(
        batiment_id=instance.batiment_id,
        actif=True,
        type_unite__in=[
            UniteLocative.TypeUnite.APPARTEMENT,
            UniteLocative.TypeUnite.STUDIO,
        ],
    ).count()

    Batiment.objects.filter(
        pk=instance.batiment_id
    ).update(
        nombre_logements=nombre
    )



class ChambreLogement(models.Model):
    batiment = models.ForeignKey(
        Batiment,
        on_delete=models.CASCADE,
        related_name="chambres"
    )

    numero = models.CharField(max_length=30)
    nom = models.CharField(max_length=100, blank=True, null=True)

    actif = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("batiment", "numero")

    def bail_actif(self):
        return self.locations.filter(active=True).first()

    def est_occupee(self):
        return self.bail_actif() is not None

    def locataire_actif(self):
        bail = self.bail_actif()
        return bail.locataire if bail else None

    def __str__(self):
        return f"{self.batiment.nom} - Chambre {self.numero}"
    



class Locataire(models.Model):
    agence = models.ForeignKey(
        Agence,
        on_delete=models.CASCADE,
        related_name="locataires"
    )

    nom = models.CharField(max_length=150)
    prenom = models.CharField(max_length=150, blank=True, null=True)
    telephone = models.CharField(max_length=30)

    email = models.EmailField(blank=True, null=True)

    date_naissance = models.DateField(blank=True, null=True)
    lieu_naissance = models.CharField(max_length=255, blank=True, null=True)

    sexe = models.CharField(
        max_length=20,
        choices=[
            ("Homme", "Homme"),
            ("Femme", "Femme"),
        ],
        blank=True,
        null=True
    )

    profession = models.CharField(max_length=255, blank=True, null=True)
    employeur = models.CharField(max_length=255, blank=True, null=True)

    revenu_mensuel = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )

    adresse_actuelle = models.TextField(blank=True, null=True)
    ville = models.CharField(max_length=150, blank=True, null=True)
    pays = models.CharField(max_length=150, blank=True, null=True)

    contact_urgence_nom = models.CharField(max_length=150, blank=True, null=True)
    contact_urgence_telephone = models.CharField(max_length=30, blank=True, null=True)
    contact_urgence_lien = models.CharField(max_length=100, blank=True, null=True)

    piece_identite = models.FileField(
        upload_to="locataires/pieces_identite/",
        blank=True,
        null=True
    )

    acte_naissance = models.FileField(
        upload_to="locataires/actes_naissance/",
        blank=True,
        null=True
    )

    photo = models.ImageField(
        upload_to="locataires/photos/",
        blank=True,
        null=True
    )

    numero_piece_identite = models.CharField(max_length=100, blank=True, null=True)
    date_expiration_piece = models.DateField(blank=True, null=True)

    # CAUTION
    caution = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    caution_payee = models.BooleanField(
        default=False
    )

    date_caution = models.DateField(
        null=True,
        blank=True
    )

    observation_caution = models.TextField(
        blank=True,
        null=True
    )

    date_debut = models.DateField(
        null=True,
        blank=True
    )

   

    date_creation = models.DateTimeField(auto_now_add=True)

    actif = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.prenom or ''} {self.nom}".strip()
    



class Employe(models.Model):
    TYPE_CHOICES = [
        ("agent", "Agent Immobilier"),
        ("secretaire", "Secrétaire"),
    ]

    agence = models.ForeignKey(
        Agence,
        on_delete=models.CASCADE,
        related_name="employes"
    )

    utilisateur = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    type_employe = models.CharField(max_length=20, choices=TYPE_CHOICES)

    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    telephone = models.CharField(max_length=30)

    adresse = models.CharField(max_length=255)
    ville = models.CharField(max_length=100)

    numero_poste = models.CharField(max_length=50, blank=True, null=True)

    salaire = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    nationalite = models.CharField(max_length=100)

    acte_naissance = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nom} {self.prenom}"



from pathlib import Path

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.text import get_valid_filename


def chemin_contrat_bail(instance, filename):
    """
    Classe automatiquement les contrats de bail par agence,
    bâtiment et location.

    Exemple :
    media/contrats_bail/agence_1/batiment_3/
    location_12_contrat-bail.pdf
    """

    fichier = Path(filename)

    nom_fichier = get_valid_filename(
        fichier.stem
    ) or "contrat-bail"

    extension = fichier.suffix.lower() or ".pdf"

    agence_id = (
        instance.agence_id
        if instance.agence_id
        else "sans_agence"
    )

    batiment_id = (
        instance.batiment_id
        if instance.batiment_id
        else "sans_batiment"
    )

    location_id = (
        instance.pk
        if instance.pk
        else "nouvelle"
    )

    return (
        f"contrats_bail/"
        f"agence_{agence_id}/"
        f"batiment_{batiment_id}/"
        f"location_{location_id}_{nom_fichier}{extension}"
    )


class Location(models.Model):
    agence = models.ForeignKey(
        Agence,
        on_delete=models.CASCADE,
        related_name="locations",
        verbose_name="Agence",
    )

    batiment = models.ForeignKey(
        Batiment,
        on_delete=models.CASCADE,
        related_name="locations",
        verbose_name="Bâtiment",
    )

    locataire = models.ForeignKey(
        Locataire,
        on_delete=models.CASCADE,
        related_name="locations",
        verbose_name="Locataire",
    )

    # Nouveau système :
    # appartement, studio ou magasin complet.
    unite = models.ForeignKey(
        "UniteLocative",
        on_delete=models.SET_NULL,
        related_name="locations",
        null=True,
        blank=True,
        verbose_name="Appartement, studio ou magasin",
        help_text=(
            "Sélectionnez l’unité complète attribuée "
            "au locataire."
        ),
    )

    # Ancien système conservé temporairement afin de ne pas
    # perdre les anciennes locations déjà enregistrées.
    chambre = models.ForeignKey(
        ChambreLogement,
        on_delete=models.SET_NULL,
        related_name="locations",
        null=True,
        blank=True,
        verbose_name="Ancien logement ou chambre",
        help_text=(
            "Ancien champ conservé temporairement pour "
            "les locations déjà enregistrées."
        ),
    )

    numero_appartement = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="Numéro de l’appartement ou de l’unité",
        help_text=(
            "Ce champ est automatiquement rempli lorsqu’une "
            "unité locative est sélectionnée."
        ),
    )

    # Null et blank permettent d’utiliser automatiquement
    # le prix défini dans UniteLocative.
    loyer = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Loyer mensuel",
        help_text=(
            "Montant mensuel en FCFA. Laissez vide pour "
            "utiliser automatiquement le prix de l’unité."
        ),
    )

    caution = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Montant de la caution",
        help_text="Montant de la caution en FCFA.",
    )

    caution_payee = models.BooleanField(
        default=False,
        verbose_name="Caution payée",
    )

    date_caution = models.DateField(
        null=True,
        blank=True,
        verbose_name="Date de paiement de la caution",
    )

    observation_caution = models.TextField(
        blank=True,
        null=True,
        verbose_name="Observation sur la caution",
    )

    date_debut = models.DateField(
        verbose_name="Date de début du bail",
    )

    date_fin = models.DateField(
        null=True,
        blank=True,
        verbose_name="Date de fin du bail",
        help_text=(
            "Laissez vide si le contrat est à durée "
            "indéterminée."
        ),
    )

    active = models.BooleanField(
        default=True,
        verbose_name="Bail actif",
    )

    # Contrat PDF créé automatiquement après l’affectation
    # d’un locataire à une unité.
    contrat_bail_numerique = models.FileField(
        upload_to=chemin_contrat_bail,
        null=True,
        blank=True,
        verbose_name="Contrat de bail numérique",
    )

    date_generation_contrat = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date de génération du contrat",
    )

    # Ne pas utiliser auto_now_add=True pour ce nouveau champ,
    # car la table contient déjà des locations.
    # timezone.now fournit une date valide aux anciennes lignes.
    date_creation = models.DateTimeField(
        default=timezone.now,
        editable=False,
        verbose_name="Date de création",
    )

    # null=True évite une erreur lors de l’ajout du champ
    # aux anciennes locations.
    date_modification = models.DateTimeField(
        auto_now=True,
        null=True,
        blank=True,
        verbose_name="Dernière modification",
    )

    class Meta:
        ordering = (
            "-active",
            "-date_debut",
            "-id",
        )

        verbose_name = "Location"
        verbose_name_plural = "Locations"

        indexes = [
            models.Index(
                fields=[
                    "agence",
                    "active",
                ],
                name="location_agence_active_idx",
            ),
            models.Index(
                fields=[
                    "batiment",
                    "active",
                ],
                name="location_bat_active_idx",
            ),
            models.Index(
                fields=[
                    "unite",
                    "active",
                ],
                name="location_unite_active_idx",
            ),
        ]

    def clean(self):
        """
        Vérifie la cohérence de la location avant
        son enregistrement.
        """

        erreurs = {}

        # Une unité ou une ancienne chambre doit être indiquée.
        if not self.unite_id and not self.chambre_id:
            erreurs["unite"] = (
                "Sélectionnez un appartement, un studio "
                "ou un magasin."
            )

        # Vérifier que l’unité appartient au bâtiment.
        if (
            self.unite_id
            and self.batiment_id
            and self.unite.batiment_id != self.batiment_id
        ):
            erreurs["unite"] = (
                "L’unité sélectionnée n’appartient pas "
                "à ce bâtiment."
            )

        # Vérifier que l’ancienne chambre appartient
        # également au bâtiment.
        if (
            self.chambre_id
            and self.batiment_id
            and self.chambre.batiment_id != self.batiment_id
        ):
            erreurs["chambre"] = (
                "L’ancien logement sélectionné n’appartient "
                "pas à ce bâtiment."
            )

        # Vérifier que le bâtiment appartient à l’agence.
        if (
            self.batiment_id
            and self.agence_id
            and self.batiment.agence_id != self.agence_id
        ):
            erreurs["batiment"] = (
                "Le bâtiment sélectionné n’appartient pas "
                "à cette agence."
            )

        # Vérifier le locataire si son modèle possède agence_id.
        if (
            self.locataire_id
            and self.agence_id
            and hasattr(self.locataire, "agence_id")
            and self.locataire.agence_id
            and self.locataire.agence_id != self.agence_id
        ):
            erreurs["locataire"] = (
                "Le locataire sélectionné n’appartient pas "
                "à cette agence."
            )

        if self.loyer is not None and self.loyer < 0:
            erreurs["loyer"] = (
                "Le montant du loyer ne peut pas être négatif."
            )

        if self.caution is not None and self.caution < 0:
            erreurs["caution"] = (
                "Le montant de la caution ne peut pas "
                "être négatif."
            )

        if (
            self.date_fin
            and self.date_debut
            and self.date_fin < self.date_debut
        ):
            erreurs["date_fin"] = (
                "La date de fin ne peut pas être antérieure "
                "à la date de début."
            )

        if self.caution_payee and not self.date_caution:
            erreurs["date_caution"] = (
                "Indiquez la date de paiement de la caution."
            )

        # Empêcher deux baux actifs sur la même unité.
        if self.active and self.unite_id:
            locations_actives = Location.objects.filter(
                unite_id=self.unite_id,
                active=True,
            )

            if self.pk:
                locations_actives = locations_actives.exclude(
                    pk=self.pk
                )

            if locations_actives.exists():
                erreurs["unite"] = (
                    "Cette unité possède déjà un bail actif. "
                    "Terminez l’ancien bail avant d’en créer "
                    "un nouveau."
                )

        # Vérification pour les anciennes chambres.
        if self.active and self.chambre_id and not self.unite_id:
            anciennes_locations_actives = (
                Location.objects.filter(
                    chambre_id=self.chambre_id,
                    active=True,
                )
            )

            if self.pk:
                anciennes_locations_actives = (
                    anciennes_locations_actives.exclude(
                        pk=self.pk
                    )
                )

            if anciennes_locations_actives.exists():
                erreurs["chambre"] = (
                    "Cet ancien logement possède déjà "
                    "un bail actif."
                )

        if erreurs:
            raise ValidationError(erreurs)

    def save(self, *args, **kwargs):
        """
        Enregistre la location et met automatiquement
        à jour le statut de l’unité.
        """

        ancienne_unite_id = None

        if self.pk:
            ancienne_location = (
                Location.objects.filter(
                    pk=self.pk
                )
                .values(
                    "unite_id",
                    "active",
                )
                .first()
            )

            if ancienne_location:
                ancienne_unite_id = (
                    ancienne_location["unite_id"]
                )

        # Nouveau système.
        if self.unite_id:
            self.numero_appartement = self.unite.numero

            if self.loyer is None:
                self.loyer = self.unite.prix_mensuel

        # Ancien système.
        elif self.chambre_id and not self.numero_appartement:
            self.numero_appartement = (
                self.chambre.numero
                or self.chambre.nom
                or ""
            )

        # Applique les validations avant la sauvegarde.
        self.full_clean()

        super().save(*args, **kwargs)

        # Mettre la nouvelle unité au statut occupé.
        if self.unite_id and self.active:
            UniteLocative.objects.filter(
                pk=self.unite_id
            ).update(
                statut=UniteLocative.Statut.OCCUPE
            )

        # Libérer l’unité lorsqu’un bail devient inactif.
        if self.unite_id and not self.active:
            autre_bail_actif = Location.objects.filter(
                unite_id=self.unite_id,
                active=True,
            ).exclude(
                pk=self.pk
            ).exists()

            if not autre_bail_actif:
                UniteLocative.objects.filter(
                    pk=self.unite_id,
                    statut=UniteLocative.Statut.OCCUPE,
                ).update(
                    statut=UniteLocative.Statut.LIBRE
                )

        # Si l’unité a été remplacée, libérer l’ancienne unité.
        if (
            ancienne_unite_id
            and ancienne_unite_id != self.unite_id
        ):
            ancien_bail_actif = Location.objects.filter(
                unite_id=ancienne_unite_id,
                active=True,
            ).exists()

            if not ancien_bail_actif:
                UniteLocative.objects.filter(
                    pk=ancienne_unite_id,
                    statut=UniteLocative.Statut.OCCUPE,
                ).update(
                    statut=UniteLocative.Statut.LIBRE
                )

    def delete(self, *args, **kwargs):
        """
        Libère automatiquement l’unité lorsque la location
        est supprimée.
        """

        unite_id = self.unite_id

        resultat = super().delete(*args, **kwargs)

        if unite_id:
            autre_bail_actif = Location.objects.filter(
                unite_id=unite_id,
                active=True,
            ).exists()

            if not autre_bail_actif:
                UniteLocative.objects.filter(
                    pk=unite_id,
                    statut=UniteLocative.Statut.OCCUPE,
                ).update(
                    statut=UniteLocative.Statut.LIBRE
                )

        return resultat

    @property
    def numero_contrat(self):
        if not self.pk:
            return "BAIL-NOUVEAU"

        return f"BAIL-{self.pk:06d}"

    @property
    def contrat_disponible(self):
        return bool(
            self.contrat_bail_numerique
        )

    @property
    def unite_affichee(self):
        """
        Retourne la nouvelle unité ou l’ancien logement.
        """

        if self.unite_id:
            return self.unite

        if self.chambre_id:
            return self.chambre

        return None

    @property
    def montant_mensuel(self):
        if self.loyer is not None:
            return self.loyer

        if self.unite_id:
            return self.unite.prix_mensuel

        return 0

    @property
    def est_nouveau_systeme(self):
        return bool(self.unite_id)

    @property
    def est_ancien_systeme(self):
        return bool(
            self.chambre_id
            and not self.unite_id
        )

    def __str__(self):
        if self.unite_id:
            nom_unite = self.unite.numero

        elif self.chambre_id:
            nom_unite = (
                self.chambre.nom
                or self.chambre.numero
                or "Ancien logement"
            )

        else:
            nom_unite = (
                self.numero_appartement
                or "Unité non indiquée"
            )

        return (
            f"{self.locataire.nom} - "
            f"{nom_unite} - "
            f"{self.batiment.nom}"
        )
    
class Paiement(models.Model):
    STATUT_CHOICES = [
        ("paye", "Payé"),
        ("attente", "En attente"),
        ("retard", "En retard"),
    ]

    MODE_CHOICES = [
        ("espece", "Espèces"),
        ("virement", "Virement bancaire"),
        ("cheque", "Chèque"),
        ("orange_money", "Orange Money"),
        ("moov_money", "Moov Money"),
        ("wave", "Wave"),
        ("carte", "Carte bancaire"),
    ]

    numero_recu = models.CharField(max_length=50, unique=True)

    agence = models.ForeignKey(
        Agence,
        on_delete=models.CASCADE,
        related_name="paiements"
    )

    proprietaire = models.ForeignKey(
        Proprietaire,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="paiements_recus"
    )

    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name="paiements"
    )

    employe = models.ForeignKey(
        Employe,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="paiements_enregistres"
    )

    montant = models.DecimalField(max_digits=10, decimal_places=2)

    pourcentage_agence = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=10
    )

    commission_agence = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    montant_proprietaire = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    mois = models.CharField(
        max_length=30,
        help_text="Exemple : Juin 2026"
    )

    mode_paiement = models.CharField(
        max_length=30,
        choices=MODE_CHOICES,
        default="espece"
    )

    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default="attente"
    )

    date_echeance = models.DateField(null=True, blank=True)
    date_paiement = models.DateField(auto_now_add=True)

    
    signature_employe = models.ImageField(
        upload_to="paiements/signatures/employes/",
        null=True,
        blank=True
    )

    signature_locataire = models.ImageField(
        upload_to="paiements/signatures/locataires/",
        null=True,
        blank=True
    )

    email_recu = models.EmailField(
        blank=True
    )

    recu_envoye_email = models.BooleanField(
        default=False
    )

    commentaire = models.TextField(blank=True, null=True)

    justificatif = models.FileField(
        upload_to="paiements/",
        blank=True,
        null=True
    )

    employe = models.ForeignKey(
    Employe,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="paiements_enregistres"
    )

    class Meta:
        ordering = ["-date_paiement"]
        verbose_name = "Paiement"
        verbose_name_plural = "Paiements"

    def save(self, *args, **kwargs):
        if self.location and self.location.batiment:
            self.proprietaire = self.location.batiment.proprietaire

        self.commission_agence = (
            self.montant * self.pourcentage_agence
        ) / 100

        self.montant_proprietaire = (
            self.montant - self.commission_agence
        )

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.numero_recu} - {self.location.locataire.nom} - {self.montant}$"
    



from decimal import Decimal
from django.db import models


class RapportMensuelProprietaire(models.Model):

    agence = models.ForeignKey(
        Agence,
        on_delete=models.CASCADE,
        related_name="rapports_mensuels"
    )

    proprietaire = models.ForeignKey(
        Proprietaire,
        on_delete=models.CASCADE,
        related_name="rapports_mensuels"
    )

    mois = models.CharField(
        max_length=30
    )

    # =========================
    # LOYERS
    # =========================

    total_loyers = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )

    # =========================
    # PART AGENCE 10 %
    # =========================

    part_agence = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )

    # =========================
    # PART PROPRIÉTAIRE
    # AVANT DÉPENSES
    # =========================

    part_proprietaire = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )

    # =========================
    # DÉPENSES PROPRIÉTAIRE
    # =========================

    depenses_proprietaire = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )

    # =========================
    # DÉPENSES AGENCE
    # =========================

    depenses_agence = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )

    # =========================
    # NET PROPRIÉTAIRE
    # =========================

    net_proprietaire = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )

    # =========================
    # NET AGENCE
    # =========================

    net_agence = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )

    # =========================
    # DATES
    # =========================

    date_creation = models.DateTimeField(
        auto_now_add=True
    )

    date_modification = models.DateTimeField(
        auto_now=True
    )

    # =========================
    # CALCUL AUTOMATIQUE
    # =========================

    def calculer(self):

        total_loyers = (
            self.total_loyers
            or Decimal("0.00")
        )

        depenses_proprietaire = (
            self.depenses_proprietaire
            or Decimal("0.00")
        )

        depenses_agence = (
            self.depenses_agence
            or Decimal("0.00")
        )

        # Commission agence = 10 %
        self.part_agence = (
            total_loyers
            * Decimal("10.00")
            / Decimal("100.00")
        )

        # Part propriétaire après commission agence
        self.part_proprietaire = (
            total_loyers
            - self.part_agence
        )

        # Net propriétaire après ses dépenses
        self.net_proprietaire = (
            self.part_proprietaire
            - depenses_proprietaire
        )

        # Net agence après dépenses agence
        self.net_agence = (
            self.part_agence
            - depenses_agence
        )

    # =========================
    # SAUVEGARDE
    # =========================

    def save(self, *args, **kwargs):
        self.calculer()
        super().save(*args, **kwargs)

    # =========================
    # AFFICHAGE
    # =========================

    def __str__(self):
        return f"{self.proprietaire} - {self.mois}"

    class Meta:
        ordering = [
            "-date_creation"
        ]

        verbose_name = (
            "Rapport mensuel propriétaire"
        )

        verbose_name_plural = (
            "Rapports mensuels propriétaires"
        )


class Construction(models.Model):
    agence = models.ForeignKey(
        Agence,
        on_delete=models.CASCADE,
        related_name="constructions"
    )

    nom = models.CharField(max_length=150)
    batiment = models.ForeignKey(
        Batiment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="constructions"
    )

    budget_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    description = models.TextField(blank=True, null=True)
    date_debut = models.DateField(blank=True, null=True)
    date_fin_prevue = models.DateField(blank=True, null=True)

    actif = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    def total_depense(self):
        return sum(etape.montant_depense for etape in self.etapes.all())

    def reste_budget(self):
        return self.budget_total - self.total_depense()

    def __str__(self):
        return self.nom


class EtatConstruction(models.Model):
    STATUT_CHOICES = [
        ("attente", "En attente"),
        ("cours", "En cours"),
        ("termine", "Terminé"),
        ("bloque", "Bloqué"),
    ]

    construction = models.ForeignKey(
        Construction,
        on_delete=models.CASCADE,
        related_name="etapes"
    )

    nom = models.CharField(max_length=150)
    description = models.TextField(blank=True, null=True)

    budget_prevu = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    montant_depense = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default="attente"
    )

    date_debut = models.DateField(blank=True, null=True)
    date_fin = models.DateField(blank=True, null=True)

    def reste(self):
        return self.budget_prevu - self.montant_depense

    def __str__(self):
        return self.nom
    



class Terrain(models.Model):
    TYPE_OPERATION = [
        ("vente", "Vente"),
        ("achat", "Achat"),
    ]

    STATUT_TERRAIN = [
        ("libre", "Libre"),
        ("construction", "En construction"),
        ("vendu", "Vendu"),
        ("reserve", "Réservé"),
    ]

    QUALITE_TERRAIN = [
        ("20/20", "20/20 - Excellent"),
        ("18/20", "18/20 - Très bon"),
        ("15/20", "15/20 - Bon"),
        ("12/20", "12/20 - Moyen"),
        ("10/20", "10/20 - À vérifier"),
    ]

    agence = models.ForeignKey(
        Agence,
        on_delete=models.CASCADE,
        related_name="terrains"
    )

    proprietaire = models.ForeignKey(
        Proprietaire,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="terrains"
    )

    titre = models.CharField(max_length=150)
    type_operation = models.CharField(
        max_length=20,
        choices=TYPE_OPERATION,
        default="vente"
    )

    statut = models.CharField(
        max_length=30,
        choices=STATUT_TERRAIN,
        default="libre"
    )

    qualite = models.CharField(
        max_length=20,
        choices=QUALITE_TERRAIN,
        default="15/20"
    )

    pays = models.CharField(max_length=100, default="Mali")
    ville = models.CharField(max_length=100)
    quartier = models.CharField(max_length=150, blank=True, null=True)
    adresse = models.CharField(max_length=255, blank=True, null=True)

    superficie = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Superficie en m²"
    )

    prix = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    description = models.TextField(blank=True, null=True)
    document_disponible = models.BooleanField(default=False)

    actif = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.titre




from decimal import Decimal

from django.core.exceptions import ValidationError



class Depense(models.Model):

    TYPE_DEPENSE_CHOICES = [
        ("agence", "Dépense de l’agence"),
        ("proprietaire", "Dépense du propriétaire"),
    ]

    CATEGORIE_CHOICES = [
        ("entretien", "Entretien"),
        ("reparation", "Réparation"),
        ("electricite", "Électricité"),
        ("eau", "Eau"),
        ("gardiennage", "Gardiennage"),
        ("nettoyage", "Nettoyage"),
        ("taxe", "Taxe"),
        ("assurance", "Assurance"),
        ("transport", "Transport"),
        ("administration", "Administration"),
        ("construction", "Construction"),
        ("autre", "Autre"),
    ]

    agence = models.ForeignKey(
        Agence,
        on_delete=models.CASCADE,
        related_name="depenses"
    )

    proprietaire = models.ForeignKey(
        Proprietaire,
        on_delete=models.CASCADE,
        related_name="depenses",
        null=True,
        blank=True
    )

    type_depense = models.CharField(
        max_length=20,
        choices=TYPE_DEPENSE_CHOICES
    )

    categorie = models.CharField(
        max_length=30,
        choices=CATEGORIE_CHOICES,
        default="autre"
    )

    titre = models.CharField(
        max_length=200
    )

    description = models.TextField(
        blank=True
    )

    montant = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    date_depense = models.DateField()

    justificatif = models.FileField(
        upload_to="depenses/justificatifs/",
        null=True,
        blank=True
    )

    ajoute_par = models.CharField(
        max_length=150,
        blank=True
    )

    date_creation = models.DateTimeField(
        auto_now_add=True
    )

    def clean(self):
        super().clean()

        if self.montant is not None and self.montant <= 0:
            raise ValidationError({
                "montant": "Le montant de la dépense doit être supérieur à zéro."
            })

        if self.type_depense == "proprietaire" and not self.proprietaire:
            raise ValidationError({
                "proprietaire": (
                    "Vous devez sélectionner un propriétaire "
                    "pour une dépense propriétaire."
                )
            })

        if self.type_depense == "agence" and self.proprietaire:
            raise ValidationError({
                "proprietaire": (
                    "Une dépense d’agence ne doit pas être liée "
                    "à un propriétaire."
                )
            })

        if (
            self.proprietaire
            and self.agence_id
            and self.proprietaire.agence_id != self.agence_id
        ):
            raise ValidationError({
                "proprietaire": (
                    "Ce propriétaire n’appartient pas à cette agence."
                )
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        if self.type_depense == "proprietaire":
            return (
                f"{self.titre} - {self.proprietaire} "
                f"- {self.montant}"
            )

        return f"{self.titre} - Agence - {self.montant}"

    class Meta:
        ordering = ["-date_depense", "-date_creation"]
        verbose_name = "Dépense"
        verbose_name_plural = "Dépenses"





import uuid

from django.core.validators import FileExtensionValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone


class CentreCommercial(models.Model):

    TYPE_CHOICES = [
        ("centre_commercial", "Centre commercial"),
        ("galerie", "Galerie commerciale"),
        ("marche", "Marché"),
        ("gare", "Gare"),
        ("station", "Station"),
        ("zone_activite", "Zone d’activité"),
        ("immeuble_commercial", "Immeuble commercial"),
        ("autre", "Autre"),
    ]

    agence = models.ForeignKey(
        Agence,
        on_delete=models.CASCADE,
        related_name="centres_commerciaux"
    )

    proprietaire = models.ForeignKey(
        Proprietaire,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="centres_commerciaux"
    )

    batiment = models.ForeignKey(
        Batiment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="centres_commerciaux"
    )

    code = models.CharField(
        max_length=30
    )

    nom = models.CharField(
        max_length=180
    )

    type_centre = models.CharField(
        max_length=30,
        choices=TYPE_CHOICES,
        default="centre_commercial"
    )

    adresse = models.CharField(
        max_length=255
    )

    ville = models.CharField(
        max_length=120
    )

    quartier = models.CharField(
        max_length=120,
        blank=True
    )

    description = models.TextField(
        blank=True
    )

    actif = models.BooleanField(
        default=True
    )

    date_creation = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["nom"]

        constraints = [
            models.UniqueConstraint(
                fields=["agence", "code"],
                name="centre_commercial_code_unique_agence"
            )
        ]

    def __str__(self):
        return f"{self.nom} — {self.ville}"

    @property
    def nombre_locaux(self):
        return self.locaux.filter(actif=True).count()

    @property
    def nombre_locaux_libres(self):
        return self.locaux.filter(
            actif=True,
            statut="libre"
        ).count()

    @property
    def nombre_locaux_occupes(self):
        return self.locaux.filter(
            actif=True,
            statut="occupe"
        ).count()


class LocalCommercial(models.Model):

    TYPE_LOCAL_CHOICES = [
        ("boutique", "Boutique"),
        ("restaurant", "Restaurant"),
        ("bureau", "Bureau"),
        ("atelier", "Atelier"),
        ("entrepot", "Entrepôt"),
        ("kiosque", "Kiosque"),
        ("station", "Station"),
        ("salon", "Salon"),
        ("pharmacie", "Pharmacie"),
        ("supermarche", "Supermarché"),
        ("lieu_travail", "Lieu de travail"),
        ("service", "Local de service"),
        ("autre", "Autre"),
    ]

    STATUT_CHOICES = [
        ("libre", "Libre"),
        ("occupe", "Occupé"),
        ("reserve", "Réservé"),
        ("maintenance", "En maintenance"),
        ("ferme", "Fermé"),
    ]

    centre = models.ForeignKey(
        CentreCommercial,
        on_delete=models.CASCADE,
        related_name="locaux"
    )

    numero = models.CharField(
        max_length=50
    )

    nom = models.CharField(
        max_length=150,
        blank=True
    )

    type_local = models.CharField(
        max_length=30,
        choices=TYPE_LOCAL_CHOICES,
        default="boutique"
    )

    superficie = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    prix_mensuel = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0
    )

    caution = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0
    )

    description = models.TextField(
        blank=True
    )

    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default="libre"
    )

    actif = models.BooleanField(
        default=True
    )

    date_creation = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = [
            "centre__nom",
            "numero"
        ]

        constraints = [
            models.UniqueConstraint(
                fields=["centre", "numero"],
                name="numero_local_unique_dans_centre"
            )
        ]

    def __str__(self):
        return (
            f"{self.centre.nom} — "
            f"{self.get_type_local_display()} {self.numero}"
        )

    @property
    def est_disponible(self):
        return (
            self.actif
            and self.statut in ["libre", "reserve"]
            and not self.contrats.filter(actif=True).exists()
        )


class OccupantCommercial(models.Model):

    TYPE_PIECE_CHOICES = [
        ("carte_identite", "Carte d’identité"),
        ("passeport", "Passeport"),
        ("permis", "Permis de conduire"),
        ("carte_consulaire", "Carte consulaire"),
        ("autre", "Autre"),
    ]

    agence = models.ForeignKey(
        Agence,
        on_delete=models.CASCADE,
        related_name="occupants_commerciaux"
    )

    nom = models.CharField(
        max_length=120
    )

    prenom = models.CharField(
        max_length=120
    )

    date_naissance = models.DateField(
        null=True,
        blank=True
    )

    lieu_naissance = models.CharField(
        max_length=180,
        blank=True
    )

    nationalite = models.CharField(
        max_length=120,
        blank=True
    )

    telephone = models.CharField(
        max_length=40
    )

    email = models.EmailField(
        blank=True
    )

    adresse = models.TextField(
        blank=True
    )

    profession = models.CharField(
        max_length=150,
        blank=True
    )

    nom_entreprise = models.CharField(
        max_length=180,
        blank=True
    )

    activite_commerciale = models.CharField(
        max_length=180,
        blank=True
    )

    registre_commerce = models.CharField(
        max_length=100,
        blank=True
    )

    type_piece = models.CharField(
        max_length=30,
        choices=TYPE_PIECE_CHOICES,
        default="carte_identite"
    )

    numero_piece = models.CharField(
        max_length=100,
        blank=True
    )

    date_expiration_piece = models.DateField(
        null=True,
        blank=True
    )

    photo = models.ImageField(
        upload_to="centres_commerciaux/occupants/photos/",
        validators=[
            FileExtensionValidator(
                ["jpg", "jpeg", "png", "webp"]
            )
        ]
    )

    piece_identite = models.FileField(
        upload_to="centres_commerciaux/occupants/pieces/",
        validators=[
            FileExtensionValidator(
                ["pdf", "jpg", "jpeg", "png"]
            )
        ]
    )

    date_creation = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.prenom} {self.nom}"


class ContratCommercial(models.Model):

    agence = models.ForeignKey(
        Agence,
        on_delete=models.CASCADE,
        related_name="contrats_commerciaux"
    )

    local = models.ForeignKey(
        LocalCommercial,
        on_delete=models.PROTECT,
        related_name="contrats"
    )

    occupant = models.ForeignKey(
        OccupantCommercial,
        on_delete=models.PROTECT,
        related_name="contrats"
    )

    numero_contrat = models.CharField(
        max_length=60,
        unique=True,
        editable=False
    )

    code_verification = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False
    )

    nom_activite = models.CharField(
        max_length=180
    )

    date_debut = models.DateField()

    date_fin = models.DateField(
        null=True,
        blank=True
    )

    prix_mensuel = models.DecimalField(
        max_digits=14,
        decimal_places=2
    )

    caution = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0
    )

    caution_payee = models.BooleanField(
        default=False
    )

    conditions = models.TextField(
        blank=True
    )

    signe_par_occupant = models.BooleanField(
        default=False
    )

    signe_par_gestionnaire = models.BooleanField(
        default=False
    )

    certifie_application = models.BooleanField(
        default=True
    )

    actif = models.BooleanField(
        default=True
    )

    date_signature = models.DateField(
        default=timezone.localdate
    )

    date_creation = models.DateTimeField(
        auto_now_add=True
    )

    date_modification = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["-date_creation"]

    def __str__(self):
        return self.numero_contrat

    def save(self, *args, **kwargs):

        if not self.numero_contrat:

            identifiant = uuid.uuid4().hex[:8].upper()

            self.numero_contrat = (
                f"CC-{timezone.now():%Y%m%d}-{identifiant}"
            )

        super().save(*args, **kwargs)

        if self.actif:

            LocalCommercial.objects.filter(
                id=self.local_id
            ).update(
                statut="occupe"
            )

        else:

            autre_contrat_actif = ContratCommercial.objects.filter(
                local_id=self.local_id,
                actif=True
            ).exclude(
                id=self.id
            ).exists()

            if not autre_contrat_actif:

                LocalCommercial.objects.filter(
                    id=self.local_id
                ).update(
                    statut="libre"
                )

    @property
    def est_certifie(self):

        return (
            self.certifie_application
            and self.signe_par_occupant
            and self.signe_par_gestionnaire
        )

    def get_verification_url(self):

        return reverse(
            "verifier_contrat_commercial",
            args=[self.code_verification]
        )

    def get_pdf_url(self):

        return reverse(
            "contrat_commercial_pdf",
            args=[self.id]
        )