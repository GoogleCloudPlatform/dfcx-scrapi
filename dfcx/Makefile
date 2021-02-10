# defautl file for whitespace fixes
f:=dfcx.py

# just fix selected whitespace
autofix-min-whitespace:
	autopep8 --select W291,E302,E301 --in-place *py

# fix all default whitespace issues in place
# use it like
# make autofix f=somefile.py
autofix-all:
	autopep8 --aggressive --aggressive --verbose --in-place ${f}

