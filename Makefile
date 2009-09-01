check:
	./ace/run_tests.py

tags: ace/*.py ace/*/*.py
	cd ace ; ctags -R . 

doc: ace/*.py ace/*/*.py
	epydoc --name=ace --exclude=tests --show-imports --src-code-tab-width=4  -o doc ace

callgraph: ace/ace
	pycallgraph --include=ace.* ace/ace

lint:
	pylint --rcfile=pylintrc ace

clean:
	find . -name \*.pyc -exec rm {} \;
	rm -f ace/tags
	rm -f ace/cscope.out
	rm -f ace/ace.profile
	rm -rf ace/.ropeproject/
	rm -rf doc/*
