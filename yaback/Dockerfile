FROM python

RUN mkdir -p /home/yaback/app
WORKDIR /home/yaback/app


COPY . /home/yaback/app
RUN pip install -r requirements.txt


EXPOSE 80

CMD ["python", "main.py"]