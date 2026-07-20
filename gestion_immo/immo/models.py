from django.db import models
from django.contrib.auth.models import User


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
        Agence,
        on_delete=models.CASCADE,
        related_name="batiments"
    )

    proprietaire = models.ForeignKey(
        Proprietaire,
        on_delete=models.CASCADE,
        related_name="batiments"
    )

    code_batiment = models.CharField(max_length=30, unique=True)
    nom = models.CharField(max_length=150)
    adresse = models.CharField(max_length=255)
    ville = models.CharField(max_length=100)
    nombre_logements = models.PositiveIntegerField(default=1)

    description = models.TextField(blank=True, null=True)
    actif = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    def chambres_total(self):
        return self.chambres.count()

    def chambres_occupees(self):
        return self.chambres.filter(locations__active=True).distinct().count()

    def est_totalement_occupe(self):
        return self.chambres_total() > 0 and self.chambres_occupees() == self.chambres_total()

    def est_partiellement_occupe(self):
        return 0 < self.chambres_occupees() < self.chambres_total()

    def est_libre(self):
        return self.chambres_occupees() == 0

    def statut_occupation(self):
        if self.est_totalement_occupe():
            return "Tout occupé"
        elif self.est_partiellement_occupe():
            return "Partiellement occupé"
        return "Libre"

    def locataires_actifs(self):
        return Locataire.objects.filter(
            locations__batiment=self,
            locations__active=True
        ).distinct()

    def __str__(self):
        return f"{self.code_batiment} - {self.nom}"
    

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



class Location(models.Model):
    agence = models.ForeignKey(
        Agence,
        on_delete=models.CASCADE,
        related_name="locations"
    )

    batiment = models.ForeignKey(
        Batiment,
        on_delete=models.CASCADE,
        related_name="locations"
    )

    locataire = models.ForeignKey(
        Locataire,
        on_delete=models.CASCADE,
        related_name="locations"
    )

    chambre = models.ForeignKey(
        ChambreLogement,
        on_delete=models.SET_NULL,
        related_name="locations",
        null=True,
        blank=True
    )

    numero_appartement = models.CharField(max_length=50)

    loyer = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    caution = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    caution_payee = models.BooleanField(default=False)

    date_caution = models.DateField(null=True, blank=True)

    observation_caution = models.TextField(blank=True, null=True)

    date_debut = models.DateField()

    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.locataire.nom} - {self.batiment.nom}"
    



    
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