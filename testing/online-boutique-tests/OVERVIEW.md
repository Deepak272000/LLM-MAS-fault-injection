# Online Boutique Robot Framework Test Suite - Overview

## Executive Summary

This comprehensive Robot Framework test suite provides automated testing for the Google Cloud Platform microservices-demo (Online Boutique) e-commerce application. The suite includes **95 test cases** across 6 test categories, covering UI, API, infrastructure, integration, performance, and negative testing scenarios.

## Test Coverage

### 1. UI Tests (15 test cases)
**File**: `tests/01_ui_tests.robot`

- Homepage loading and navigation
- Product browsing and search
- Shopping cart operations (add, remove, update)
- Complete checkout flow
- Currency conversion
- Mobile responsiveness
- Product recommendations

**Key Tests**:
- TC001: Verify Home Page Loads Successfully
- TC004: Add Single Product To Cart
- TC007: Complete Full Checkout Process
- TC013: Product Recommendations Display

### 2. API Tests (15 test cases)
**File**: `tests/02_api_tests.robot`

- Product Catalog API endpoints
- Cart Service API
- Currency Service API
- Checkout Service API
- Health checks
- Response time validation
- Error handling

**Key Tests**:
- TC101: Product Catalog Service - List Products
- TC105: Cart Service - Add Item To Cart
- TC108: Frontend Health Check
- TC109: API Response Time - Product Catalog

### 3. Kubernetes Tests (15 test cases)
**File**: `tests/03_kubernetes_tests.robot`

- Pod status verification
- Service availability
- Deployment health
- Resource limits
- ConfigMaps and Secrets
- Service endpoints
- Autoscaling configuration

**Key Tests**:
- TC201: Verify All Pods Are Running
- TC203: Verify All Required Services Exist
- TC204: Verify Deployments Have Desired Replicas
- TC207: Verify No Pods Are In CrashLoopBackOff

### 4. Integration Tests (15 test cases)
**File**: `tests/04_integration_tests.robot`

- End-to-end purchase workflows
- Service-to-service communication
- Cart persistence (Redis)
- Currency conversion integration
- Recommendation engine
- Shipping cost calculation
- Payment processing
- Email service integration

**Key Tests**:
- TC301: End-to-End Purchase Flow
- TC303: Cart Persistence Across Services
- TC306: Shipping Cost Calculation Integration
- TC315: Checkout Service Orchestration

### 5. Performance Tests (15 test cases)
**File**: `tests/05_performance_tests.robot`

- Page load time benchmarks
- API response time validation
- Concurrent user simulation
- Heavy cart load testing
- Resource loading efficiency
- Search performance
- Currency conversion performance
- Memory leak detection

**Key Tests**:
- TC401: Homepage Load Time Test
- TC404: Add to Cart Performance
- TC408: Concurrent User Load Test
- TC414: Memory Leak Test - Extended Session

### 6. Negative Tests (20 test cases)
**File**: `tests/06_negative_tests.robot`

- Invalid input handling
- Empty cart checkout prevention
- Form validation (email, credit card, zip code)
- SQL injection protection
- XSS prevention
- Rate limiting
- Invalid HTTP methods
- Session handling
- Browser back button behavior

**Key Tests**:
- TC502: Empty Cart Checkout Attempt
- TC509: SQL Injection Attempt in Search
- TC510: XSS Attempt in Input Fields
- TC516: Expired Credit Card

## Technology Stack

- **Robot Framework**: 6.1.1 - Test automation framework
- **Browser Library**: 17.5.2 - Modern browser automation
- **RequestsLibrary**: 0.9.5 - HTTP/REST API testing
- **KubeLibrary**: 0.8.3 - Kubernetes testing
- **SeleniumLibrary**: 6.1.3 - Legacy browser support

## Architecture

```
online-boutique-tests/
├── tests/                  # Test suites (6 files, 95 tests)
├── keywords/              # Reusable keywords
│   ├── cart_keywords.robot
│   └── checkout_keywords.robot
├── resources/             # Configuration & common resources
│   ├── config.robot
│   └── common_keywords.robot
├── libraries/             # Custom Python libraries
├── .github/workflows/     # CI/CD pipeline
├── requirements.txt       # Dependencies
├── Makefile              # Build automation
├── docker-compose.yml    # Container support
├── README.md             # Full documentation
└── QUICKSTART.md         # Quick start guide
```

## Key Features

### 1. Comprehensive Coverage
- **95 test cases** covering all application features
- **6 test categories** for complete validation
- **Multiple testing approaches**: UI, API, Infrastructure

### 2. Enterprise-Ready
- CI/CD integration (GitHub Actions)
- Docker support for containerized testing
- Parallel execution support (Pabot)
- Detailed HTML reports with screenshots

### 3. Maintainable Design
- Keyword-driven approach
- Page Object Model pattern
- Reusable components
- Clear documentation

### 4. Flexible Configuration
- Environment-specific variables
- Multiple browser support
- Headless mode for CI/CD
- Configurable timeouts and retries

## Test Execution Options

### Quick Smoke Test (5 minutes)
```bash
robot --include smoke tests/
```
Runs critical tests to verify basic functionality.

### Full Test Suite (30-45 minutes)
```bash
robot tests/
```
Executes all 95 test cases across all categories.

### Specific Test Category
```bash
robot tests/01_ui_tests.robot        # UI tests only
robot tests/02_api_tests.robot       # API tests only
robot tests/03_kubernetes_tests.robot # K8s tests only
```

### By Tag
```bash
robot --include critical tests/     # Critical tests
robot --include e2e tests/          # End-to-end tests
robot --include performance tests/  # Performance tests
```

## Tag Reference

- **smoke**: Quick validation tests (run first)
- **critical**: Business-critical functionality
- **e2e**: Complete user workflows
- **ui**: Browser-based tests
- **api**: REST API tests
- **k8s**: Kubernetes infrastructure tests
- **integration**: Service integration tests
- **performance**: Load and timing tests
- **negative**: Error handling and security
- **security**: Security-specific tests

## Prerequisites

1. **Python 3.8+**
2. **Online Boutique** deployed and accessible
3. **kubectl** (for Kubernetes tests)
4. **Node.js** (for Browser library)

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Initialize browsers
rfbrowser init

# Configure your environment
vi resources/config.robot  # Update BASE_URL
```

## Success Criteria

### Smoke Tests (Must Pass)
- Homepage loads successfully
- Products are displayed
- Add to cart works
- Checkout completes
- All pods are running

### Full Suite (Expected)
- **Pass Rate**: 90%+ (some tests may be environment-specific)
- **Performance**: All tests under defined thresholds
- **No Critical Failures**: Business-critical paths must pass

## CI/CD Integration

The suite includes a GitHub Actions workflow that:
- Runs smoke tests on every commit
- Executes full suite on PR
- Generates and archives test reports
- Supports scheduled daily runs

```yaml
# .github/workflows/robot-tests.yml
- Smoke tests
- UI tests  
- API tests
- Integration tests
- Result publishing
```

## Reporting

After test execution, Robot Framework generates:

1. **report.html**: High-level test summary with statistics
2. **log.html**: Detailed execution log with screenshots
3. **output.xml**: Machine-readable results for CI/CD

Reports include:
- Pass/fail statistics
- Execution times
- Error messages and stack traces
- Screenshots (for UI tests)
- Tag-based filtering

## Best Practices Implemented

1. **Separation of Concerns**: Tests, keywords, and config separated
2. **DRY Principle**: Reusable keywords for common operations
3. **Clear Naming**: Descriptive test and keyword names
4. **Documentation**: Every test documented with purpose
5. **Error Handling**: Proper teardowns and cleanup
6. **Timeout Management**: Configurable timeouts
7. **Tagging Strategy**: Multiple tag levels for filtering
8. **Environment Agnostic**: Works on local, staging, production

## Maintenance

### Adding New Tests
1. Create test in appropriate suite file
2. Follow naming convention (TC###)
3. Add appropriate tags
4. Document the test purpose
5. Use existing keywords when possible

### Updating Configuration
- Modify `resources/config.robot` for URL/environment changes
- Update `requirements.txt` for new dependencies
- Adjust timeouts based on environment performance

## Support and Resources

- **Test Suite**: This repository
- **Online Boutique**: [GitHub](https://github.com/GoogleCloudPlatform/microservices-demo)
- **Robot Framework**: [Documentation](https://robotframework.org)
- **Browser Library**: [Documentation](https://robotframework-browser.org)

## Version History

- **v1.0.0**: Initial release with 95 test cases
  - Complete UI test coverage
  - Comprehensive API testing
  - Kubernetes infrastructure tests
  - Integration test suite
  - Performance benchmarks
  - Security and negative tests

## License

This test suite is provided for testing the Online Boutique application.
MIT License - See LICENSE file for details.

---

**Ready to start testing?** See [QUICKSTART.md](QUICKSTART.md) for a 5-minute setup guide!
