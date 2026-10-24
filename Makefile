.PHONY: help run test coverage contract-test sandbox sandbox-stop install

HOST_PORT ?= 8080

help:
	@echo "make install        Install runtime and test dependencies"
	@echo "make run            Start the service on 0.0.0.0:$(HOST_PORT) so your neighbour can reach it"
	@echo "make test           Run the unit and integration tests"
	@echo "make coverage       Run the tests and write an HTML coverage report"
	@echo "make contract-test  Run the contract test against NEIGHBOR_BASE_URL"
	@echo "make sandbox        Same as run, but in Docker"

install:
	python -m pip install -r requirements.txt -r requirements-dev.txt

## Bind to 0.0.0.0, not 127.0.0.1 — on localhost your neighbour cannot reach you.
run:
	python -m uvicorn main:app --host 0.0.0.0 --port $(HOST_PORT)

test:
	python -m pytest

coverage:
	python -m pytest --cov=. --cov-report=term --cov-report=html
	@echo "Open htmlcov/index.html in a browser."

## Session 05. Point this at the neighbouring team's running sandbox:
##   make contract-test NEIGHBOR_BASE_URL=http://10.0.0.42:8080
contract-test:
	@test -n "$(NEIGHBOR_BASE_URL)" || \
		{ echo "Set NEIGHBOR_BASE_URL, e.g. make contract-test NEIGHBOR_BASE_URL=http://10.0.0.42:8080"; exit 1; }
	NEIGHBOR_BASE_URL=$(NEIGHBOR_BASE_URL) python -m pytest tests/contract -v -s

sandbox:
	docker compose up --build -d
	@echo "Listening on 0.0.0.0:$(HOST_PORT). Tell your neighbour: http://<your-ip>:$(HOST_PORT)"

sandbox-stop:
	docker compose down
