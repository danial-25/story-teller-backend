from django.shortcuts import render,get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .models import User, User_favorites, User_character
from stories.utilities import bot, vector
import pinecone
from dotenv import dotenv_values
from django.core.cache import cache
config = dotenv_values(".env")

max_time_out=2**31-1
@api_view(['POST'])
@permission_classes([AllowAny])
def user_history(request):
    email=request.data.get('email')
    print('hey')
    if email!='undefined':
        cached_data = cache.get(f'{email}-history')
        print(cached_data)
        try:
            fav = get_object_or_404(User_favorites, username=email)
        except:
            fav=None
        if fav is not None:
            if cached_data and len(cached_data['favoriteStories'])==len(fav.favorite_vectors):
                return Response(cached_data)
        pinecone.init(api_key=config['PINECONE_KEY'], environment=config['PINECONE_ENV'])
        index = pinecone.Index("story-teller")
        user = get_object_or_404(User, username=email)
        fav = None 
        try:
            fav = get_object_or_404(User_favorites, username=email)
        except:
            pass
        story_vectors = user.story_vector[::-1]
        response=index.fetch(ids=story_vectors)
        vector_title = []
        vector_audio=[]
        vector_story=[]
        for story_vector in story_vectors:
            vector_title.append(response['vectors'][story_vector]['metadata']['title'])
            vector_audio.append(response['vectors'][story_vector]['metadata']['audio'])
            vector_story.append(response['vectors'][story_vector]['metadata']['story'])
        cache.set(f'{email}-history', {'story': vector_story, 'title': vector_title, 'audio': vector_audio, 'ids': story_vectors, 'favoriteStories': fav.favorite_vectors if fav else []}, timeout=max_time_out)
        return Response({'story': vector_story, 'title':vector_title, 'audio':vector_audio, 'ids':story_vectors, 'favoriteStories':fav.favorite_vectors if fav else []})
    return Response(status=404)




@api_view(['POST', 'DELETE', 'GET'])
@permission_classes([AllowAny])
def user_favorites(request):
    print('yo')
    if request.method=='DELETE':
        story_vector = request.GET.get('story_id')
        user = request.GET.get('email')
        cached_data = cache.get(f'{user}-history')
        print(user)
        cached_data_favorites = cache.get(f'{user}-favorites')
        if cached_data_favorites is None:
            cached_data_favorites = {'story': [], 'title': [], 'audio': [], 'ids': []}
            cache.set(f'{user}-favorites', cached_data_favorites, timeout=max_time_out)
            print(user)
        deleted_object=get_object_or_404(User_favorites, username=user)
        print(story_vector)
        if story_vector in deleted_object.favorite_vectors:
            deleted_object.favorite_vectors.remove(story_vector)
            deleted_object.save()
            cached_data['favoriteStories'].remove(story_vector)
            cache.set(f'{user}-history', cached_data, timeout=max_time_out)
            story=vector.fetch_by_id(story_vector)
            if len(cached_data_favorites['ids'])>0:
                cached_data_favorites['story'].remove(story['story'])
                cached_data_favorites['title'].remove(story['title'])
                cached_data_favorites['audio'].remove(story['audio'])
                cached_data_favorites['ids'].remove(story_vector)
                cache.set(f'{user}-favorites', cached_data_favorites, timeout=max_time_out)
            return Response(status=201)
    if request.method=='POST':
        story_vector=request.data.get('story_id')
        user=request.data.get('email')
        cached_data = cache.get(f'{user}-history')
        print(user)
        cached_data_favorites = cache.get(f'{user}-favorites')
        if cached_data_favorites is None:
            cached_data_favorites = {'story': [], 'title': [], 'audio': [], 'ids': []}
            cache.set(f'{user}-favorites', cached_data_favorites, timeout=max_time_out)
        new_vec, _ = User_favorites.objects.get_or_create(username=user)
        print(new_vec)
        new_vec.favorite_vectors.append(story_vector)
        new_vec.save()
        cached_data['favoriteStories'].append(story_vector)
        cache.set(f'{user}-history',cached_data, timeout=max_time_out)
        story=vector.fetch_by_id(story_vector)
        print(story)
        cached_data_favorites['story'].insert(0, story['story'])
        cached_data_favorites['title'].insert(0, story['title'])
        cached_data_favorites['audio'].insert(0, story['audio'])
        cached_data_favorites['ids'].insert(0, story_vector)
        cache.set(f'{user}-favorites', cached_data_favorites, timeout=max_time_out)
        return Response(status=202)
    if request.method=='GET':
        user=request.GET.get('email')
        cached_data_favorites = cache.get(f'{user}-favorites')
        retrieved=get_object_or_404(User_favorites, username=user)
        if cached_data_favorites and len(cached_data_favorites['ids'])==len(retrieved.favorite_vectors):
            print(cached_data_favorites)
            return Response(cached_data_favorites)
        else:
            cached_data_favorites = {'story': [], 'title': [], 'audio': [], 'ids': []}
            cache.set(f'{user}-favorites', cached_data_favorites, timeout=max_time_out)
        if len(retrieved.favorite_vectors)>0:
            pinecone.init(api_key=config['PINECONE_KEY'], environment=config['PINECONE_ENV'])
            index = pinecone.Index("story-teller")
            response=index.fetch(ids=retrieved.favorite_vectors)
            vector_title = []
            vector_audio=[]
            vector_story=[]
            for story_vector in retrieved.favorite_vectors[::-1]:
                print('yo')
                vector_title.append(response['vectors'][story_vector]['metadata']['title'])
                vector_audio.append(response['vectors'][story_vector]['metadata']['audio'])
                vector_story.append(response['vectors'][story_vector]['metadata']['story'])
            cache.set(f'{user}-favorites', {'story': vector_story, 'title':vector_title, 'audio':vector_audio, 'ids':retrieved.favorite_vectors[::-1] })
            return Response({'story': vector_story, 'title':vector_title, 'audio':vector_audio, 'ids':retrieved.favorite_vectors[::-1] })
    return Response(status=202)     

#character of user generated by gpt based on the favorite stories
@api_view(['GET'])
@permission_classes([AllowAny])
def user_character(request):
    email=request.GET.get('email')
    if email!='undefined':
        try:
            user_fav=User_favorites.objects.get(username=email)
            user_char, created=User_character.objects.get_or_create(username=email)
            user_fav_ids=set(user_fav.favorite_vectors)#setting stories into cache
            user_char_ids=set(user_char.favorite_vectors)
            #comparing in case favorite was added, and the generation doesn't include it
            if user_char_ids != user_fav_ids:
                user_char.favorite_vectors=list(user_fav_ids) 
                user_char.save()
                if len(user_char.favorite_vectors)>0:
                    user_char.description=bot.character(list(user_char.favorite_vectors)) #generation of analysis
                else:
                    user_char.description=''
                user_char.save()    
            return Response({'character':user_char.description})
        except:
            return Response(status=404)
    return Response(status=404)