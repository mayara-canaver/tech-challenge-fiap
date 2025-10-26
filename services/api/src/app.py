from flask import Flask, jsonify, request, redirect, url_for
import pandas as pd
import os
from datetime import timedelta
from dotenv import load_dotenv
from flask_jwt_extended import (
    JWTManager, create_access_token, create_refresh_token,
    jwt_required, get_jwt
)
from services.api.utils.helpers import load_books_df, project_list, dataset_path, REQUIRED_COLS
from flask_cors import CORS

load_dotenv()

def create_app() -> Flask:
    app = Flask(__name__)

    # Configurações JWT
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET")
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=30)
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=7)
    jwt = JWTManager(app)

    ADMIN_USER = os.getenv("ADMIN_USER")
    ADMIN_PASS = os.getenv("ADMIN_PASS")

    def is_valid_user(username: str, password: str) -> bool:
        # MVP: 1 usuário admin via env. Se quiser, dá pra expandir p/ várias contas.
        return username == ADMIN_USER and password == ADMIN_PASS

    def assert_admin():
        claims = get_jwt()
        if claims.get("role") != "admin":
            # 403 sem permissão
            return jsonify({"msg": "admin only"}), 403
        return None
    
    @app.post("/api/v1/auth/login")
    def auth_login():
        data = request.get_json(silent=True) or {}
        username = (data.get("username") or "").strip()
        password = (data.get("password") or "").strip()
        if not is_valid_user(username, password):
            return jsonify({"msg": "credenciais inválidas"}), 401

        additional_claims = {"role": "admin", "username": username}
        access_token = create_access_token(identity=username, additional_claims=additional_claims)
        refresh_token = create_refresh_token(identity=username, additional_claims=additional_claims)
        return jsonify({"access_token": access_token, "refresh_token": refresh_token})

    @app.post("/api/v1/auth/refresh")
    @jwt_required(refresh=True)
    def auth_refresh():
        claims = get_jwt()
        username = claims.get("sub")
        additional_claims = {"role": claims.get("role", "user"), "username": username}
        new_access = create_access_token(identity=username, additional_claims=additional_claims)
        return jsonify({"access_token": new_access})

    @app.post("/api/v1/scraping/trigger")
    @jwt_required()  # precisa de access token
    def trigger_scraping():
        # exige admin
        not_admin = assert_admin()
        if not_admin:
            return not_admin

        # Aqui você pode acionar o scraper/clean via subprocess se quiser.
        # Para segurança do desafio, vou só retornar 202 com stub.
        # (Se quiser rodar de verdade, descomente o bloco abaixo.)
        return jsonify({"msg": "trigger recebido (stub). Em produção chamaria o job ETL."}), 202

    @app.get("/api/v1/health")
    def health():
        df = load_books_df()
        path = dataset_path()
        ok = (df is not None) and (not df.empty) and REQUIRED_COLS.issubset(set(df.columns))
        details = {
            "dataset_path": str(path),
            "exists": path.exists(),
            "rows": 0 if df is None else int(len(df)),
            "columns_present": [] if df is None else sorted(df.columns.tolist()),
            "columns_required_ok": ok,
        }
        return jsonify({"status": "ok" if ok else "degraded", "details": details}), (200 if ok else 503)

    @app.get("/api/v1/books")
    def list_books():
        df = load_books_df()
        if df is None or df.empty:
            return jsonify({"error": "dataset indisponível"}), 503

        # Filtros opcionais (não obrigatórios, mas úteis): ?q= & paginação
        q    = request.args.get("q")
        page = int(request.args.get("page", 1))
        size = int(request.args.get("size", 20))
        start = max((page - 1) * size, 0)

        dfl = df
        if q and "title" in dfl.columns:
            dfl = dfl[dfl["title"].str.contains(q, case=False, na=False)]

        dfl = project_list(dfl).sort_values(["title", "id"], ascending=[True, True], kind="stable")
        total = int(len(dfl))
        items = dfl.iloc[start:start + size].to_dict(orient="records")
        return jsonify({"items": items, "page": page, "size": size, "total": total})

    @app.get("/api/v1/books/<string:book_id>")
    def book_detail(book_id: str):
        df = load_books_df()
        if df is None or df.empty:
            return jsonify({"error": "dataset indisponível"}), 503
        hit = df[df["id"] == book_id]
        if hit.empty:
            return jsonify({"error": f"book id '{book_id}' não encontrado"}), 404
        return jsonify(hit.iloc[0].to_dict())

    @app.get("/api/v1/books/search")
    def search_books():
        df = load_books_df()
        if df is None or df.empty:
            return jsonify({"error": "dataset indisponível"}), 503

        title    = request.args.get("title")
        category = request.args.get("category")
        page     = int(request.args.get("page", 1))
        size     = int(request.args.get("size", 20))
        start    = max((page - 1) * size, 0)

        dfl = df
        if title and "title" in dfl.columns:
            dfl = dfl[dfl["title"].str.contains(title, case=False, na=False)]
        if category and "category" in dfl.columns:
            dfl = dfl[dfl["category"].str.contains(category, case=False, na=False)]

        dfl = project_list(dfl).sort_values(["title", "id"], ascending=[True, True], kind="stable")
        total = int(len(dfl))
        items = dfl.iloc[start:start + size].to_dict(orient="records")
        return jsonify({"items": items, "page": page, "size": size, "total": total})

    @app.get("/api/v1/categories")
    def list_categories():
        df = load_books_df()
        if df is None or df.empty:
            return jsonify({"error": "dataset indisponível"}), 503
        if "category" not in df.columns:
            return jsonify({"items": [], "total": 0})
        cats = (
            df["category"]
            .fillna("")
            .astype(str)
            .str.strip()
            .replace("", pd.NA)
            .dropna()
            .drop_duplicates()
            .sort_values()
            .tolist()
        )
        return jsonify({"items": cats, "total": len(cats)})

    @app.get("/api/v1/books/price-range")
    def books_price_range():
        df = load_books_df()
        if df is None or df.empty:
            return jsonify({"error": "dataset indisponível"}), 503

        min_q = request.args.get("min")
        max_q = request.args.get("max")

        try:
            min_val = float(min_q) if min_q is not None else float("-inf")
            max_val = float(max_q) if max_q is not None else float("inf")
        except ValueError:
            return jsonify({"error": "parâmetros 'min' e 'max' devem ser numéricos"}), 400

        if min_val > max_val:
            return jsonify({"error": "'min' não pode ser maior que 'max'"}), 400

        dff = df[df["price"].notna() & (df["price"].between(min_val, max_val, inclusive="both"))]

        page = int(request.args.get("page", 1))
        size = int(request.args.get("size", 20))
        start = max((page - 1) * size, 0)

        dfl = project_list(dff).sort_values(["price","title","id"], ascending=[True, True, True], kind="stable")
        total = int(len(dfl))
        items = dfl.iloc[start:start + size].to_dict(orient="records")

        return jsonify({
            "filters": {"min": None if min_q is None else min_val, "max": None if max_q is None else max_val},
            "items": items,
            "page": page,
            "size": size,
            "total": total
        })
    
    @app.get("/api/v1/books/top-rated")
    def top_rated_books():
        df = load_books_df()
        if df is None or df.empty:
            return jsonify({"error": "dataset indisponível"}), 503

        # parâmetros
        min_rating = int(request.args.get("min_rating", 4))
        limit      = int(request.args.get("limit", 10))
        category   = request.args.get("category")

        # filtro por rating e categoria (se informado)
        dff = df[df["rating"].fillna(0) >= min_rating]
        if category and "category" in dff.columns:
            dff = dff[dff["category"].str.contains(category, case=False, na=False)]

        # ordena: rating desc, depois título/id para desempatar
        dfl = project_list(dff).sort_values(
            ["rating", "title", "id"],
            ascending=[False, True, True],
            kind="stable"
        )

        total = int(len(dfl))
        items = dfl.head(max(0, limit)).to_dict(orient="records")

        return jsonify({
            "filters": {"min_rating": min_rating, "limit": limit, "category": category},
            "items": items,
            "total": total
        })

    @app.get("/api/v1/stats/categories")
    def stats_categories():
        """
        Estatísticas por categoria:
        - books: quantidade de livros
        - price_min, price_max, price_mean, price_median (apenas onde houver price)
        Params opcionais:
          - min_count (int, default 1): filtra categorias com pelo menos N livros
          - sort (str, default 'books'): books|price_mean|price_median|price_min|price_max
          - order (str, default 'desc'): asc|desc
        """
        df = load_books_df()
        if df is None or df.empty:
            return jsonify({"error": "dataset indisponível"}), 503
        if "category" not in df.columns or "price" not in df.columns:
            return jsonify({"error": "dataset sem colunas necessárias (category/price)"}), 400

        # Considera apenas linhas com preço para métricas de preço;
        # a contagem de livros usa todos (com ou sem preço).
        # Para contar todos, calculamos duas agregações e fazemos merge.
        cnt = (
            df.groupby("category", dropna=False)
              .agg(books=("id", "nunique"))
              .reset_index()
        )

        price_df = df[df["price"].notna()]
        if not price_df.empty:
            metrics = (
                price_df.groupby("category", dropna=False)
                        .agg(price_min=("price", "min"),
                             price_max=("price", "max"),
                             price_mean=("price", "mean"),
                             price_median=("price", "median"))
                        .reset_index()
            )
            out = cnt.merge(metrics, on="category", how="left")
        else:
            # sem nenhum price válido
            out = cnt.assign(price_min=pd.NA, price_max=pd.NA,
                             price_mean=pd.NA, price_median=pd.NA)

        # Filtros e ordenação
        min_count = int(request.args.get("min_count", 1))
        sort = request.args.get("sort", "books")
        order = request.args.get("order", "desc")
        allowed_sort = {"books", "price_min", "price_max", "price_mean", "price_median"}
        if sort not in allowed_sort:
            sort = "books"
        ascending = (order == "asc")

        out = out[out["books"] >= min_count]

        # Substitui NaN de categoria por 'unknown' para responder em JSON
        out["category"] = out["category"].fillna("unknown")

        out = out.sort_values(sort, ascending=ascending, kind="stable")

        # Totais
        total_categories = int(out["category"].nunique())
        total_books = int(cnt["books"].sum())

        items = out.to_dict(orient="records")
        return jsonify({
            "total_categories": total_categories,
            "total_books": total_books,
            "min_count": min_count,
            "sorted_by": sort,
            "order": "asc" if ascending else "desc",
            "items": items
        })

    @app.get("/api/v1/stats/overview")
    def stats_overview():
        df = load_books_df()
        if df is None or df.empty:
            return jsonify({"error": "dataset indisponível"}), 503

        total_books = int(len(df))

        # categorias (ignora nulos/vazios)
        if "category" in df.columns:
            cats = df["category"].fillna("").astype(str).str.strip()
            total_categories = int(cats.replace("", pd.NA).dropna().nunique())
        else:
            total_categories = 0

        # preços (considera apenas price não nulo)
        price_stats = {"count": 0, "min": None, "max": None, "mean": None, "median": None}
        if "price" in df.columns:
            p = df["price"].dropna()
            if not p.empty:
                price_stats = {
                    "count": int(len(p)),
                    "min": float(p.min()),
                    "max": float(p.max()),
                    "mean": float(p.mean()),
                    "median": float(p.median()),
                }

        # distribuição de ratings (0..5) – garante todas as classes
        rating_dist = {"counts": {}, "percents": {}}
        if "rating" in df.columns:
            r = pd.to_numeric(df["rating"], errors="coerce").fillna(0).astype(int).clip(0, 5)
            for k in range(0, 6):
                cnt = int((r == k).sum())
                rating_dist["counts"][str(k)] = cnt
                rating_dist["percents"][str(k)] = round((cnt / total_books) * 100, 2) if total_books else 0.0

        return jsonify({
            "total_books": total_books,
            "total_categories": total_categories,
            "price": price_stats,
            "rating_distribution": rating_dist
        })

    return app

if __name__ == "__main__":
    app = create_app()
    CORS(app)
    app.run(host="127.0.0.1", port=5000, debug=True)
