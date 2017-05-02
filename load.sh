#!/bin/bash


echo "load.sh"
echo "Load files into brwsr from the command line"
echo ""
echo "Usage: load.sh '../path/to/files/*.nq'"
echo "       make sure that the path to files is within single quotes ('') and relative to the 'src' directory"
echo ""

export LOCAL_STORE=True
export LOCAL_FILE=$@

cd src
python run.py
