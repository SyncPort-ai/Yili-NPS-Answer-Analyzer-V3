# Defaults
PORT ?= 7070
IMAGE ?= nps-report-analyzer
TAG ?= v0.0.1

.PHONY: help install run dev docker-build docker-run fmt

help:
	@echo "Common targets:"
	@echo "  make install        # pip install requirements"
	@echo "  make run            # run via python (port 7000 inside app)"
	@echo "  make dev PORT=7070  # run uvicorn --reload on given port"
	@echo "  make docker-build   # build docker image $(IMAGE):$(TAG)"
	@echo "  make docker-run     # run container and map $(PORT)->7000"

install:
	pip install -r requirements.txt

run:
	python api.py

dev:
	uvicorn api:app --reload --port $(PORT)

docker-build:
	docker build -t $(IMAGE):$(TAG) .

docker-run:
	docker run --rm -p $(PORT):7000 $(IMAGE):$(TAG)
