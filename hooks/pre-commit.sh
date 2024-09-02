#!/bin/bash

# Apply Black to Python files
echo "Running Black..."
black .

# Apply isort to Python files
echo "Running isort..."
isort .

# Add changes made by Black and isort
git add .

# # Run mypy
# echo "Running mypy..."
# mypy .

# # Check if mypy found any errors
# if [ $? -ne 0 ]; then
#     echo "mypy found errors. Commit aborted."
#     exit 1
# fi

# If we've made it here, all checks passed
echo "All checks passed. Proceeding with commit."
exit 0