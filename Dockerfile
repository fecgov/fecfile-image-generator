FROM python:3.7
ENV PYTHONUNBUFFERED 1

RUN mkdir /opt/imagegenerator
WORKDIR /opt/imagegenerator
ADD . /opt/imagegenerator
RUN pip install -r requirements.txt

#RUN flake8 .

EXPOSE 8080
ENTRYPOINT ["gunicorn", "-w", "4", "--bind", "0.0.0.0:8080", "wsgi:APP"]

