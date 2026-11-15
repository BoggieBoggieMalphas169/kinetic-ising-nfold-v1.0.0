.PHONY: all test sanitize clean

all:
	$(MAKE) -C simulator all

test:
	$(MAKE) -C simulator test

sanitize:
	$(MAKE) -C simulator sanitize

clean:
	$(MAKE) -C simulator clean
	rm -rf build build-sanitize
