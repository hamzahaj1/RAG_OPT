# [FILE] — scripts/rag_probe.py
"""Sonde RAG du jalon 13 — chunking par marqueurs, vectorisation, top-k.

Exécute le protocole figé de ``jalon13-constat.md`` (commit de
gouvernance) : découpe l'échantillon de 5 fichiers par les marqueurs du
Standard V3 — un chunk = un bloc ``# [RAG]`` + sa fonction, un bloc
``# [MODEL]``/``# [SCHEMA]`` = un chunk à lui seul, boilerplate
d'imports exclu via ``[CODE_START]`` (FR-016) — puis vectorise en local
(fastembed, modèle épinglé) et relève le top-k=5 par question :
score cosinus à 4 décimales, égalités signalées, critères binaires
évalués. Pas de base vectorielle, pas de framework RAG (R5) — l'index
est une matrice numpy en mémoire.

Depuis le relevé R3 (décision de gouvernance du 2026-08-28, piste 4) :
modèle ``intfloat/multilingual-e5-large`` avec les préfixes d'usage e5
``query:``/``passage:`` appliqués côté sonde — le corpus sur disque est
inchangé. Depuis le relevé R4 (amendement de protocole, CLAUDE.md
§4 ter) : questions en anglais — la langue des questions suit celle du
corpus, migré aux lots a–c.

La qualification des modules réutilise celle du module d'analyse
partagé (une seule définition de la notion).

Exécution : ``python -m scripts.rag_probe``.
"""

# ─── IMPORTS ───
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from fastembed import TextEmbedding

from scripts.corpus_analysis import _module_qualified

# ──────────────

# [CODE_START]

CODE_START_MARKER: str = "# [CODE_START]"

EMBEDDING_MODEL: str = "intfloat/multilingual-e5-large"

PASSAGE_PREFIX: str = "passage: "

QUERY_PREFIX: str = "query: "

QUESTIONS: tuple[tuple[str, str], ...] = (
    ("Q1", "what happens when a user is deleted?"),
    ("Q2", "how does an HTTP request obtain a database session?"),
)

SAMPLE_FILES: tuple[str, ...] = (
    "app/domains/users/services.py",
    "app/domains/organizations/services.py",
    "app/core/database.py",
    "app/domains/users/router.py",
    "app/domains/users/models.py",
)

TOP_K: int = 5

_DEF_PATTERN: re.Pattern[str] = re.compile(r"^(?:async )?def (\w+)")


@dataclass(frozen=True)
class Chunk:
    """Unité d'indexation : identifiant protocolaire + texte vectorisé."""

    identifier: str
    text: str


def _chunk_code(module: str, lines: list[str]) -> list[Chunk]:
    """Chunks de code d'un fichier : un bloc [RAG] + sa fonction chacun.

    Règles (protocole) : le chunk court du marqueur ``# [RAG]`` au dernier
    contenu avant le bloc suivant (ou la fin du fichier) ; tout ce qui
    précède ``[CODE_START]`` — imports, en-tête, docstring de module —
    n'entre dans aucun chunk (FR-016).
    """
    # ─── VARIABLE DECLARATION ZONE ───
    chunks: list[Chunk]
    code_start: int
    name: str
    starts: list[int]
    stop: int
    # ─────────────────────────────────

    # [STEP 1] Borner la zone de code et relever les blocs → ancrages des chunks
    code_start = lines.index(CODE_START_MARKER) if CODE_START_MARKER in lines else 0
    starts = [i for i in range(code_start, len(lines)) if lines[i] == "# [RAG]"]

    # [STEP 2] Découper de bloc en bloc → une fonction et son en-tête par chunk
    chunks = []
    for position, start in enumerate(starts):
        stop = starts[position + 1] if position + 1 < len(starts) else len(lines)
        name = next(
            (m.group(1) for line in lines[start:stop] if (m := _DEF_PATTERN.match(line))),
            "inconnu",
        )
        chunks.append(
            Chunk(
                identifier=f"{module}.{name} [RAG]",
                text="\n".join(lines[start:stop]).rstrip() + "\n",
            )
        )
    return chunks


def _chunk_metadata(module: str, lines: list[str]) -> list[Chunk]:
    """Chunks de métadonnées : chaque bloc [MODEL] ou [SCHEMA], seul.

    Règles (protocole) : identifiant ``<module>.<Entité> [MODEL]`` (champ
    ``entity`` du bloc) ou ``<module> [SCHEMA]`` ; le bloc est le chunk —
    le signal d'arêtes (``referenced_by``) voyage avec lui.
    """
    # ─── VARIABLE DECLARATION ZONE ───
    chunks: list[Chunk]
    close_index: int
    entity: str
    identifier: str
    kind: str
    # ─────────────────────────────────

    # [STEP 1] Balayer les paires de marqueurs → un chunk par bloc structurel
    chunks = []
    for index, line in enumerate(lines):
        if line not in ("# [MODEL]", "# [SCHEMA]"):
            continue
        kind = "MODEL" if line == "# [MODEL]" else "SCHEMA"
        close_index = lines.index(f"# [/{kind}]", index)
        entity = ""
        for item in lines[index:close_index]:
            if item.startswith("# entity: "):
                entity = item.removeprefix("# entity: ")
                break
        identifier = f"{module}.{entity} [MODEL]" if kind == "MODEL" else f"{module} [SCHEMA]"
        chunks.append(
            Chunk(identifier=identifier, text="\n".join(lines[index : close_index + 1]) + "\n")
        )
    return chunks


def _rank(matrix: np.ndarray, query: np.ndarray, chunks: list[Chunk]) -> list[tuple[float, str]]:
    """Top-k d'une question : similarité cosinus, tri déterministe.

    Règles (protocole) : k=5 ; score décroissant, départage par
    identifiant croissant (déterminisme) — les égalités à 4 décimales
    restent visibles dans le relevé.
    """
    # ─── VARIABLE DECLARATION ZONE ───
    ranked: list[tuple[float, str]]
    scores: np.ndarray
    # ─────────────────────────────────

    # [STEP 1] Noter chaque chunk et trier → top-k stable et reproductible
    scores = matrix @ query
    ranked = sorted(
        ((float(scores[i]), chunk.identifier) for i, chunk in enumerate(chunks)),
        key=lambda item: (-item[0], item[1]),
    )
    return ranked[:TOP_K]


def collect_chunks(root: Path) -> list[Chunk]:
    """Découpe l'échantillon figé du protocole en chunks, ordre des fichiers.

    Règles métier :
    - l'échantillon est la constante ``SAMPLE_FILES`` — toute évolution
      est une décision de gouvernance (protocole du constat) ;
    - un fichier sans bloc [RAG] par fonction (modèles) reste découpé
      correctement sur ses marqueurs de base (edge case de la spec).
    """
    # ─── VARIABLE DECLARATION ZONE ───
    chunks: list[Chunk]
    lines: list[str]
    module: str
    path: Path
    # ─────────────────────────────────

    # [STEP 1] Chunker chaque fichier de l'échantillon → code puis métadonnées
    chunks = []
    for relative in SAMPLE_FILES:
        path = root / relative
        lines = path.read_text(encoding="utf-8").splitlines()
        module = _module_qualified(root / "app", path)
        chunks.extend(_chunk_metadata(module, lines))
        chunks.extend(_chunk_code(module, lines))
    return chunks


def main() -> None:
    """Exécute la sonde : inventaire, relevés top-5, critères binaires.

    Règles métier (protocole figé, jalon13-constat.md) :
    - inventaire intégral avant tout relevé ;
    - relevé brut — rang, score à 4 décimales, identifiant — avant toute
      interprétation ; égalités signalées ;
    - critères binaires évalués tels que figés, jamais ajustés ici.
    """
    # ─── VARIABLE DECLARATION ZONE ───
    chunks: list[Chunk]
    crit_a: bool
    crit_b: bool
    matrix: np.ndarray
    model: TextEmbedding
    query: np.ndarray
    ranked: list[tuple[float, str]]
    rendered: list[str]
    top_ids: list[str]
    # ─────────────────────────────────

    # [STEP 1] Inventorier les chunks → comptage et identifiants intégraux
    chunks = collect_chunks(Path("."))
    print(f"Inventaire — {len(chunks)} chunks :")
    for chunk in chunks:
        print(f"  {chunk.identifier}")

    # [STEP 2] Vectoriser l'échantillon → matrice normalisée en mémoire
    model = TextEmbedding(EMBEDDING_MODEL)
    matrix = np.array(list(model.embed([PASSAGE_PREFIX + chunk.text for chunk in chunks])))
    matrix = matrix / np.linalg.norm(matrix, axis=1, keepdims=True)

    # [STEP 3] Relever chaque question → top-5 brut puis critères binaires
    for label, question in QUESTIONS:
        query = np.array(list(model.embed([QUERY_PREFIX + question])))[0]
        query = query / np.linalg.norm(query)
        ranked = _rank(matrix, query, chunks)
        print(f"\n{label} — « {question} »")
        rendered = [f"{score:.4f}" for score, _ in ranked]
        for rank, (score, identifier) in enumerate(ranked, start=1):
            tie = " (égalité)" if rendered.count(f"{score:.4f}") > 1 else ""
            print(f"  {rank}. {score:.4f}  {identifier}{tie}")
        top_ids = [identifier for _, identifier in ranked]
        if label == "Q1":
            crit_a = "users.services.delete_user [RAG]" in top_ids[:3]
            crit_b = "users.models.User [MODEL]" in top_ids
            print(f"  critère A (delete_user [RAG] top-3) : {crit_a}")
            print(f"  critère B (users [MODEL] top-5)      : {crit_b}")
        else:
            crit_a = "core.database.get_db [RAG]" in top_ids[:3]
            crit_b = any(i.startswith("users.router.") for i in top_ids)
            print(f"  critère A (get_db [RAG] top-3)       : {crit_a}")
            print(f"  critère B (endpoint Depends top-5)   : {crit_b}")


if __name__ == "__main__":
    main()
