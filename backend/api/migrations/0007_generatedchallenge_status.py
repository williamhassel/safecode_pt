from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0006_generatedchallenge_is_pooled'),
    ]

    operations = [
        migrations.AddField(
            model_name='generatedchallenge',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending_review', 'Pending Review'),
                    ('approved', 'Approved'),
                    ('discarded', 'Discarded'),
                ],
                default='approved',
                max_length=20,
            ),
        ),
    ]
