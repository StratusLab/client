#!/bin/bash -e

cd $1
virtualenv venv
source venv/bin/activate
pip install $2
