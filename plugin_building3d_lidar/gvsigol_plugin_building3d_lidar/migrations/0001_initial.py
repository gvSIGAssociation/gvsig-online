from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Building3DJob",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("status", models.CharField(max_length=16, choices=[("pending", "Pending"), ("running", "Running"), ("finished", "Finished"), ("failed", "Failed")], default="pending")),
                ("progress", models.PositiveSmallIntegerField(default=0)),
                ("message", models.TextField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("lidar_file_path", models.TextField(blank=True, null=True)),
                ("buildings_zip_path", models.TextField(blank=True, null=True)),
                ("result_geojson", models.TextField(blank=True, null=True)),
                ("result_features_count", models.IntegerField(blank=True, null=True)),
                ("result_center", models.TextField(blank=True, null=True)),
                ("download_path", models.TextField(blank=True, null=True)),
                ("download_name", models.CharField(max_length=255, blank=True, null=True)),
            ],
            options={
                "db_table": "building3d_job",
                "ordering": ("-created_at",),
            },
        )
    ]
