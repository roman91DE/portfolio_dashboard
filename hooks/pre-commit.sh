#!/bin/bash

# Apply Black to Python files
echo "Running Black..."
black .

# Apply isort to Python files
echo "Running isort..."
isort .

# Add changes made by Black and isort
git add .



# If we've made it here, all checks passed
echo "All checks passed. Proceeding with commit."
exit 0