from django.db import migrations


TABLE_LOCATION = "immo_location"


def obtenir_colonnes(schema_editor, table_name):
    """
    Retourne la liste des colonnes réellement présentes
    dans une table SQLite.
    """
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            f'PRAGMA table_info("{table_name}")'
        )

        return {
            ligne[1]
            for ligne in cursor.fetchall()
        }


def reparer_colonnes_location(apps, schema_editor):
    """
    Ajoute uniquement les colonnes manquantes de Location.

    Cette migration est nécessaire lorsque l’état Django
    contient les champs, mais que SQLite ne possède pas
    encore les colonnes correspondantes.
    """

    colonnes_existantes = obtenir_colonnes(
        schema_editor,
        TABLE_LOCATION,
    )

    colonnes_a_ajouter = {
        "unite_id": (
            'INTEGER NULL '
            'REFERENCES "immo_unitelocative" ("id")'
        ),

        "date_fin": (
            "date NULL"
        ),

        "contrat_bail_numerique": (
            "varchar(100) NULL"
        ),

        "date_generation_contrat": (
            "datetime NULL"
        ),

        "date_creation": (
            "datetime NULL"
        ),

        "date_modification": (
            "datetime NULL"
        ),
    }

    for nom_colonne, definition_sql in (
        colonnes_a_ajouter.items()
    ):
        if nom_colonne not in colonnes_existantes:
            schema_editor.execute(
                f'ALTER TABLE "{TABLE_LOCATION}" '
                f'ADD COLUMN "{nom_colonne}" '
                f"{definition_sql}"
            )

    # Donner une date de création aux anciennes locations.
    schema_editor.execute(
        f'UPDATE "{TABLE_LOCATION}" '
        'SET "date_creation" = CURRENT_TIMESTAMP '
        'WHERE "date_creation" IS NULL'
    )

    # Créer un index pour accélérer les recherches
    # des locations associées aux unités.
    schema_editor.execute(
        'CREATE INDEX IF NOT EXISTS '
        '"immo_location_unite_id_repair_idx" '
        f'ON "{TABLE_LOCATION}" ("unite_id")'
    )


class Migration(migrations.Migration):

    dependencies = [
        (
            "immo",
            "0017_alter_location_options_and_more",
        ),
    ]

    operations = [
        migrations.RunPython(
            reparer_colonnes_location,
            migrations.RunPython.noop,
        ),
    ]