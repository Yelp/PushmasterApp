lcss_assets := $(shell find lcss -name '*.css')
css_assets := $(patsubst lcss/%.css, css/%.css, $(lcss_assets))
images_assets := $(shell find images -name '*.png' -or -name '*.gif' -or -name '*.jpg')
js_assets := $(shell find js -name '*.js')
checksums:= images.sha css.sha js.sha

.PHONY: clean all

all: static __init__.py

clean:
	rm -rf static __init__.py $(checksums) css images_assets.py

css/%: lcss/% images_assets.py
	@mkdir -p $(@D)
	python make_css.py < $< > $@

images.sha: $(images_assets)
	@echo $(images_assets) | xargs sha1sum > $@

js.sha: $(js_assets)
	@echo $(js_assets) | xargs js -s -C
	@echo $(js_assets) | xargs sha1sum > $@

css.sha: $(css_assets)
	@echo $(css_assets) | xargs sha1sum > $@

images_assets.py: images.sha
	@python make_init.py < $< > $@

__init__.py: $(checksums)
	cat $(checksums) | python make_init.py > $@

static: $(checksums)
	@rm -rf static
	cat $(checksums) | python make_static.py 
