#!/bin/bash
# delete python 2.X's pyc file clutter here (3.X's __pycache__ is better)

echo 'before:' *.pyc
rm *.pyc
echo 'after:' *.pyc