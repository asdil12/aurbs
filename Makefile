
.PHONY: install clean

ifndef DESTDIR
DESTDIR=/
endif

install:
	python setup.py install --optimize=1 --prefix=/usr --root=$(DESTDIR)
	python init.py $(DESTDIR)

clean:
	rm -rf ./build
	find -name "__pycache__" | xargs rm -rf
