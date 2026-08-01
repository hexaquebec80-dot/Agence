import django.utils.timezone
from django.db import migrations, models
import django.db.models.deletion
import immo.models


class Migration(migrations.Migration):

    dependencies = [
        ("immo", "0016_paiement_email_recu_paiement_recu_envoye_email_and_more"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="UniteLocative",
                    fields=[
                        (
                            "id",
                            models.BigAutoField(
                                auto_created=True,
                                primary_key=True,
                                serialize=False,
                                verbose_name="ID",
                            ),
                        ),

                        # IMPORTANT :
                        # Copiez ici tous les autres champs
                        # du CreateModel actuel sans les modifier.
                    ],
                    options={
                        # Copiez ici les options actuelles.
                    },
                ),
            ],
        ),

        # Gardez toutes les autres opérations existantes ici.
        # Exemple :
        #
        # migrations.AddField(...)
        # migrations.AlterField(...)
        # migrations.AddIndex(...)
    ]