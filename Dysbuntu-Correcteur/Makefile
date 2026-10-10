.PHONY: build test install uninstall demo-server clean
PY ?= python3

build:            ## construit dist/dysbuntu-correcteur-<version>.oxt
	$(PY) build.py

test: build       ## tous les tests (le test LibreOffice est ignoré si LibreOffice manque)
	$(PY) -m unittest discover -s tests -t . -v

install: build    ## installe l'extension pour l'utilisateur courant (fermer LibreOffice avant)
	-unopkg remove org.dysbuntu.correcteur
	unopkg add --suppress-license dist/dysbuntu-correcteur-*.oxt

uninstall:
	unopkg remove org.dysbuntu.correcteur

demo-server:      ## FAUX serveur LanguageTool (démo sans Java) sur le port 8081
	$(PY) tests/fake_languagetool.py --port 8081

clean:
	rm -rf dist build __pycache__
