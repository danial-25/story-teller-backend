from django.db import models

class User(models.Model):
    username = models.CharField(max_length=255, unique=True)
    story_vector = models.JSONField(default=list)

    def add_story_vector(self, vector_id):
        if vector_id not in self.story_vector:
            self.story_vector.append(vector_id)
            self.save()

    def has_story_vector(self, vector_id):
        return vector_id in self.story_vector
class User_favorites(models.Model):
    username = models.CharField(max_length=255, unique=True)
    favorite_vectors=models.JSONField(default=list)
class User_character(models.Model):
    username = models.CharField(max_length=255, unique=True)
    favorite_vectors=models.JSONField(default=list)
    description=models.TextField()