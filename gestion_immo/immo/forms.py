from django import forms

from .models import (
    CentreCommercial,
    ContratCommercial,
    LocalCommercial,
    OccupantCommercial,
)


# =========================================================
# STYLE AUTOMATIQUE DES FORMULAIRES
# =========================================================

def appliquer_style_formulaire(formulaire):

    for nom_champ, champ in formulaire.fields.items():

        widget = champ.widget

        # Checkbox
        if isinstance(
            widget,
            forms.CheckboxInput
        ):

            widget.attrs.update({
                "class": "form-check-input",
            })

        # Liste déroulante
        elif isinstance(
            widget,
            forms.Select
        ):

            widget.attrs.update({
                "class": "form-select",
            })

        # Zone de texte
        elif isinstance(
            widget,
            forms.Textarea
        ):

            widget.attrs.update({
                "class": "form-control",
                "rows": 4,
            })

        # Fichier
        elif isinstance(
            widget,
            forms.ClearableFileInput
        ):

            widget.attrs.update({
                "class": "form-control",
                "accept": (
                    ".jpg,.jpeg,.png,.webp,.pdf"
                ),
            })

        # Tous les autres champs
        else:

            widget.attrs.update({
                "class": "form-control",
            })

        # Placeholder automatique
        if not isinstance(
            widget,
            (
                forms.CheckboxInput,
                forms.Select,
                forms.ClearableFileInput,
            )
        ):

            widget.attrs.setdefault(
                "placeholder",
                champ.label
            )

    return formulaire


# =========================================================
# FORMULAIRE CENTRE COMMERCIAL
# =========================================================

class CentreCommercialForm(forms.ModelForm):

    class Meta:

        model = CentreCommercial

        fields = [
            "proprietaire",
            "batiment",
            "code",
            "nom",
            "type_centre",
            "adresse",
            "ville",
            "quartier",
            "description",
            "actif",
        ]

        labels = {
            "proprietaire": "Propriétaire",
            "batiment": "Bâtiment associé",
            "code": "Code du centre",
            "nom": "Nom du centre",
            "type_centre": "Type de centre",
            "adresse": "Adresse complète",
            "ville": "Ville",
            "quartier": "Quartier",
            "description": "Description",
            "actif": "Centre actif",
        }

        widgets = {
            "description": forms.Textarea(
                attrs={
                    "rows": 4,
                }
            ),
        }

    def clean_code(self):

        code = self.cleaned_data.get(
            "code",
            ""
        ).strip().upper()

        if not code:

            raise forms.ValidationError(
                "Le code du centre est obligatoire."
            )

        return code

    def clean_nom(self):

        nom = self.cleaned_data.get(
            "nom",
            ""
        ).strip()

        if not nom:

            raise forms.ValidationError(
                "Le nom du centre est obligatoire."
            )

        return nom


# =========================================================
# FORMULAIRE LOCAL COMMERCIAL
# =========================================================

class LocalCommercialForm(forms.ModelForm):

    class Meta:

        model = LocalCommercial

        fields = [
            "numero",
            "nom",
            "type_local",
            "superficie",
            "prix_mensuel",
            "caution",
            "description",
            "statut",
            "actif",
        ]

        labels = {
            "numero": "Numéro du local",
            "nom": "Nom du local",
            "type_local": "Type de local",
            "superficie": "Superficie en m²",
            "prix_mensuel": "Prix mensuel",
            "caution": "Montant de la caution",
            "description": "Description",
            "statut": "Statut du local",
            "actif": "Local actif",
        }

        widgets = {
            "superficie": forms.NumberInput(
                attrs={
                    "min": "0",
                    "step": "0.01",
                }
            ),

            "prix_mensuel": forms.NumberInput(
                attrs={
                    "min": "0",
                    "step": "0.01",
                }
            ),

            "caution": forms.NumberInput(
                attrs={
                    "min": "0",
                    "step": "0.01",
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "rows": 4,
                }
            ),
        }

    def clean_numero(self):

        numero = self.cleaned_data.get(
            "numero",
            ""
        ).strip().upper()

        if not numero:

            raise forms.ValidationError(
                "Le numéro du local est obligatoire."
            )

        return numero

    def clean_prix_mensuel(self):

        prix = self.cleaned_data.get(
            "prix_mensuel"
        )

        if prix is not None and prix < 0:

            raise forms.ValidationError(
                "Le prix mensuel ne peut pas être négatif."
            )

        return prix

    def clean_caution(self):

        caution = self.cleaned_data.get(
            "caution"
        )

        if caution is not None and caution < 0:

            raise forms.ValidationError(
                "La caution ne peut pas être négative."
            )

        return caution


# =========================================================
# FORMULAIRE PERSONNE OCCUPANTE
# =========================================================

class OccupantCommercialForm(forms.ModelForm):

    class Meta:

        model = OccupantCommercial

        fields = [
            "nom",
            "prenom",
            "date_naissance",
            "lieu_naissance",
            "nationalite",
            "telephone",
            "email",
            "adresse",
            "profession",
            "nom_entreprise",
            "activite_commerciale",
            "registre_commerce",
            "type_piece",
            "numero_piece",
            "date_expiration_piece",
            "photo",
            "piece_identite",
        ]

        labels = {
            "nom": "Nom",
            "prenom": "Prénom",
            "date_naissance": "Date de naissance",
            "lieu_naissance": "Lieu de naissance",
            "nationalite": "Nationalité",
            "telephone": "Téléphone",
            "email": "Adresse courriel",
            "adresse": "Adresse de résidence",
            "profession": "Profession",
            "nom_entreprise": "Nom de l’entreprise",
            "activite_commerciale": (
                "Activité commerciale"
            ),
            "registre_commerce": (
                "Numéro du registre de commerce"
            ),
            "type_piece": "Type de pièce d’identité",
            "numero_piece": (
                "Numéro de la pièce d’identité"
            ),
            "date_expiration_piece": (
                "Date d’expiration de la pièce"
            ),
            "photo": "Photo d’identité",
            "piece_identite": (
                "Copie de la pièce d’identité"
            ),
        }

        widgets = {
            "date_naissance": forms.DateInput(
                attrs={
                    "type": "date",
                }
            ),

            "date_expiration_piece": forms.DateInput(
                attrs={
                    "type": "date",
                }
            ),

            "adresse": forms.Textarea(
                attrs={
                    "rows": 3,
                }
            ),

            "photo": forms.ClearableFileInput(
                attrs={
                    "accept": (
                        "image/jpeg,"
                        "image/png,"
                        "image/webp"
                    ),
                }
            ),

            "piece_identite": (
                forms.ClearableFileInput(
                    attrs={
                        "accept": (
                            "application/pdf,"
                            "image/jpeg,"
                            "image/png"
                        ),
                    }
                )
            ),
        }

    def clean_nom(self):

        nom = self.cleaned_data.get(
            "nom",
            ""
        ).strip().upper()

        if not nom:

            raise forms.ValidationError(
                "Le nom est obligatoire."
            )

        return nom

    def clean_prenom(self):

        prenom = self.cleaned_data.get(
            "prenom",
            ""
        ).strip().title()

        if not prenom:

            raise forms.ValidationError(
                "Le prénom est obligatoire."
            )

        return prenom

    def clean_telephone(self):

        telephone = self.cleaned_data.get(
            "telephone",
            ""
        ).strip()

        if not telephone:

            raise forms.ValidationError(
                "Le numéro de téléphone est obligatoire."
            )

        return telephone

    def clean_photo(self):

        photo = self.cleaned_data.get(
            "photo"
        )

        if photo and photo.size > 5 * 1024 * 1024:

            raise forms.ValidationError(
                "La photo ne doit pas dépasser 5 Mo."
            )

        return photo

    def clean_piece_identite(self):

        fichier = self.cleaned_data.get(
            "piece_identite"
        )

        if fichier and fichier.size > 10 * 1024 * 1024:

            raise forms.ValidationError(
                "La pièce d’identité ne doit pas dépasser 10 Mo."
            )

        return fichier


# =========================================================
# FORMULAIRE CONTRAT COMMERCIAL
# =========================================================

class ContratCommercialForm(forms.ModelForm):

    class Meta:

        model = ContratCommercial

        fields = [
            "nom_activite",
            "date_debut",
            "date_fin",
            "prix_mensuel",
            "caution",
            "caution_payee",
            "conditions",
            "signe_par_occupant",
            "signe_par_gestionnaire",
        ]

        labels = {
            "nom_activite": "Nom de l’activité",
            "date_debut": "Date de début",
            "date_fin": "Date de fin",
            "prix_mensuel": "Prix mensuel",
            "caution": "Montant de la caution",
            "caution_payee": "Caution payée",
            "conditions": (
                "Conditions particulières du contrat"
            ),
            "signe_par_occupant": (
                "Contrat signé par l’occupant"
            ),
            "signe_par_gestionnaire": (
                "Contrat signé par le gestionnaire"
            ),
        }

        widgets = {
            "date_debut": forms.DateInput(
                attrs={
                    "type": "date",
                }
            ),

            "date_fin": forms.DateInput(
                attrs={
                    "type": "date",
                }
            ),

            "prix_mensuel": forms.NumberInput(
                attrs={
                    "min": "0",
                    "step": "0.01",
                }
            ),

            "caution": forms.NumberInput(
                attrs={
                    "min": "0",
                    "step": "0.01",
                }
            ),

            "conditions": forms.Textarea(
                attrs={
                    "rows": 6,
                    "placeholder": (
                        "Indiquez les conditions particulières "
                        "du contrat..."
                    ),
                }
            ),
        }

    def clean(self):

        cleaned_data = super().clean()

        date_debut = cleaned_data.get(
            "date_debut"
        )

        date_fin = cleaned_data.get(
            "date_fin"
        )

        prix_mensuel = cleaned_data.get(
            "prix_mensuel"
        )

        caution = cleaned_data.get(
            "caution"
        )

        if (
            date_debut
            and date_fin
            and date_fin < date_debut
        ):

            self.add_error(
                "date_fin",
                (
                    "La date de fin ne peut pas être "
                    "antérieure à la date de début."
                ),
            )

        if (
            prix_mensuel is not None
            and prix_mensuel < 0
        ):

            self.add_error(
                "prix_mensuel",
                (
                    "Le prix mensuel ne peut pas "
                    "être négatif."
                ),
            )

        if caution is not None and caution < 0:

            self.add_error(
                "caution",
                (
                    "Le montant de la caution ne peut "
                    "pas être négatif."
                ),
            )

        return cleaned_data