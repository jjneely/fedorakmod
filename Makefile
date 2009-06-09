VERSION=1.0.1
NAME=fedorakmod
SPEC=yum-plugin-kmod.spec

ifndef PYTHON
PYTHON=/usr/bin/python
endif
SITELIB=`$(PYTHON) -c "from distutils.sysconfig import get_python_lib; print get_python_lib()"`

.PHONY: archive clean

all:
	@echo "WebKickstart Makefile"
	@echo
	@echo "make clean 		-- Clean the source directory"
	@echo "make archive		-- Build a tar.bz2 ball for release"
	@echo "make srpm		-- Build a src.rpm for release"
	@echo "make install     -- Do useful things - define a DESTDIR"
	@echo

install:
	install -m 755 -d $(DESTDIR)/usr/lib/yum-plugins
	install -m 755 -d $(DESTDIR)/usr/share/fedorakmod
	install -m 755 -d $(DESTDIR)/etc/yum/pluginconf.d
	
	install -m 644 fedorakmod.py   $(DESTDIR)/usr/lib/yum-plugins/
	install -m 644 fedorakmod.conf $(DESTDIR)/etc/yum/pluginconf.d/
	install -m 644 kmodtool        $(DESTDIR)/usr/share/fedorakmod/

srpm: archive
	rpmbuild --define "_srcrpmdir ." -ts $(NAME)-$(VERSION).tar.bz2

clean:
	rm -f `find . -name \*.pyc -o -name \*~`
	rm -f $(NAME)-*.tar.bz2

release: archive
	git tag -f -a -m "Tag $(VERSION)" $(VERSION)

archive:
	if ! grep "Version: $(VERSION)" $(SPEC) > /dev/null ; then \
		sed -i '/^Version: $(VERSION)/q; s/^Version:.*$$/Version:        $(VERSION)/' $(SPEC) ; \
		git add $(SPEC) ; git commit -m "Bumb version tag to $(VERSION)" ; \
	fi
	git archive --prefix=$(NAME)-$(VERSION)/ \
		--format=tar HEAD | bzip2 > $(NAME)-$(VERSION).tar.bz2
	@echo "The archive is in $(NAME)-$(VERSION).tar.bz2"

