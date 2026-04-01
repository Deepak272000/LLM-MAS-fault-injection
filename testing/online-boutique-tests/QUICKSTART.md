# Quick Start Guide

Get up and running with the Online Boutique Robot Framework tests in 5 minutes!

## Prerequisites

- Python 3.8 or higher
- Online Boutique application running (locally or remote)
- pip (Python package manager)

## Step 1: Install Dependencies

```bash
# Install Python packages
pip install -r requirements.txt

# Initialize browser drivers
rfbrowser init
```

## Step 2: Configure Your Environment

Edit `resources/config.robot` and update the BASE_URL:

```robot
${BASE_URL}    http://localhost:8080  # Change to your Online Boutique URL
```

### Common URLs:
- **Local (port-forward)**: `http://localhost:8080`
- **Minikube**: `http://$(minikube ip):30001`
- **GKE**: `http://YOUR_EXTERNAL_IP`

## Step 3: Run Smoke Tests

Quick validation that everything works:

```bash
robot --include smoke tests/
```

Expected output:
```
==============================================================================
Tests                                                                         
==============================================================================
Tests.01 Ui Tests :: End-to-end UI tests for Online Boutique application     
==============================================================================
TC001: Verify Home Page Loads Successfully                            | PASS |
------------------------------------------------------------------------------
TC004: Add Single Product To Cart                                     | PASS |
------------------------------------------------------------------------------
TC007: Complete Full Checkout Process                                 | PASS |
==============================================================================
```

## Step 4: Run Full Test Suite

```bash
robot tests/
```

## Step 5: View Results

Open the generated report:

```bash
# macOS
open report.html

# Linux
xdg-open report.html

# Windows
start report.html
```

## Common Issues

### Issue: "Connection refused"
**Fix**: Make sure Online Boutique is running
```bash
kubectl get svc frontend-external
curl http://YOUR_URL
```

### Issue: "rfbrowser: command not found"
**Fix**: Install browser library properly
```bash
pip install robotframework-browser
rfbrowser init
```

### Issue: "No tests found"
**Fix**: Make sure you're in the correct directory
```bash
cd online-boutique-tests
ls tests/  # Should show .robot files
```

## Quick Commands

```bash
# Smoke tests only
make smoke

# UI tests only
make ui

# All tests
make test

# Clean results
make clean
```

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Explore individual test files in `tests/` directory
- Customize tests for your specific needs
- Set up CI/CD with the provided GitHub Actions workflow

## Need Help?

Check the troubleshooting section in README.md or run:
```bash
make help
```

## Test Coverage Summary

| Test Suite | Tests | Coverage |
|------------|-------|----------|
| UI Tests | 15 | Complete user flows |
| API Tests | 15 | All microservices |
| K8s Tests | 15 | Infrastructure validation |
| Integration | 15 | Service interactions |
| Performance | 15 | Load & response times |
| Negative | 20 | Error handling |

**Total: 95 test cases** covering all aspects of Online Boutique!

Happy Testing! 🚀
