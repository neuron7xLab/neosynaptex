"""
Extension modules for MLSDM (NeuroLang, Aphasia-Broca, etc.).
"""

from .neuro_lang_extension import AphasiaBrocaDetector, NeuroLangWrapper

__all__ = [
    "NeuroLangWrapper",
    "AphasiaBrocaDetector",
]
