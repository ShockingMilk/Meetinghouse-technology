from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0007_remove_assetdependency_dependent_asset_and_more"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.AddField(
                    model_name="roomassessment",
                    name="assessment_type",
                    field=models.CharField(
                        choices=[
                            ("full", "Full assessment"),
                            ("focused", "Focused assessment"),
                        ],
                        default="full",
                        max_length=20,
                    ),
                ),
                migrations.AddField(
                    model_name="roomassessment",
                    name="assessed_areas",
                    field=models.JSONField(default=list),
                ),
            ],
            state_operations=[],
        ),
    ]
