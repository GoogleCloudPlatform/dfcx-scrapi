python-setup:
	sudo apt-get install python3-venv
	python3 -m venv venv
	pip3 install --upgrade pip
	python3 -m pip install --upgrade setuptools

pinstall:
	pip install -r requirements.txt

pfreeze:
	pip freeze > requirements.txt

test:
	pytest tests/dfcx_scrapi/core/$(f)

lint:
	pylint --rcfile=.pylintrc src/dfcx_scrapi/*
	pylint --rcfile=.pylintrc tests/dfcx_scrapi/*

# just fix selected whitespace
autofix-min-whitespace:
	autopep8 --select W291,E302,E301 --in-place *py

# fix all default whitespace issues in place
# use it like
# make autofix f=somefile.py
autofix-all:
	autopep8 --aggressive --aggressive --verbose --in-place ${f}

# use it like this:
# make fix f=tools/validation_util.py
fix:
	black --line-length=80 ${f}

build:
	python3 -m build
	pip uninstall dfcx-scrapi -y
