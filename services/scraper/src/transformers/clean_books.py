# services/scraper/src/transformers/clean_books.py
# Fecha todo o tratamento/normalização na silver.
# Saída: data/silver/books.csv (UTF-8) e, se possível, books.parquet

from pathlib import Path
import re
import unicodedata
import pandas as pd

BRONZE_DIR = Path(__file__).resolve().parents[4] / "data" / "bronze"
SILVER_DIR = Path(__file__).resolve().parents[4] / "data" / "silver"
SILVER_DIR.mkdir(parents=True, exist_ok=True)

def _normalize_text(s: str) -> str:
    """minúsculas + ASCII + sem pontuação estranha + compacta espaços."""
    if pd.isna(s):
        return ""
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-z0-9 _-]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _coerce_price(x) -> float | None:
    """Converte '£51.77', 'R$ 1.234,56', 'Â£51,77' -> float, robusto a vírgula/ponto."""
    if pd.isna(x):
        return None
    s = str(x)
    # remove tudo que não for dígito, vírgula, ponto ou sinal
    s = re.sub(r"[^\d,.\-]", "", s)
    if not s:
        return None
    # regra dos separadores
    if "," in s and "." not in s:
        s = s.replace(",", ".")
    elif "," in s and "." in s:
        # último separador é decimal; o outro é milhar
        last_comma, last_dot = s.rfind(","), s.rfind(".")
        if last_comma > last_dot:
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    try:
        return float(s)
    except Exception:
        return None

def _pick_bronze_csv() -> Path:
    cands = list(BRONZE_DIR.glob("books*.csv"))
    if not cands:
        raise SystemExit(f"[ERRO] Nenhum CSV encontrado em {BRONZE_DIR} (esperado books*.csv).")
    cands.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return cands[0]

INPUT_CSV = _pick_bronze_csv()
print(f"[INFO] Lendo bronze: {INPUT_CSV}")

# --- leitura bronze (tipos flexíveis) ---
df = pd.read_csv(INPUT_CSV)
orig_rows = len(df)

# --- renomeações de compatibilidade ---
if "link" in df.columns and "product_url" not in df.columns:
    df = df.rename(columns={"link": "product_url"})

# --- normalizações finais (fechadas na silver) ---
# título -> 'title' normalizado (mantém 'book_title' se existir como referência)
if "book_title" in df.columns:
    df["book_title"] = df["book_title"].astype(str).map(_normalize_text)
    df["title"] = df["book_title"]
elif "title" in df.columns:
    df["title"] = df["title"].astype(str).map(_normalize_text)
else:
    # se não tiver nenhum, cria vazio (evita erro)
    df["title"] = ""

# categoria normalizada
if "category" in df.columns:
    df["category"] = df["category"].astype(str).map(_normalize_text)
else:
    df["category"] = ""

# preço final (float) -> 'price' a partir de 'raw_price' ou 'price'
if "raw_price" in df.columns:
    df["price"] = df["raw_price"].map(_coerce_price)
elif "price" in df.columns:
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
else:
    df["price"] = pd.NA

# rating int [0..5]
if "rating" in df.columns:
    df["rating"] = (
        pd.to_numeric(df["rating"], errors="coerce")
        .fillna(0)
        .astype(int)
        .clip(0, 5)
    )
else:
    df["rating"] = 0

# stock (se houver): número inteiro opcional
if "instock" in df.columns:
    try:
        df["instock"] = pd.to_numeric(df["instock"], errors="coerce").astype("Int64")
    except Exception:
        # se vier texto, deixa string
        df["instock"] = df["instock"].astype("string")
else:
    df["instock"] = pd.Series([pd.NA] * len(df), dtype="Int64")

# URL do produto
if "product_url" in df.columns:
    df["product_url"] = df["product_url"].astype("string").str.strip()
else:
    df["product_url"] = pd.Series([pd.NA] * len(df), dtype="string")

# imagens e UPC se existirem
for col in ("image_url", "image_path", "UPC"):
    if col in df.columns:
        df[col] = df[col].astype("string").str.strip()
    else:
        df[col] = pd.Series([pd.NA] * len(df), dtype="string")

# id como string
if "id" in df.columns:
    df["id"] = df["id"].astype("string").str.strip()
else:
    # fallback: derive de product_url se necessário
    if "product_url" in df.columns:
        df["id"] = (
            df["product_url"].fillna("").astype(str)
            .str.rsplit("/", n=1).str[-1]
            .str.replace(".html", "", regex=False)
            .astype("string")
        )
    else:
        df["id"] = pd.Series([pd.NA] * len(df), dtype="string")

# --- dedupe e ordenação estável ---
if "id" in df.columns and df["id"].notna().any():
    df = df.drop_duplicates(subset=["id"], keep="first")
else:
    df = df.drop_duplicates(subset=["title", "price"], keep="first")

# --- seleção e ordem final de colunas ---
final_cols = [
    "id",            # string
    "title",         # string normalizada
    "category",      # string normalizada
    "price",         # float64
    "rating",        # int64 (0..5)
    "instock",       # Int64 (pode ter NA)
    "UPC",           # string
    "product_url",   # string
    "image_url",     # string
    "image_path",    # string
]

# mantém 'book_title' apenas se existir (referência), mas não é necessária p/ API
if "book_title" in df.columns:
    final_cols.insert(2, "book_title")  # após 'title'

# garante existência das colunas
for c in final_cols:
    if c not in df.columns:
        df[c] = pd.NA

df = df[final_cols].reset_index(drop=True)

# --- tipos finais explícitos na silver ---
dtype_map = {
    "id": "string",
    "title": "string",
    "book_title": "string",
    "category": "string",
    "price": "float64",
    "rating": "int64",
    "instock": "Int64",
    "UPC": "string",
    "product_url": "string",
    "image_url": "string",
    "image_path": "string",
}
for col, dt in dtype_map.items():
    if col in df.columns:
        try:
            if dt == "Int64":  # pandas nullable int
                df[col] = pd.Series(df[col], dtype="Int64")
            else:
                df[col] = df[col].astype(dt)
        except Exception:
            pass  # se não conseguir, deixa como está para não quebrar

# --- salvar silver ---
out_csv     = SILVER_DIR / "books.csv"
out_parquet = SILVER_DIR / "books.parquet"

df.to_csv(out_csv, index=False, encoding="utf-8")  # UTF-8 sem BOM

parquet_ok, parquet_err = True, None
try:
    df.to_parquet(out_parquet, index=False)
except Exception as e:
    parquet_ok, parquet_err = False, e

print(f"[INFO] Linhas de entrada: {orig_rows} | Linhas de saída: {len(df)}")
print(f"[OK] CSV: {out_csv}")
print(f"[{'OK' if parquet_ok else 'WARN'}] Parquet: {out_parquet}{'' if parquet_ok else f' (falhou: {parquet_err})'}")
