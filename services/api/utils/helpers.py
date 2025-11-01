# services/api/utils/helpers.py
from pathlib import Path
import pandas as pd
from typing import Optional

# Raiz do repo (utils -> api -> services -> repo root)
REPO_ROOT = Path(__file__).resolve().parents[3]

# Arquivos de dados (preferimos Parquet se existir; caso contrário CSV)
PARQUET_PATH = (REPO_ROOT / "data" / "silver" / "books.parquet").resolve()
CSV_PATH     = (REPO_ROOT / "data" / "silver" / "books.csv").resolve()

# Esquema esperado na silver (pós-clean_books)
REQUIRED_COLS = {
    "id", "title", "category", "price", "rating",
    "instock", "UPC", "product_url", "image_url", "image_path"
}
OPTIONAL_COLS = {"book_title"}  # compatibilidade se você manteve

def load_books_df() -> Optional[pd.DataFrame]:
    """Lê a silver já tratada (Parquet se disponível, senão CSV). Nenhuma limpeza aqui."""
    path = PARQUET_PATH if PARQUET_PATH.exists() else CSV_PATH
    if not path.exists():
        return None

    if path.suffix == ".parquet":
        df = pd.read_parquet(path)
    else:
        # dtypes estáveis para CSV
        dtypes = {
            "id": "string",
            "title": "string",
            "book_title": "string",
            "category": "string",
            "UPC": "string",
            "product_url": "string",
            "image_url": "string",
            "image_path": "string",
        }
        df = pd.read_csv(path, dtype=dtypes, encoding="utf-8")

        # numéricos conforme silver
        if "price" in df.columns:
            df["price"] = pd.to_numeric(df["price"], errors="coerce")
        if "rating" in df.columns:
            df["rating"] = pd.to_numeric(df["rating"], errors="coerce").fillna(0).astype(int)
        if "instock" in df.columns:
            # pandas nullable int
            try:
                df["instock"] = pd.to_numeric(df["instock"], errors="coerce").astype("Int64")
            except Exception:
                pass

    return df

def project_list(df: pd.DataFrame) -> pd.DataFrame:
    """Projeção de colunas para listagens e busca."""
    cols_pref = [
        "id", "title", "category", "price", "rating",
        "product_url", "image_url", "image_path"
    ]
    cols = [c for c in cols_pref if c in df.columns]
    return df[cols].copy()

def dataset_path() -> Path:
    """Retorna o caminho real usado pelo loader (útil para /health)."""
    #return PARQUET_PATH if PARQUET_PATH.exists() else CSV_PATH
    return CSV_PATH

def _cat_index_map(df: pd.DataFrame, col: str) -> dict:
    cats = (
        df[col].fillna("")
        .astype(str).str.strip()
        .replace("", pd.NA).dropna()
        .drop_duplicates().sort_values()
        .tolist()
    )
    return {c: i for i, c in enumerate(cats)}

def build_ml_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Constrói features ML-ready:
      - id (string)
      - price (float)
      - rating (int)
      - category_idx (int codificado)
      - title_len (int: número de caracteres)
      - title_tok (int: número de tokens por espaço)
      - has_image (0/1)
    """
    d = df.copy()

    d["title"] = d["title"].fillna("").astype(str)
    d["category"] = d["category"].fillna("").astype(str)

    cat2idx = _cat_index_map(d, "category")
    d["category_idx"] = d["category"].map(cat2idx).fillna(-1).astype(int)

    d["title_len"] = d["title"].str.len().fillna(0).astype(int)
    d["title_tok"] = d["title"].str.split().map(len).fillna(0).astype(int)

    d["has_image"] = d["image_path"].notna().astype(int) if "image_path" in d.columns else 0

    cols = ["id", "price", "rating", "category_idx", "title_len", "title_tok", "has_image"]
    # garante existência
    for c in cols:
        if c not in d.columns:
            d[c] = 0
    return d[cols]
