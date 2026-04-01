# Online Boutique Robot Framework Test Suite

Comprehensive Robot Framework test suite for the Google Cloud Platform microservices-demo (Online Boutique) application.

## Overview

This test suite provides comprehensive test coverage for the Online Boutique application including:

- **UI Tests (01_ui_tests.robot)**: End-to-end browser-based tests
- **API Tests (02_api_tests.robot)**: RESTful API endpoint tests
- **Kubernetes Tests (03_kubernetes_tests.robot)**: Infrastructure and deployment tests
- **Integration Tests (04_integration_tests.robot)**: Service-to-service integration tests
- **Performance Tests (05_performance_tests.robot)**: Load and performance tests
- **Negative Tests (06_negative_tests.robot)**: Error handling and security tests

## Prerequisites

1. **Python 3.8+**
2. **Online Boutique Application** deployed and accessible
3. **kubectl** configured (for Kubernetes tests)
4. **Node.js** (for Browser library)

## Installation

### 1. Clone or download this test suite

```bash
cd online-boutique-tests
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Install Browser library dependencies

```bash
rfbrowser init
```

## Configuration

### Update Test Variables

Edit `resources/config.robot` to match your environment:

```robot
${BASE_URL}                http://your-frontend-url:8080
${NAMESPACE}               your-namespace
${KUBECONFIG}             ~/.kube/config
```

### Common Configuration Scenarios

#### Local Deployment (Minikube/Kind)
```robot
${BASE_URL}                http://localhost:8080
${NAMESPACE}               default
```

#### GKE Deployment
```robot
${BASE_URL}                http://your-external-ip
${NAMESPACE}               default
```

#### Port Forward Setup
If using kubectl port-forward:
```bash
kubectl port-forward svc/frontend 8080:80
```

## Running Tests

### Run All Tests
```bash
robot tests/
```

### Run Specific Test Suite
```bash
robot tests/01_ui_tests.robot
robot tests/02_api_tests.robot
robot tests/03_kubernetes_tests.robot
```

### Run Tests by Tag
```bash
# Run only smoke tests
robot --include smoke tests/

# Run only API tests
robot --include api tests/

# Run E2E tests
robot --include e2e tests/

# Exclude slow tests
robot --exclude performance tests/
```

### Run Specific Test Case
```bash
robot --test "TC001: Verify Home Page Loads Successfully" tests/01_ui_tests.robot
```

### Run in Headless Mode
```bash
robot --variable HEADLESS:True tests/01_ui_tests.robot
```

### Run with Different Browser
```bash
robot --variable BROWSER:firefox tests/01_ui_tests.robot
```

## Test Tags

Tests are organized with the following tags:

- `smoke`: Critical smoke tests for quick validation
- `ui`: User interface tests
- `api`: API endpoint tests
- `k8s`: Kubernetes infrastructure tests
- `integration`: Integration tests
- `e2e`: End-to-end workflow tests
- `performance`: Performance and load tests
- `negative`: Negative test cases
- `security`: Security-related tests
- `critical`: Business critical tests

## Test Reports

After running tests, Robot Framework generates:

- `report.html`: Detailed test execution report
- `log.html`: Detailed log with screenshots (for UI tests)
- `output.xml`: Machine-readable results

### View Reports
```bash
# Open in browser
open report.html  # macOS
xdg-open report.html  # Linux
start report.html  # Windows
```

## Test Structure

```
online-boutique-tests/
├── tests/                      # Test suites
│   ├── 01_ui_tests.robot      # UI tests
│   ├── 02_api_tests.robot     # API tests
│   ├── 03_kubernetes_tests.robot
│   ├── 04_integration_tests.robot
│   ├── 05_performance_tests.robot
│   └── 06_negative_tests.robot
├── keywords/                   # Reusable keywords
│   ├── cart_keywords.robot
│   └── checkout_keywords.robot
├── resources/                  # Configuration & common resources
│   ├── config.robot
│   └── common_keywords.robot
├── libraries/                  # Custom Python libraries (if needed)
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## Writing New Tests

### Example Test Case

```robot
*** Test Cases ***
My New Test Case
    [Documentation]    Description of what this test does
    [Tags]    ui    smoke
    Open Online Boutique
    Verify Product Card Visible    Vintage Camera
    Add Product To Cart    Vintage Camera
    Navigate To Cart
    Get Cart Item Count
    [Teardown]    Clear Cart
```

### Using Keywords

Import keywords from resource files:

```robot
*** Settings ***
Resource    ../keywords/cart_keywords.robot

*** Test Cases ***
Test Cart Functionality
    Add Product To Cart    Vintage Camera
    Verify Product In Cart    Vintage Camera
    Remove Product From Cart    Vintage Camera
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Robot Framework Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          rfbrowser init
      - name: Run smoke tests
        run: robot --include smoke tests/
      - name: Upload results
        uses: actions/upload-artifact@v2
        if: always()
        with:
          name: robot-results
          path: |
            report.html
            log.html
            output.xml
```

## Troubleshooting

### Issue: Browser tests fail to start
**Solution**: Install browser drivers
```bash
rfbrowser init
```

### Issue: Kubernetes tests fail
**Solution**: Verify kubectl is configured
```bash
kubectl config current-context
kubectl get pods -n default
```

### Issue: Connection refused errors
**Solution**: Verify the application is running
```bash
kubectl get svc frontend-external
curl http://your-frontend-url
```

### Issue: Tests timeout
**Solution**: Increase timeout values in config.robot
```robot
${BROWSER_TIMEOUT}         30s
${API_TIMEOUT}             10
```

## Best Practices

1. **Tag Tests Appropriately**: Use tags to organize and filter tests
2. **Use Variables**: Define URLs and configuration in config.robot
3. **Reuse Keywords**: Create reusable keywords for common operations
4. **Clean Up**: Use test teardowns to clean up test data
5. **Document Tests**: Use [Documentation] to explain test purpose
6. **Run Smoke Tests First**: Use --include smoke for quick validation
7. **Parallel Execution**: Use Pabot for parallel execution (advanced)

## Parallel Execution (Optional)

Install Pabot for parallel test execution:

```bash
pip install robotframework-pabot
```

Run tests in parallel:

```bash
pabot --processes 4 tests/
```

## Advanced Configuration

### Custom Variables File

Create a custom variables file for different environments:

```bash
robot --variablefile env/staging.py tests/
robot --variablefile env/production.py tests/
```

### Debugging

Run with debug logging:

```bash
robot --loglevel DEBUG tests/01_ui_tests.robot
```

Pause execution for debugging:

```robot
*** Test Cases ***
Debug Test
    Open Online Boutique
    Debug    # Pauses execution for inspection
    Navigate To Cart
```

## Contributing

When adding new tests:

1. Follow the existing naming convention (TC###)
2. Add appropriate tags
3. Document the test purpose
4. Use existing keywords when possible
5. Update this README if adding new test categories

## Support

For issues with:
- **Test Suite**: Check this README and logs
- **Online Boutique App**: See [GitHub repo](https://github.com/GoogleCloudPlatform/microservices-demo)
- **Robot Framework**: See [Robot Framework User Guide](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html)

## License

This test suite is provided as-is for testing the Online Boutique application.
