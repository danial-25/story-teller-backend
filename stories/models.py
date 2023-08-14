from django.db import models

# Create your models here.
class Stories(models.Model):
    story_ids = models.JSONField(default=list)
    amount=models.IntegerField(default=0)
    language=models.CharField(max_length=10, default='None')