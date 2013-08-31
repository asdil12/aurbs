
.PHONY: install clean

ifndef DESTDIR
DESTDIR=/
endif

install:
	python setup.py install --optimize=1 --prefix=/usr --root=$(DESTDIR)
	python init.py $(DESTDIR)
	mkdir -p $(DESTDIR)/usr/share/aurbs/ui
	cp -r aurbs/ui/{templates,static} $(DESTDIR)/usr/share/aurbs/ui/

clean:
	rm -rf ./build
	find -name "__pycache__" | xargs rm -rf
