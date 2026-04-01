.PHONY: help install init test smoke ui api k8s integration performance negative clean report

# Default target
help:
	@echo "Online Boutique Robot Framework Test Suite"
	@echo ""
	@echo "Available targets:"
	@echo "  install       - Install Python dependencies"
	@echo "  init          - Initialize browser drivers"
	@echo "  test          - Run all tests"
	@echo "  smoke         - Run smoke tests only"
	@echo "  ui            - Run UI tests"
	@echo "  api           - Run API tests"
	@echo "  k8s           - Run Kubernetes tests"
	@echo "  integration   - Run integration tests"
	@echo "  performance   - Run performance tests"
	@echo "  negative      - Run negative tests"
	@echo "  report        - Open test report in browser"
	@echo "  clean         - Clean test results"
	@echo ""
	@echo "Examples:"
	@echo "  make install"
	@echo "  make smoke"
	@echo "  make test"

# Install dependencies
install:
	pip install -r requirements.txt

# Initialize browser drivers
init:
	rfbrowser init

# Run all tests
test:
	robot tests/

# Run smoke tests
smoke:
	robot --include smoke tests/

# Run UI tests
ui:
	robot tests/01_ui_tests.robot

# Run API tests
api:
	robot tests/02_api_tests.robot

# Run Kubernetes tests
k8s:
	robot tests/03_kubernetes_tests.robot

# Run integration tests
integration:
	robot tests/04_integration_tests.robot

# Run performance tests
performance:
	robot tests/05_performance_tests.robot

# Run negative tests
negative:
	robot tests/06_negative_tests.robot

# Run critical tests
critical:
	robot --include critical tests/

# Run E2E tests
e2e:
	robot --include e2e tests/

# Run tests with specific browser
firefox:
	robot --variable BROWSER:firefox tests/01_ui_tests.robot

chrome:
	robot --variable BROWSER:chromium tests/01_ui_tests.robot

# Run tests in headless mode
headless:
	robot --variable HEADLESS:True tests/

# Open test report
report:
	@if [ -f report.html ]; then \
		if command -v open > /dev/null; then \
			open report.html; \
		elif command -v xdg-open > /dev/null; then \
			xdg-open report.html; \
		else \
			echo "Please open report.html manually"; \
		fi \
	else \
		echo "No report.html found. Run tests first."; \
	fi

# Clean test results
clean:
	rm -f report.html log.html output.xml
	rm -rf screenshots/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Parallel execution with pabot
parallel:
	pabot --processes 4 tests/

# Run with dry run (no actual test execution)
dryrun:
	robot --dryrun tests/

# Validate test syntax
validate:
	robot --dryrun --output NONE --report NONE --log NONE tests/
