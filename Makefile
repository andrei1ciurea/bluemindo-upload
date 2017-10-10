prefix=/usr
LIBDIR=$(DESTDIR)$(prefix)/lib
BIN=$(DESTDIR)$(prefix)/bin
DATADIR=$(DESTDIR)$(prefix)/share
LOCALEDIR=$(DATADIR)/locale
MANDIR=$(DATADIR)/man

all:
clean:
	rm -f locale/*/LC_MESSAGES/bluemindo.mo
	rm -f bluemindo.1.gz


install:
	install -d $(LOCALEDIR) $(BIN) $(DATADIR)/bluemindo $(DATADIR)/bluemindo/image $(DATADIR)/bluemindo/glade $(DATADIR)/bluemindo/src

	install -m644 data/image/*.png $(DATADIR)/bluemindo/image
	install -m644 data/glade/*.ui $(DATADIR)/bluemindo/glade

	install -m644 data/misc/Bluemindo.desktop $(DATADIR)/applications
	install -m644 data/misc/bluemindo.png $(DATADIR)/pixmaps
	install -m755 data/misc/bluemindo $(BIN)

	cat data/misc/bluemindo.1 | gzip > bluemindo.1.gz
	install -m644 bluemindo.1.gz $(MANDIR)/man1

	for sourcedir in `find src/ -type d | grep -v '.svn' | grep -v '.pyc' | sed 's:src/::g'` ; do \
		install -d $(DATADIR)/bluemindo/src/$$sourcedir; \
		for sourcefile in `find src/$$sourcedir -maxdepth 1 -type f | grep -v '.svn' | grep -v '.pyc'` ; do \
			install -m644 $$sourcefile $(DATADIR)/bluemindo/src/$$sourcedir; \
		done \
	done

	install -m755 src/bluemindo.py $(DATADIR)/bluemindo/src
	install -m644 src/mainapplication.py $(DATADIR)/bluemindo/src
	install -m644 src/extensionsloader.py $(DATADIR)/bluemindo/src

	for localename in `find locale/ -maxdepth 1 -type d | grep -v '.svn' | sed 's:locale/::g'` ; do \
		if [ -d locale/$$localename ]; then \
			install -d $(LOCALEDIR)/$$localename; \
			install -d $(LOCALEDIR)/$$localename/LC_MESSAGES; \
			msgfmt locale/$$localename/LC_MESSAGES/bluemindo.po -o locale/$$localename/LC_MESSAGES/bluemindo.mo -v; \
			install -m644 locale/$$localename/LC_MESSAGES/bluemindo.mo $(LOCALEDIR)/$$localename/LC_MESSAGES; \
		fi \
	done

uninstall:
	rm -f $(DATADIR)/applications/Bluemindo.desktop
	rm -f $(DATADIR)/pixmaps/bluemindo.png
	rm -f $(BIN)/bluemindo
	rm -f $(MANDIR)/man1/bluemindo.1.gz
	rm -rf $(LIBDIR)/bluemindo
	rm -rf $(DATADIR)/bluemindo

	for gettextfile in `find $(LOCALEDIR) -name 'bluemindo.mo'` ; do \
		rm -f $$gettextfile; \
	done