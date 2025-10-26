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
