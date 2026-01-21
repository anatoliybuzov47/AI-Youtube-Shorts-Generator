#!/bin/bash
export LD_LIBRARY_PATH=$(find $(pwd)/venv/lib/python3.12/site-packages/nvidia -name "lib" -type d | paste -sd ":" -)
source venv/bin/activate
python main.py "$@"
