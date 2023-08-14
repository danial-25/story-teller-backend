FROM python:3.10.6

WORKDIR /story-teller/back

COPY . .

RUN pip install -r requirements.txt
RUN python3 manage.py makemigrations
RUN python3 manage.py migrate
RUN python3 manage.py store_vectors

CMD ["python3", "manage.py", "runserver", "0.0.0.0:8000"]
