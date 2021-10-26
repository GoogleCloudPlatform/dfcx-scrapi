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
	pytest tests --cov=tests --project=${gcp_project} --gcs_bucket=${gcs_bucket} --creds=${creds}

lint:
	make pylint ${dir}/*

# just fix selected whitespace
autofix-min-whitespace:
	autopep8 --select W291,E302,E301 --in-place *py

# fix all default whitespace issues in place
# use it like
# make autofix f=somefile.py
autofix-all:
	autopep8 --aggressive --aggressive --verbose --in-place ${f}

# use it like this:
# f=tools/validation_kit.py make lint-lines
lint-lines:
	black --line-length=80 ${f}
