"""Dysbuntu Correcteur : correcteur orthographique et grammatical pour LibreOffice Writer.

Ce paquet contient la logique pure Python (sans dépendance à UNO), ce qui permet
de la tester hors de LibreOffice. Le code qui parle à UNO se trouve dans
``uno_document.py`` et ``ui.py`` (objets UNO utilisés par duck-typing) ainsi que
dans les composants ``DysbuntuProofreader.py`` et ``DysbuntuDispatch.py``.
"""

__version__ = "0.1.0"
EXTENSION_ID = "org.dysbuntu.correcteur"
