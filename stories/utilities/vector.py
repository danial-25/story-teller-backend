import pinecone
import openai
import uuid
import time
import traceback
from users.models import User
import json
from dotenv import dotenv_values
from stories.models import Stories
config = dotenv_values(".env")
openai.api_key = config["OPENAI_API_KEY"]
def get_embedding(text, model="text-embedding-ada-002"):
    text = text.replace("\n", " ")
    embedding=openai.Embedding.create(input = [text], model=model)['data'][0]['embedding']
    return embedding




def get_story(username, text):
    pinecone.init(api_key=config['PINECONE_KEY'], environment=config['PINECONE_ENV'])
    index = pinecone.Index("story-teller")
    embedding=get_embedding(text)#getting vector embed we can make a similiarity search
    print(embedding is not None)
    try:
        if username!='undefined':
            result = index.query(embedding, top_k=100, include_metadata=True)
            search=User.objects.get(username=username)
            print(search)
            print(len(result['matches']))
            for i in range(len(result['matches'])):#retrieving suitable story out of all matches
                if result['matches'][i]['score']>=0.915 and search.has_story_vector(result['matches'][i]['id'])==False:
                    story = result['matches'][i]
                    return story
        return None
    except Exception as e:
        traceback.print_exc()  # Print the full traceback
        print("Exception:", str(e))  # Print the exception message
        return None
def create_story(username,title, story, topic,audio, language):
    pinecone.init(api_key=config['PINECONE_KEY'], environment=config['PINECONE_ENV'])
    index = pinecone.Index("story-teller")
    embedding=get_embedding(topic)
    #creating id to store in db
    unique_id = str(uuid.uuid4()) 
    timestamp = str(int(time.time()))
    id=unique_id+timestamp
    print(id)
    index.upsert([(id, embedding, {'title':title,'story':story, 'audio':audio})])
    if username!='undefined':
        search, created=User.objects.get_or_create(username=username)
        search.add_story_vector(id)
    stories, created=Stories.objects.get_or_create(language=language)
    print(stories)
    stories.story_ids.append(id)
    stories.amount+=1
    stories.save()
    return id


def fetch_by_id(id):
    pinecone.init(api_key=config['PINECONE_KEY'], environment=config['PINECONE_ENV'])
    index = pinecone.Index("story-teller")
    try:
        story=index.fetch(ids=[id])
        return story['vectors'][id]['metadata'] 
    except:
        return None