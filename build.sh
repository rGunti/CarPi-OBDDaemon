#!/bin/bash
mode=$1

rm -r build
rm -r dist

python setup.py bdist_wheel --universal
python setup.py sdist

if [[ "$mode" == "prod" ]]; then
    twine upload dist/*
else
    twine upload --repository-url https://test.pypi.org/legacy/ dist/*
fi
