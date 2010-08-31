.PHONY: www clean deploy

all: www

clean:
	find . -name '*.py[co]' -delete
	cd www && make clean

www:
	cd www && make

deploy: www
	appcfg.py update -V $(shell bash app-version.sh) .

run: www
	dev_appserver.py .
