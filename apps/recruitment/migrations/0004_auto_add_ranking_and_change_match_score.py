from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ("recruitment", "0003_candidate_analysis_completed_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="analysis",
            name="ranking_position",
            field=models.IntegerField(blank=True, db_index=True, null=True),
        ),
        migrations.AlterField(
            model_name="analysis",
            name="match_score",
            field=models.FloatField(
                db_index=True,
                default=0.0,
                validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)],
            ),
        ),
    ]
