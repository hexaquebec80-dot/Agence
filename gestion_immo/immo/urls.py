from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),

    path("proprietaires/", views.proprietaires, name="proprietaires"),


    path("batiments/", views.batiments, name="batiments"),
    path("batiment/ajouter/", views.ajouter_batiment, name="ajouter_batiment"),

    path("locataires/", views.locataires, name="locataires"),
    path("locataire/ajouter/", views.ajouter_locataire, name="ajouter_locataire"),

    path("locations/", views.locations, name="locations"),
    path("paiements/", views.paiements, name="paiements"),
    path("versements/", views.versements, name="versements"),
    path("rapports/", views.rapports, name="rapports"),

    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("logout/", views.logout_view, name="logout"),
    path("proprietaire/ajouter/", views.ajouter_proprietaire, name="ajouter_proprietaire"),

    path("batiment/<int:id>/",views.detail_batiment,name="detail_batiment"),
    path("batiment/modifier/<int:id>/",views.modifier_batiment,name="modifier_batiment"),
    path("employes/",views.employes,name="employes"),

    path("employe/ajouter/",views.ajouter_employe,name="ajouter_employe"),
    path("employe/<int:id>/",views.detail_employe,name="detail_employe"),

    path("employe/modifier/<int:id>/",views.modifier_employe,name="modifier_employe"),

    path("employe/supprimer/<int:id>/",views.supprimer_employe,name="supprimer_employe"),
    path("employe/reset-password/<int:id>/",views.reset_password_employe,name="reset_password_employe"),
    path("employe/modifier-username/<int:id>/",views.modifier_username_employe,name="modifier_username_employe"),
    path("espace-employe/",views.espace_employe,name="espace_employe"),
    path("proprietaire/<int:id>/",views.detail_proprietaire,name="detail_proprietaire"),
    path("proprietaire/modifier/<int:id>/",views.modifier_proprietaire,name="modifier_proprietaire"),
    path("proprietaire/supprimer/<int:id>/",views.supprimer_proprietaire,name="supprimer_proprietaire"),
    path("paiements/ajouter/",views.ajouter_paiement,name="ajouter_paiement"),

    path("locataire/<int:id>/",views.detail_locataire,name="detail_locataire"),
    path(
    "location/<int:id>/modifier/",
    views.modifier_location,
    name="modifier_location",
    ),

    path("locataire/modifier/<int:id>/",views.modifier_locataire,name="modifier_locataire"),

    path("locataire/supprimer/<int:id>/",views.supprimer_locataire,name="supprimer_locataire"),
    path(
        "paiement/<int:paiement_id>/facture/",
        views.facture_paiement_pdf,
        name="facture_paiement_pdf"
    ),

    path(
        "paiement/<int:paiement_id>/recu/",
        views.recu_paiement_pdf,
        name="recu_paiement_pdf"
    ),

    path(
        "paiement/<int:paiement_id>/imprimer/",
        views.imprimer_paiement,
        name="imprimer_paiement"
    ),

    path(
        "paiement/<int:paiement_id>/modifier/",
        views.modifier_paiement,
        name="modifier_paiement"
    ),

    path(
    "statistiques-locataires/",
    views.statistiques_locataires,
    name="statistiques_locataires",
    ),

    path(
    "locataires/modifier/<int:locataire_id>/",
    views.modifier_locataire,
    name="modifier_locataire"
   ),
   path(
    "batiment/<int:id>/supprimer/",
    views.supprimer_batiment,
    name="supprimer_batiment",
    ),
   path(
    "batiment/<int:id>/chambre/ajouter/",
    views.ajouter_chambre,
    name="ajouter_chambre"
   ),
   path("chambre/<int:id>/modifier/", views.modifier_chambre, name="modifier_chambre"),
   path("chambre/<int:id>/supprimer/", views.supprimer_chambre, name="supprimer_chambre"),
   path(
    "chambre/<int:id>/modifier/",
    views.modifier_chambre,
    name="modifier_chamb"
    ),

    path(
    "chambre/<int:id>/supprimer/",
    views.supprimer_chamb,
    name="supprimer_chamb"
   ),

   path(
    "rapport/proprietaire/<int:proprietaire_id>/",
    views.rapport_mensuel_proprietaire,
    name="rapport_mensuel_proprietaire"
    ),

    path(
    "rapports/agence/",
    views.rapport_mensuel_agence,
    name="rapport_mensuel_agence"
   ),




    path(
        "constructions/",
        views.constructions,
        name="constructions"
    ),

    path(
        "constructions/ajouter/",
        views.ajouter_construction,
        name="ajouter_construction"
    ),

    path(
        "constructions/<int:construction_id>/",
        views.detail_construction,
        name="detail_construction"
    ),

    path(
        "constructions/<int:construction_id>/etat/ajouter/",
        views.ajouter_etat_construction,
        name="ajouter_etat_construction"
    ),

    path(
        "constructions/etat/<int:etat_id>/modifier/",
        views.modifier_etat_construction,
        name="modifier_etat_construction"
    ),


    path("terrains/", views.terrains, name="terrains"),
    path("terrains/ajouter/", views.ajouter_terrain, name="ajouter_terrain"),
    path("terrains/<int:terrain_id>/", views.detail_terrain, name="detail_terrain"),
    path( "depenses/agence/", views.depenses_agence,name="depenses_agence" ),
    path(
    "depenses/proprietaires/",
    views.depenses_proprietaires,
    name="depenses_proprietaires"
    ),
    path(
    "depenses/ajouter/",
    views.ajouter_depense,
    name="ajouter_depense"
   ),

   path(
    "depenses/<int:depense_id>/supprimer/",
    views.supprimer_depense,
    name="supprimer_depense"
   ),

   path(
    "employe/paiement/ajouter/",
    views.ajouter_paiement_employe,
    name="ajouter_paiement_employe"
    ),

    path(
    "employe/batiments/",
    views.espace_batiments_employe,
    name="espace_batiments_employe"
    ),

    path(
    "employe/batiment/<int:batiment_id>/",
    views.espace_batiment_employe,
    name="espace_batiment_employe",
     ),

     path(
    "employe/locataire/ajouter/",
    views.ajouter_locataire_employe,
    name="ajouter_locataire_employe"
    ),

    path(
    "employe/locations/",
    views.locations_employe,
    name="locations_employe"
    ),


    path(
    "centres-commerciaux/",
    views.centres_commerciaux,
    name="centres_commerciaux"
    ),

    path(
    "centres-commerciaux/ajouter/",
    views.ajouter_centre_commercial,
    name="ajouter_centre_commercial"
    ),

    path(
    "centres-commerciaux/<int:centre_id>/",
    views.detail_centre_commercial,
    name="detail_centre_commercial"
    ),

    path(
    "centres-commerciaux/<int:centre_id>/local/ajouter/",
    views.ajouter_local_commercial,
    name="ajouter_local_commercial"
    ),

    path(
    "locaux-commerciaux/<int:local_id>/occuper/",
    views.occuper_local_commercial,
    name="occuper_local_commercial"
    ),

    path(
    "contrats-commerciaux/<int:contrat_id>/",
    views.detail_contrat_commercial,
    name="detail_contrat_commercial"
   ),

   path(
    "contrats-commerciaux/<int:contrat_id>/cloturer/",
    views.liberer_local_commercial,
    name="liberer_local_commercial"
    ),

    path(
    "contrats-commerciaux/<int:contrat_id>/pdf/",
    views.contrat_commercial_pdf,
    name="contrat_commercial_pdf"
    ),

    path(
    "verification/contrat-commercial/<uuid:code_verification>/",
    views.verifier_contrat_commercial,
    name="verifier_contrat_commercial"
    ),

    path(
    "support/",
    views.support,
    name="support",
    ),


    path(
    "centres-commerciaux/<int:centre_id>/supprimer/",
    views.supprimer_centre_commercial,
    name="supprimer_centre_commercial",
    ),


    path(
        "locaux-commerciaux/<int:local_id>/supprimer/",
        views.supprimer_local_commercial,
        name="supprimer_local_commercial",
    ),


    path(
    "contrats-commerciaux/<int:contrat_id>/supprimer/",
    views.supprimer_contrat_commercial,
    name="supprimer_contrat_commercial",
    ),

    path(
    "proprietaires/<int:proprietaire_id>/attestation/",
    views.attestation_proprietaire,
    name="attestation_proprietaire"
    ),


    path(
    "unite/<int:unite_id>/affecter-locataire/",
    views.affecter_unite_locataire,
    name="affecter_unite_locataire",
    ),


    path(
    "location/<int:location_id>/generer-contrat/",
    views.generer_contrat_bail,
    name="generer_contrat_bail",
    ),

    path(
    "location/<int:location_id>/liberer-unite/",
    views.liberer_unite_locataire,
    name="liberer_unite_locataire",
    ),

    



]