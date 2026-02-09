"""Text-Fabric data access layer for biblical texts."""

from __future__ import annotations

import logging
import os
from typing import Any

from tf.app import use

from text_fabric_mcp.models import (
    BookInfo,
    FeatureInfo,
    ObjectTypeInfo,
    PassageResult,
    SchemaResult,
    VerseResult,
    WordInfo,
)

logger = logging.getLogger(__name__)

# Corpus registry: name -> (tf org/repo, display name)
CORPORA = {
    "hebrew": ("ETCBC/bhsa", "Biblical Hebrew (BHSA)"),
    "greek": ("ETCBC/nestle1904", "Greek New Testament (Nestle 1904)"),
}

# Word-level features to retrieve per corpus.
# Maps our canonical names to the TF feature names.
WORD_FEATURES = {
    "hebrew": {
        "text": "g_word_utf8",
        "trailer": "trailer_utf8",
        "lexeme": "lex",
        "lexeme_utf8": "lex_utf8",
        "gloss": "gloss",
        "part_of_speech": "sp",
        "gender": "gn",
        "number": "nu",
        "person": "ps",
        "state": "st",
        "verbal_stem": "vs",
        "verbal_tense": "vt",
        "language": "language",
    },
    "greek": {
        "text": "unicode",
        "trailer": "after",
        "lexeme": "lemma",
        "lexeme_utf8": "lemma",
        "gloss": "gloss",
        "part_of_speech": "cls",
        "gender": "gender",
        "number": "number",
        "person": "person",
        "state": "",
        "verbal_stem": "voice",
        "verbal_tense": "tense",
        "language": "",
    },
}

# The word-level object type name differs per corpus
WORD_TYPE = {
    "hebrew": "word",
    "greek": "w",
}


class TFEngine:
    """Manages Text-Fabric corpus loading and queries."""

    def __init__(self) -> None:
        self._apis: dict[str, Any] = {}
        self._loaded: dict[str, bool] = {}

    def _ensure_loaded(self, corpus: str) -> Any:
        """Load a corpus if not already loaded, return the TF API."""
        if corpus not in CORPORA:
            raise ValueError(
                f"Unknown corpus '{corpus}'. Available: {list(CORPORA.keys())}"
            )
        if corpus not in self._apis:
            org_repo, display_name = CORPORA[corpus]
            home = os.environ.get("HOME", "~")
            logger.info(
                "Loading %s from %s (HOME=%s) ...", display_name, org_repo, home
            )
            api = use(org_repo, silent=False)
            # Verify the API initialized properly
            if not hasattr(api, "T") or not hasattr(api.F, "otype"):
                raise RuntimeError(
                    f"Failed to load corpus '{corpus}' from {org_repo}. "
                    f"HOME={home}. "
                    "Text-Fabric data may not have downloaded correctly. "
                    "Check network access and disk space."
                )
            self._apis[corpus] = api
            self._loaded[corpus] = True
            logger.info("Loaded %s", display_name)
        return self._apis[corpus]

    def list_corpora(self) -> list[dict[str, str]]:
        """Return available corpora."""
        return [{"id": cid, "name": display} for cid, (_, display) in CORPORA.items()]

    def list_books(self, corpus: str = "hebrew") -> list[BookInfo]:
        """Return all books with chapter counts for a corpus."""
        A = self._ensure_loaded(corpus)
        api = A.api
        books = []
        for book_node in api.F.otype.s("book"):
            book_name = api.T.sectionFromNode(book_node)[0]
            chapter_nodes = api.L.d(book_node, otype="chapter")
            books.append(BookInfo(name=book_name, chapters=len(chapter_nodes)))
        return books

    def get_passage(
        self,
        book: str,
        chapter: int,
        verse_start: int = 1,
        verse_end: int | None = None,
        corpus: str = "hebrew",
    ) -> PassageResult:
        """Get words with features for a verse range."""
        A = self._ensure_loaded(corpus)
        api = A.api
        feat_map = WORD_FEATURES.get(corpus, WORD_FEATURES["hebrew"])

        if verse_end is None:
            verse_end = verse_start

        wtype = WORD_TYPE.get(corpus, "word")

        verses: list[VerseResult] = []
        for verse_num in range(verse_start, verse_end + 1):
            verse_node = api.T.nodeFromSection((book, chapter, verse_num))
            if verse_node is None:
                continue

            word_nodes = api.L.d(verse_node, otype=wtype)
            words: list[WordInfo] = []
            for w in word_nodes:
                words.append(self._word_info(api, w, feat_map))

            verses.append(
                VerseResult(
                    book=book,
                    chapter=chapter,
                    verse=verse_num,
                    words=words,
                )
            )

        return PassageResult(corpus=corpus, verses=verses)

    def get_schema(self, corpus: str = "hebrew") -> SchemaResult:
        """Return object types and their features for a corpus."""
        A = self._ensure_loaded(corpus)
        api = A.api

        object_types: list[ObjectTypeInfo] = []
        for otype in api.F.otype.all:
            nodes = api.F.otype.s(otype)
            count = len(nodes)
            if count == 0:
                continue

            sample_node = nodes[0]
            features: list[FeatureInfo] = []
            for feat_name in sorted(api.Fall()):
                feat_obj = api.Fs(feat_name)
                val = feat_obj.v(sample_node)
                if val is not None:
                    features.append(FeatureInfo(name=feat_name))

            object_types.append(
                ObjectTypeInfo(name=otype, count=count, features=features)
            )

        return SchemaResult(corpus=corpus, object_types=object_types)

    def search_words(
        self,
        corpus: str = "hebrew",
        book: str | None = None,
        chapter: int | None = None,
        features: dict[str, str] | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Search for words matching feature constraints."""
        A = self._ensure_loaded(corpus)
        api = A.api
        wtype = WORD_TYPE.get(corpus, "word")

        # Build Text-Fabric search template
        constraints = []
        if features:
            for feat, val in features.items():
                constraints.append(f"  {feat}={val}")

        constraint_str = "\n".join(constraints)

        if book and chapter:
            template = (
                f"book book={book}\n"
                f"  chapter chapter={chapter}\n"
                f"    {wtype}\n{constraint_str}\n"
            )
        elif book:
            template = f"book book={book}\n  {wtype}\n{constraint_str}\n"
        else:
            template = f"{wtype}\n{constraint_str}\n"

        results = A.search(template)

        feat_map = WORD_FEATURES.get(corpus, WORD_FEATURES["hebrew"])
        output = []
        for result_tuple in results[:limit]:
            # Last element in tuple is always the word node
            w = result_tuple[-1]
            section = api.T.sectionFromNode(w)
            info = self._word_info(api, w, feat_map)
            output.append(
                {
                    "book": section[0],
                    "chapter": section[1],
                    "verse": section[2],
                    "word": info.model_dump(),
                }
            )

        return output

    def get_context(
        self,
        book: str,
        chapter: int,
        verse: int,
        word_index: int = 0,
        corpus: str = "hebrew",
    ) -> dict:
        """Get the hierarchical context (phrase, clause, sentence) for a word."""
        A = self._ensure_loaded(corpus)
        api = A.api

        wtype = WORD_TYPE.get(corpus, "word")

        verse_node = api.T.nodeFromSection((book, chapter, verse))
        if verse_node is None:
            return {"error": f"Verse not found: {book} {chapter}:{verse}"}

        word_nodes = api.L.d(verse_node, otype=wtype)
        if word_index >= len(word_nodes):
            return {
                "error": f"Word index {word_index} out of range (max {len(word_nodes) - 1})"
            }

        w = word_nodes[word_index]
        feat_map = WORD_FEATURES.get(corpus, WORD_FEATURES["hebrew"])

        context: dict[str, Any] = {
            "word": self._word_info(api, w, feat_map).model_dump(),
        }

        # Walk up the hierarchy — available types vary by corpus
        all_types = [
            t for t in api.F.otype.all if t not in ("book", "chapter", "verse", wtype)
        ]
        for parent_type in all_types:
            parents = api.L.u(w, otype=parent_type)
            if parents:
                parent = parents[0]
                parent_features = {}
                for feat_name in sorted(api.Fall()):
                    feat_obj = api.Fs(feat_name)
                    val = feat_obj.v(parent)
                    if val is not None:
                        parent_features[feat_name] = str(val)
                context[parent_type] = {
                    "node": parent,
                    "features": parent_features,
                    "text": api.T.text(parent),
                }

        return context

    def search_constructions(
        self,
        template: str,
        corpus: str = "hebrew",
        limit: int = 50,
    ) -> list[dict]:
        """Search using a Text-Fabric search template for structural patterns.

        Templates express hierarchical containment. For example:
            clause typ=NmCl
              phrase function=Pred
                word sp=verb

        This finds nominal clauses containing a predicate phrase with a verb.
        Indentation indicates nesting (parent contains child).
        """
        A = self._ensure_loaded(corpus)
        api = A.api
        feat_map = WORD_FEATURES.get(corpus, WORD_FEATURES["hebrew"])

        wtype = WORD_TYPE.get(corpus, "word")

        results = A.search(template)

        output = []
        for result_tuple in results[:limit]:
            entry: dict[str, Any] = {"objects": []}
            for node in result_tuple:
                otype = api.F.otype.v(node)
                section = api.T.sectionFromNode(node)
                obj: dict[str, Any] = {
                    "type": otype,
                    "book": section[0] if len(section) > 0 else "",
                    "chapter": section[1] if len(section) > 1 else 0,
                    "verse": section[2] if len(section) > 2 else 0,
                    "text": api.T.text(node),
                }
                if otype == wtype:
                    obj["word"] = self._word_info(api, node, feat_map).model_dump()
                else:
                    # Collect features for non-word objects
                    features = {}
                    for feat_name in sorted(api.Fall()):
                        val = api.Fs(feat_name).v(node)
                        if val is not None:
                            features[feat_name] = str(val)
                    obj["features"] = features
                entry["objects"].append(obj)
            output.append(entry)

        return output

    def get_lexeme_info(
        self,
        lexeme: str,
        corpus: str = "hebrew",
        limit: int = 50,
    ) -> dict:
        """Look up a lexeme and return its occurrences with context."""
        A = self._ensure_loaded(corpus)
        api = A.api
        feat_map = WORD_FEATURES.get(corpus, WORD_FEATURES["hebrew"])

        lex_feat = feat_map.get("lexeme", "lex")
        gloss_feat = feat_map.get("gloss", "gloss")
        sp_feat = feat_map.get("part_of_speech", "sp")
        lex_utf8_feat = feat_map.get("lexeme_utf8", "lex_utf8")

        # Use TF search for efficient lexeme lookup
        wtype = WORD_TYPE.get(corpus, "word")
        template = f"{wtype} {lex_feat}={lexeme}\n"
        results = A.search(template)
        corpus_count = len(results)

        first_gloss = ""
        first_sp = ""
        first_utf8 = ""
        matches = []

        for result_tuple in results[:limit]:
            w = result_tuple[0]

            if not first_gloss and gloss_feat:
                g = api.Fs(gloss_feat).v(w)
                if g:
                    first_gloss = str(g)
            if not first_sp and sp_feat:
                s = api.Fs(sp_feat).v(w)
                if s:
                    first_sp = str(s)
            if not first_utf8 and lex_utf8_feat:
                u = api.Fs(lex_utf8_feat).v(w)
                if u:
                    first_utf8 = str(u)

            section = api.T.sectionFromNode(w)
            matches.append(
                {
                    "book": section[0],
                    "chapter": section[1],
                    "verse": section[2],
                    "word": self._word_info(api, w, feat_map).model_dump(),
                }
            )

        return {
            "lexeme": lexeme,
            "lexeme_utf8": first_utf8,
            "gloss": first_gloss,
            "part_of_speech": first_sp,
            "total_occurrences": corpus_count,
            "occurrences": matches,
        }

    def get_vocabulary(
        self,
        book: str,
        chapter: int,
        verse_start: int = 1,
        verse_end: int | None = None,
        corpus: str = "hebrew",
    ) -> list[dict]:
        """Get unique lexemes in a passage with frequency and gloss."""
        A = self._ensure_loaded(corpus)
        api = A.api
        feat_map = WORD_FEATURES.get(corpus, WORD_FEATURES["hebrew"])

        if verse_end is None:
            verse_end = verse_start

        wtype = WORD_TYPE.get(corpus, "word")
        lexemes: dict[str, dict] = {}

        for v in range(verse_start, verse_end + 1):
            verse_node = api.T.nodeFromSection((book, chapter, v))
            if verse_node is None:
                continue
            for w in api.L.d(verse_node, otype=wtype):
                lex_feat = feat_map.get("lexeme", "lex")
                lex = api.Fs(lex_feat).v(w) or ""
                if not lex or lex in lexemes:
                    if lex in lexemes:
                        lexemes[lex]["count"] += 1
                    continue

                gloss_feat = feat_map.get("gloss", "gloss")
                gloss_val = api.Fs(gloss_feat).v(w) if gloss_feat else None

                sp_feat = feat_map.get("part_of_speech", "sp")
                sp_val = api.Fs(sp_feat).v(w) if sp_feat else None

                lex_utf8_feat = feat_map.get("lexeme_utf8", "lex_utf8")
                lex_utf8_val = api.Fs(lex_utf8_feat).v(w) if lex_utf8_feat else None

                freq_feat = "freq_lex"
                freq_val = None
                try:
                    freq_val = api.Fs(freq_feat).v(w)
                except Exception:
                    pass

                lexemes[lex] = {
                    "lexeme": lex,
                    "lexeme_utf8": str(lex_utf8_val) if lex_utf8_val else "",
                    "gloss": str(gloss_val) if gloss_val else "",
                    "part_of_speech": str(sp_val) if sp_val else "",
                    "corpus_frequency": int(freq_val) if freq_val else 0,
                    "count": 1,
                }

        return sorted(
            lexemes.values(), key=lambda x: x["corpus_frequency"], reverse=True
        )

    def _word_info(self, api: Any, w: int, feat_map: dict[str, str]) -> WordInfo:
        """Extract word features into a WordInfo model."""

        def _get(canonical: str) -> str:
            tf_name = feat_map.get(canonical, "")
            if not tf_name:
                return ""
            val = api.Fs(tf_name).v(w)
            return str(val) if val is not None else ""

        return WordInfo(
            monad=w,
            text=_get("text"),
            trailer=_get("trailer"),
            lexeme=_get("lexeme"),
            lexeme_utf8=_get("lexeme_utf8"),
            gloss=_get("gloss"),
            part_of_speech=_get("part_of_speech"),
            gender=_get("gender"),
            number=_get("number"),
            person=_get("person"),
            state=_get("state"),
            verbal_stem=_get("verbal_stem"),
            verbal_tense=_get("verbal_tense"),
            language=_get("language"),
        )
