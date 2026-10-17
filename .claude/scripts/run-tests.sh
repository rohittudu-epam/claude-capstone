#!/usr/bin/env bash
# Detects the project type and runs the appropriate test suite
set -euo pipefail

echo "Detecting project type and test runner..."

if [ -f "package.json" ]; then
  echo "Node.js project detected"
  if grep -q '"test"' package.json; then
    echo "Running: npm test"
    npm test 2>&1
  else
    echo "No test script found in package.json"
    exit 1
  fi
elif [ -f "pyproject.toml" ] || [ -f "setup.py" ] || [ -f "pytest.ini" ] || [ -f "setup.cfg" ]; then
  echo "Python project detected"
  if command -v pytest &> /dev/null; then
    echo "Running: pytest -v"
    python -m pytest -v 2>&1
  elif command -v python &> /dev/null; then
    echo "Running: python -m unittest discover"
    python -m unittest discover -v 2>&1
  else
    echo "No Python test runner available"
    exit 1
  fi
elif [ -f "go.mod" ]; then
  echo "Go project detected"
  echo "Running: go test ./... -v"
  go test ./... -v 2>&1
elif [ -f "Cargo.toml" ]; then
  echo "Rust project detected"
  echo "Running: cargo test"
  cargo test 2>&1
else
  echo "No recognized project type. Looking for test directories..."
  if [ -d "tests" ] || [ -d "test" ] || [ -d "__tests__" ]; then
    echo "Test directory found but no test runner detected. Please configure a test runner."
    exit 1
  else
    echo "No tests found."
    exit 1
  fi
fi
