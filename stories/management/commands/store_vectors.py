from django.core.management.base import BaseCommand
from stories.utilities import vector
from dotenv import dotenv_values
import pinecone
import openai
from stories.utilities import bot
from stories.models import Stories
config = dotenv_values(".env")
openai.api_key = config["OPENAI_API_KEY"]
from django.db.models import Sum


class Command(BaseCommand):
    help = 'retrieve all the vectors from vector db and store them in sql grouped by langs'
    def handle(self, *args, **options):
        embedding=vector.get_embedding('hey')#retrieving all vectors
        pinecone.init(api_key=config['PINECONE_KEY'], environment=config['PINECONE_ENV'])
        index = pinecone.Index("story-teller")
        result = index.query(embedding, top_k=10000, include_metadata=True)
        total_amount = Stories.objects.aggregate(total=Sum('amount'))['total']
        if total_amount is None:
            total_amount=0
        if total_amount<len(result['matches']):
            for i in result['matches']:
                language=bot.detect_lang(i['metadata']['title'])
                print(language)
                stories, created = Stories.objects.get_or_create(language=language)
                id_to_append = i['id']

                if id_to_append not in stories.story_ids:
                    stories.story_ids.append(id_to_append)
                    print(id_to_append)
                    stories.amount+=1
                    stories.save()
        self.stdout.write('Retrieval suceeded')