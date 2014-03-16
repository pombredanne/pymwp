##  Makefile
##

PACKAGE=pymwp

PYTHON=python
GIT=git
RM=rm -f
CP=cp -f

all:

install:
	$(PYTHON) setup.py install --home=$(HOME)

clean:
	-$(PYTHON) setup.py clean
	-$(RM) -r build dist MANIFEST
	-cd $(PACKAGE) && $(MAKE) clean

distclean: clean

sdist: distclean MANIFEST.in
	$(PYTHON) setup.py sdist
register: distclean MANIFEST.in
	$(PYTHON) setup.py sdist upload register

WEBDIR=$$HOME/Site/unixuser.org/python/$(PACKAGE)
publish:
	$(CP) docs/*.html docs/*.png docs/*.css $(WEBDIR)
