from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .utilities import bot, sound
from stories.utilities import vector
from users.models import User
from google.cloud import storage
import re
import os
os.environ['GOOGLE_APPLICATION_CREDENTIALS']='audio_key.json'
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.views.decorators.cache import cache_control
from django.urls import reverse 
from .models import Stories
from users.models import User
import requests
from stories.utilities import bot
from django.core.cache import cache

max_time_out=2**31-1
@api_view(['GET'])
@permission_classes([AllowAny])
def get_story(request):
    topic = request.query_params.get('topic')
    email = request.query_params.get('email')
    cached_data=None
    #check if there are similiar topic in vector db
    check_existence = vector.get_story(email, topic)
    print(check_existence)
    if email!='undefined':
        try:
            cached_data = cache.get(f'{email}-history')
        except:
            cached_data=None
            print('exception')
        if cached_data is None:
            cached_data = {'story': [], 'title': [], 'audio': [], 'ids': [], 'favoriteStories':[]}
            cache.set(f'{email}-history', cached_data, timeout=max_time_out)
    #generation of story
    if check_existence is None:
        answer = bot.tell(topic)
        pattern = r"^As an AI model.*?$"
        answer = re.sub(pattern, "", answer, flags=re.MULTILINE | re.DOTALL)
        #detecting lang to generate suitable audio and txt
        match = re.search(r"Language:\s*(\w+)", answer, flags=re.MULTILINE)
        print(match)
        if match:
            word_after_language = match.group(1)#retrieving language of story
            print(word_after_language)
            paragraphs = answer.split('\n\n')
            answer = '\n\n'.join(paragraphs[1:])
            sound.text_to_audio(answer, word_after_language)
            name = sound.extract_name(answer)
            if len(name) > 50:
                name = sound.first_word(name)
            #storing items in google cloud storage
            storage_client = storage.Client()
            bucket = storage_client.get_bucket('story-teller-audio')
            blob = bucket.blob(name)
            audio_path = f'stories/utilities/sounds/{name}.mp3'
            blob.upload_from_filename(audio_path)  
            story_id=vector.create_story(email, name, answer, topic, blob.public_url, word_after_language)
            print(story_id)
            if cached_data:
                cached_data['story'].insert(0,answer)
                cached_data['title'].insert(0,name)
                cached_data['audio'].insert(0,blob.public_url)
                cached_data['ids'].insert(0,story_id)
                cache.set(f'{email}-history', cached_data, timeout=max_time_out)

            return Response({'story': answer, 'audio': blob.public_url, 'story_id':story_id})
    else:
        #retrieve matching answer
        print(check_existence)
        if cached_data:
            print(cached_data)
            search, created = User.objects.get_or_create(username=email)
            search.add_story_vector(check_existence['id'])
            cached_data['story'].insert(0,check_existence['metadata']['story'])
            cached_data['title'].insert(0,check_existence['metadata']['title'])
            cached_data['audio'].insert(0,check_existence['metadata']['audio'])
            cached_data['ids'].insert(0,check_existence['id'])
            cache.set(f'{email}-history', cached_data, timeout=max_time_out)
        return Response({'story': check_existence['metadata']['story'], 'audio': check_existence['metadata']['audio'], 'story_id':check_existence['id']})
    return Response(status=202)         


@api_view(['GET'])
@permission_classes([AllowAny])
def story_by_id(request, id): 
    story=vector.fetch_by_id(id)
    if story:
        return Response({'story':story['story'], 'audio':story['audio'], 'story_id':id })
    else:
        return Response(status=404)

@api_view(['GET'])
@permission_classes([AllowAny])
def random_story(request):
    #retrieval of stories based on the language user chooses
    username = request.GET.get('email')
    language=request.GET.get('language')
    all_stories, created=Stories.objects.get_or_create(language=language)
    user = None
    print(username)
    #retrieval of random stories from db works only if user is defined
    if username!='undefined':
        cached_data = cache.get(f'{username}-history')
        if cached_data is None:
            cached_data = {'story': [], 'title': [], 'audio': [], 'ids': [], 'favoriteStories':[]}
            cache.set(f'{username}-history', cached_data, timeout=max_time_out)

        try:
            user,created = User.objects.get_or_create(username=username)
        except User.DoesNotExist:
            pass
    if user is not None and len(all_stories.story_ids)>0:
        for id in all_stories.story_ids:
            if user.has_story_vector(id)==False:
                url = reverse('story_by_id', args=[id])
                print(request.build_absolute_uri(url))
                response = requests.get(request.build_absolute_uri(url))
                user.add_story_vector(id)
                story=vector.fetch_by_id(id)

                cached_data['story'].insert(0,story['story'])
                cached_data['title'].insert(0,story['title'])
                cached_data['audio'].insert(0,story['audio'])
                cached_data['ids'].insert(0,id)
                cache.set(f'{username}-history', cached_data, timeout=max_time_out)

                return Response(response.json())
    #unless story is retrieved, the new topic is generated, and then story is generated using get_story function
    topic=bot.topic(language)
    print(topic)
    base_url = request.build_absolute_uri('/')
    url = base_url + reverse('get_story')  
    url += f'?topic={topic}&email={username}' 
    get_story_response = requests.get(url)
    return Response(get_story_response.json())