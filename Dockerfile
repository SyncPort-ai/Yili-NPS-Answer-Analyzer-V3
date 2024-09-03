# Use an official Python runtime as a parent image
FROM python:3.11-slim
# pip配置
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple

RUN mkdir -p /opt/app
COPY requirements.txt /opt/app/requirements.txt
RUN pip install -r /opt/app/requirements.txt --default-timeout=1200
COPY . /opt/app

#RUN mkdir -p /opt/resources
#COPY resources /opt/resources

RUN useradd dota
ENV PYTHONPATH /opt
WORKDIR /opt/app
CMD ["python3", "api.py"]
