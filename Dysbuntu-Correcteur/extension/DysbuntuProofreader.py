# -*- coding: utf-8 -*-
"""Composant UNO : correcteur grammatical (service com.sun.star.linguistic2.Proofreader).

Writer appelle doProofreading() pour chaque paragraphe modifié ; les erreurs
renvoyées sont soulignées et proposées dans le menu contextuel.
"""
import os
import sys

import uno
import unohelper


def _ensure_pythonpath():
    """Le chargeur Python de LibreOffice ajoute déjà « pythonpath » ; ceci est une sécurité."""
    try:
        ctx = uno.getComponentContext()
        pip = ctx.getByName("/singletons/com.sun.star.deployment.PackageInformationProvider")
        url = pip.getPackageLocation("org.dysbuntu.correcteur")
        base = uno.fileUrlToSystemPath(url)
    except Exception:
        base = os.path.dirname(os.path.abspath(globals().get("__file__", ".")))
    path = os.path.join(base, "pythonpath")
    if os.path.isdir(path) and path not in sys.path:
        sys.path.insert(0, path)


_ensure_pythonpath()

from com.sun.star.beans import PropertyValue  # noqa: E402
from com.sun.star.lang import Locale, XInitialization, XServiceDisplayName, XServiceInfo  # noqa: E402
from com.sun.star.linguistic2 import ProofreadingResult, SingleProofreadingError, XProofreader  # noqa: E402

from dysbuntu_correcteur.core import get_core  # noqa: E402
from dysbuntu_correcteur.logutil import get_logger  # noqa: E402
from dysbuntu_correcteur.textutil import utf16_len  # noqa: E402

IMPL_NAME = "org.dysbuntu.correcteur.Proofreader"
SERVICE_NAMES = ("com.sun.star.linguistic2.Proofreader",)
FRENCH_LOCALES = (("fr", "FR"), ("fr", "BE"), ("fr", "CA"), ("fr", "CH"), ("fr", "LU"), ("fr", "MC"))

log = get_logger("component")


def _text_markup_proofreading():
    try:
        return uno.getConstantByName("com.sun.star.text.TextMarkupType.PROOFREADING")
    except Exception:
        return 2


class DysbuntuProofreader(unohelper.Base, XProofreader, XServiceInfo, XServiceDisplayName, XInitialization):
    def __init__(self, ctx):
        self.ctx = ctx
        self.core = get_core()

    # XInitialization
    def initialize(self, args):
        pass

    # XServiceInfo
    def getImplementationName(self):
        return IMPL_NAME

    def supportsService(self, name):
        return name in SERVICE_NAMES

    def getSupportedServiceNames(self):
        return SERVICE_NAMES

    # XServiceDisplayName
    def getServiceDisplayName(self, locale):
        return "Dysbuntu Correcteur"

    # XSupportedLocales
    def hasLocale(self, locale):
        return locale.Language == "fr"

    def getLocales(self):
        return tuple(Locale(lang, country, "") for lang, country in FRENCH_LOCALES)

    # XProofreader
    def isSpellChecker(self):
        return False

    def ignoreRule(self, rule_id, locale):
        self.core.proofreader.ignore_rule(rule_id)

    def resetIgnoreRules(self):
        self.core.proofreader.reset_ignored_rules()

    def doProofreading(self, doc_id, text, locale, start, end_hint, properties):
        result = ProofreadingResult()
        result.aDocumentIdentifier = doc_id
        result.aText = text
        result.aLocale = locale
        result.nStartOfSentencePosition = start
        result.nBehindEndOfSentencePosition = utf16_len(text)
        result.aProperties = ()
        result.aErrors = ()
        try:
            tag = locale.Language + ("-" + locale.Country if locale.Country else "")
            issues = self.core.proofreader.check(text, tag)
            errors = []
            marker = _text_markup_proofreading()
            for issue in issues:
                if issue.offset < start:
                    continue
                err = SingleProofreadingError()
                err.nErrorStart = issue.offset
                err.nErrorLength = issue.length
                err.nErrorType = marker
                err.aRuleIdentifier = issue.rule_id
                err.aShortComment = issue.short_comment
                err.aFullComment = issue.full_comment
                err.aSuggestions = tuple(issue.suggestions)
                prop = PropertyValue()
                prop.Name = "LineColor"
                prop.Value = issue.color
                err.aProperties = (prop,)
                errors.append(err)
            result.aErrors = tuple(errors)
        except Exception as exc:  # ne jamais faire planter Writer
            log.error("doProofreading : %s: %s", type(exc).__name__, exc)
        return result


g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationHelper.addImplementation(DysbuntuProofreader, IMPL_NAME, SERVICE_NAMES)
