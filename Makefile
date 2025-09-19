IMAGE ?= applehealth
EXPORT ?=
OUT ?=$(PWD)

.PHONY: help docker-build docker-run docker-run-bash run-local

help:
	@echo "Targets:"
	@echo "  make docker-build                 # Build Docker image ($(IMAGE))"
	@echo "  make docker-run EXPORT=/abs/export.xml [OUT=$(OUT)]  # Run Docker and save outputs to OUT"
	@echo "  make docker-run-bash EXPORT=/abs/export.xml [OUT=$(OUT)]  # Start a shell in the container"
	@echo "  make run-local EXPORT=/abs/export.xml [OUT=$(OUT)]   # Run locally with interactive charts"

docker-build:
	docker build -t $(IMAGE) .

docker-run:
	@if [ -z "$(EXPORT)" ]; then \
		echo "Set EXPORT=/absolute/path/to/export.xml"; \
		exit 1; \
	fi
	docker run -it \
	  -v "$(EXPORT)":/export.xml \
	  -v "$(OUT)":/out \
	  $(IMAGE)

docker-run-bash:
	@if [ -z "$(EXPORT)" ]; then \
		echo "Set EXPORT=/absolute/path/to/export.xml"; \
		exit 1; \
	fi
	docker run -it --entrypoint /bin/bash \
	  -v "$(EXPORT)":/export.xml \
	  -v "$(OUT)":/out \
	  $(IMAGE)

run-local:
	@if [ -z "$(EXPORT)" ]; then \
		echo "Set EXPORT=/absolute/path/to/export.xml"; \
		exit 1; \
	fi
	python3 src/applehealth.py --export "$(EXPORT)" --out "$(OUT)"

