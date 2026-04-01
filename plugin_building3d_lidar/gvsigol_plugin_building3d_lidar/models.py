import uuid
from django.db import models
from django_jsonfield_backport.models import JSONField


class Building3DJob(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("running", "Running"),
        ("finished", "Finished"),
        ("failed", "Failed"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="pending")
    progress = models.PositiveSmallIntegerField(default=0)
    message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(blank=True, null=True)

    # Input file storage (paths on disk)
    lidar_file_path = models.TextField(blank=True, null=True)
    buildings_zip_path = models.TextField(blank=True, null=True)

    # Results
    result_geojson = models.TextField(blank=True, null=True)
    result_features_count = models.IntegerField(blank=True, null=True)
    # Django 2.2 no incluye models.JSONField; usamos el backport instalado (django-jsonfield-backport).
    result_center = JSONField(blank=True, null=True)  # {"lat": ..., "lng": ...}
    download_path = models.TextField(blank=True, null=True)
    download_name = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = "building3d_job"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.id} [{self.status}] {self.progress}%"
