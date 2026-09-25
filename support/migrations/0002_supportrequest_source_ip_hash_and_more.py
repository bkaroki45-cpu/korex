from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("support", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="supportrequest",
            name="source_ip_hash",
            field=models.CharField(blank=True, db_index=True, editable=False, max_length=64),
        ),
        migrations.AlterField(
            model_name="supportrequest",
            name="message",
            field=models.TextField(max_length=1500),
        ),
    ]