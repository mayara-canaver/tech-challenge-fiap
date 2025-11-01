from flask import Flask, jsonify, request, redirect
import pandas as pd
import os
from datetime import timedelta
from dotenv import load_dotenv
from pathlib import Path
import json
import time
from flask_jwt_extended import (
    JWTManager, create_access_token, create_refresh_token,
    jwt_required, get_jwt, get_jwt_identity
)
from services.api.utils.helpers import load_books_df, project_list, dataset_path, REQUIRED_COLS
from flask_cors import CORS
from flasgger import Swagger

load_dotenv()

def create_app() -> Flask:
    app = Flask(__name__)

    # --- Configuração do Swagger (Flasgger) ---
    app.config['SWAGGER'] = {
        'title': 'API Pública de Livros - Tech Challenge',
        'uiversion': 3,
        'description': 'API para consulta de dados de livros, com endpoints de insights e autenticação JWT.',
        'version': '1.0.0',
        'contact': {
            'name': 'Nome do Desenvolvedor',
            'email': 'seu.email@exemplo.com',
        },
        'specs_route': '/apidocs/'
    }

    # Definição de segurança para JWT no Swagger
    template = app.config['SWAGGER']
    template['securityDefinitions'] = {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header',
            'description': 'Token de acesso JWT. Formato: "Bearer <token>"'
        }
    }
    # Inicializa o Swagger
    swagger = Swagger(app, template=template)
    # --------------------------------------------

    # Configurações JWT
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET", "default-super-secret-key")
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=30)
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=7)
    jwt = JWTManager(app)

    ADMIN_USER = os.getenv("ADMIN_USER")
    ADMIN_PASS = os.getenv("ADMIN_PASS")

    def is_valid_user(username: str, password: str) -> bool:
        return username == ADMIN_USER and password == ADMIN_PASS

    def assert_admin():
        claims = get_jwt()
        if claims.get("role") != "admin":
            return jsonify({"msg": "admin only"}), 403
        return None
    
    # --- Endpoints ---

    @app.get("/")
    def root_redirect():
        """
        Redireciona para a documentação.
        Este endpoint redireciona a raiz (/) para a interface do Swagger UI (/apidocs/).
        ---
        tags:
          - Status
        responses:
          302:
            description: Redirecionamento para /apidocs/
        """
        return redirect('/apidocs/')

    @app.post("/api/v1/auth/login")
    def auth_login():
        """
        Autentica um usuário e retorna tokens JWT.
        Recebe um JSON com "username" e "password". Se as credenciais (definidas nas
        variáveis de ambiente) estiverem corretas, retorna um access_token e um refresh_token.
        ---
        tags:
          - Autenticação
        parameters:
          - in: body
            name: body
            required: true
            schema:
              type: object
              properties:
                username:
                  type: string
                  example: "admin"
                password:
                  type: string
                  example: "admin123"
        responses:
          200:
            description: Login bem-sucedido.
            schema:
              type: object
              properties:
                access_token:
                  type: string
                refresh_token:
                  type: string
          401:
            description: Credenciais inválidas.
        """
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
        """
        Atualiza um access_token expirado.
        Este endpoint requer um 'refresh_token' válido no header 'Authorization'.
        Ele retorna um novo 'access_token'.
        ---
        tags:
          - Autenticação
        security:
          - Bearer: []
        responses:
          200:
            description: Token atualizado com sucesso.
            schema:
              type: object
              properties:
                access_token:
                  type: string
          401:
            description: Refresh token inválido ou ausente.
        """
        claims = get_jwt()
        username = claims.get("sub")
        additional_claims = {"role": claims.get("role", "user"), "username": username}
        new_access = create_access_token(identity=username, additional_claims=additional_claims)
        return jsonify({"access_token": new_access})

    @app.post("/api/v1/scraping/trigger")
    @jwt_required()
    def trigger_scraping():
        """
        [Admin] Aciona o processo de web scraping (stub).
        Este é um endpoint protegido que (em produção) acionaria o pipeline
        de ETL (scrape + clean). Requer um access_token de admin.
        ---
        tags:
          - Admin
        security:
          - Bearer: []
        responses:
          202:
            description: Trigger recebido e job (stub) iniciado.
          401:
            description: Token de acesso ausente ou inválido.
          403:
            description: Acesso negado (usuário não é admin).
        """
        not_admin = assert_admin()
        if not_admin:
            return not_admin
        
        return jsonify({"msg": "trigger recebido (stub). Em produção chamaria o job ETL."}), 202

    @app.get("/api/v1/health")
    def health():
        """
        Verifica a saúde da API e a disponibilidade dos dados.
        Retorna o status da API e detalhes sobre o dataset carregado (caminho, 
        número de linhas, colunas presentes e se as colunas obrigatórias existem).
        ---
        tags:
          - Status
        responses:
          200:
            description: API operacional e dados carregados.
            schema:
              type: object
              properties:
                status:
                  type: string
                  example: "ok"
                details:
                  type: object
          503:
            description: API operacional, mas os dados estão degradados ou ausentes.
            schema:
              type: object
              properties:
                status:
                  type: string
                  example: "degraded"
                details:
                  type: object
        """
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
        """
        Lista todos os livros (paginado).
        Retorna uma lista paginada de livros. Permite filtrar por um termo
        de busca 'q' (que busca no título).
        ---
        tags:
          - Livros (Core)
        parameters:
          - name: q
            in: query
            type: string
            required: false
            description: Termo de busca para filtrar por título (case-insensitive).
          - name: page
            in: query
            type: integer
            required: false
            default: 1
            description: Número da página.
          - name: size
            in: query
            type: integer
            required: false
            default: 20
            description: Número de itens por página.
        responses:
          200:
            description: Lista de livros retornada com sucesso.
          503:
            description: Dataset indisponível.
        """
        df = load_books_df()
        if df is None or df.empty:
            return jsonify({"error": "dataset indisponível"}), 503

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
        """
        Busca detalhes de um livro específico por ID.
        Retorna todos os campos de um único livro baseado no seu ID.
        ---
        tags:
          - Livros (Core)
        parameters:
          - name: book_id
            in: path
            type: string
            required: true
            description: O ID (ou UPC) do livro.
        responses:
          200:
            description: Detalhes do livro.
          404:
            description: Livro não encontrado.
          503:
            description: Dataset indisponível.
        """
        df = load_books_df()
        if df is None or df.empty:
            return jsonify({"error": "dataset indisponível"}), 503
        hit = df[df["id"] == book_id]
        if hit.empty:
            return jsonify({"error": f"book id '{book_id}' não encontrado"}), 404
        return jsonify(hit.iloc[0].to_dict())

    @app.get("/api/v1/books/search")
    def search_books():
        """
        Busca livros por título e/ou categoria (paginado).
        Endpoint obrigatório. Retorna livros filtrando por 'title' (substring,
        case-insensitive) e/ou 'category' (substring, case-insensitive).
        ---
        tags:
          - Livros (Core)
        parameters:
          - name: title
            in: query
            type: string
            required: false
            description: Termo de busca para filtrar por título (case-insensitive).
          - name: category
            in: query
            type: string
            required: false
            description: Termo de busca para filtrar por categoria (case-insensitive).
          - name: page
            in: query
            type: integer
            required: false
            default: 1
            description: Número da página.
          - name: size
            in: query
            type: integer
            required: false
            default: 20
            description: Número de itens por página.
        responses:
          200:
            description: Lista de livros filtrada.
          503:
            description: Dataset indisponível.
        """
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
        """
        Lista todas as categorias de livros únicas.
        Retorna uma lista ordenada de todas as categorias únicas presentes no dataset.
        ---
        tags:
          - Livros (Core)
        responses:
          200:
            description: Lista de categorias.
            schema:
              type: object
              properties:
                items:
                  type: array
                  items:
                    type: string
                total:
                  type: integer
          503:
            description: Dataset indisponível.
        """
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
        """
        [Insights] Filtra livros por faixa de preço.
        Retorna livros cujo preço está entre 'min' e 'max' (inclusivo).
        ---
        tags:
          - Livros (Insights)
        parameters:
          - name: min
            in: query
            type: number
            required: false
            description: Preço mínimo.
          - name: max
            in: query
            type: number
            required: false
            description: Preço máximo.
          - name: page
            in: query
            type: integer
            required: false
            default: 1
          - name: size
            in: query
            type: integer
            required: false
            default: 20
        responses:
          200:
            description: Lista de livros filtrada por preço.
          400:
            description: Parâmetros 'min' ou 'max' inválidos.
          503:
            description: Dataset indisponível.
        """
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
        """
        [Insights] Lista os livros com melhor avaliação.
        Retorna livros com 'rating' maior ou igual a 'min_rating'.
        ---
        tags:
          - Livros (Insights)
        parameters:
          - name: min_rating
            in: query
            type: integer
            required: false
            default: 4
            description: Rating mínimo (de 0 a 5).
          - name: limit
            in: query
            type: integer
            required: false
            default: 10
            description: Número máximo de livros a retornar.
          - name: category
            in: query
            type: string
            required: false
            description: Filtra por categoria (substring, case-insensitive).
        responses:
          200:
            description: Lista de livros com melhor avaliação.
          503:
            description: Dataset indisponível.
        """
        df = load_books_df()
        if df is None or df.empty:
            return jsonify({"error": "dataset indisponível"}), 503

        min_rating = int(request.args.get("min_rating", 4))
        limit      = int(request.args.get("limit", 10))
        category   = request.args.get("category")

        dff = df[df["rating"].fillna(0) >= min_rating]
        if category and "category" in dff.columns:
            dff = dff[dff["category"].str.contains(category, case=False, na=False)]

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
        [Insights] Estatísticas detalhadas por categoria.
        Retorna contagem de livros e estatísticas de preço (min, max, mean, median)
        agrupadas por categoria.
        ---
        tags:
          - Estatísticas
        parameters:
          - name: min_count
            in: query
            type: integer
            required: false
            default: 1
            description: Filtra categorias com pelo menos N livros.
          - name: sort
            in: query
            type: string
            required: false
            default: "books"
            enum: ["books", "price_mean", "price_median", "price_min", "price_max"]
            description: Coluna para ordenação.
          - name: order
            in: query
            type: string
            required: false
            default: "desc"
            enum: ["asc", "desc"]
            description: Ordem de classificação.
        responses:
          200:
            description: Estatísticas por categoria.
          503:
            description: Dataset indisponível.
        """
        df = load_books_df()
        if df is None or df.empty:
            return jsonify({"error": "dataset indisponível"}), 503
        if "category" not in df.columns or "price" not in df.columns:
            return jsonify({"error": "dataset sem colunas necessárias (category/price)"}), 400

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
            out = cnt.assign(price_min=pd.NA, price_max=pd.NA,
                             price_mean=pd.NA, price_median=pd.NA)

        min_count = int(request.args.get("min_count", 1))
        sort = request.args.get("sort", "books")
        order = request.args.get("order", "desc")
        allowed_sort = {"books", "price_min", "price_max", "price_mean", "price_median"}
        if sort not in allowed_sort:
            sort = "books"
        ascending = (order == "asc")

        out = out[out["books"] >= min_count]
        out["category"] = out["category"].fillna("unknown")
        out = out.sort_values(sort, ascending=ascending, kind="stable")

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
        """
        [Insights] Estatísticas gerais da coleção.
        Retorna totais de livros, categorias, estatísticas de preço 
        e a distribuição de ratings (0 a 5 estrelas).
        ---
        tags:
          - Estatísticas
        responses:
          200:
            description: Visão geral das estatísticas.
          503:
            description: Dataset indisponível.
        """
        df = load_books_df()
        if df is None or df.empty:
            return jsonify({"error": "dataset indisponível"}), 503

        total_books = int(len(df))

        if "category" in df.columns:
            cats = df["category"].fillna("").astype(str).str.strip()
            total_categories = int(cats.replace("", pd.NA).dropna().nunique())
        else:
            total_categories = 0

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
    
    # ========= ML-READY: FEATURES =========
    @app.get("/api/v1/ml/features")
    def ml_features():
        """
        Retorna features por livro (paginação opcional):
          - id, price, rating, category_idx, title_len, title_tok, has_image
        Params:
          - page, size
          - format=csv (opcional) -> retorna CSV
        """
        df = load_books_df()
        if df is None or df.empty:
            return jsonify({"error": "dataset indisponível"}), 503

        feats = build_ml_features(df)

        fmt = request.args.get("format", "json").lower()
        if fmt == "csv":
            # exporta tudo (ou pagina se preferir)
            csv = feats.to_csv(index=False)
            return app.response_class(csv, mimetype="text/csv")
        else:
            page = int(request.args.get("page", 1))
            size = int(request.args.get("size", 100))
            start = max((page - 1) * size, 0)
            total = int(len(feats))
            items = feats.iloc[start:start + size].to_dict(orient="records")
            return jsonify({"items": items, "page": page, "size": size, "total": total})

    # ========= ML-READY: TRAINING DATA =========
    @app.get("/api/v1/ml/training-data")
    def ml_training_data():
        """
        Retorna dataset de treino (features + alvo sintético)
        Alvo: target_high_rating = 1 se rating >= 4, senão 0.
        Params:
          - format=csv/json
        """
        df = load_books_df()
        if df is None or df.empty:
            return jsonify({"error": "dataset indisponível"}), 503

        feats = build_ml_features(df)
        feats["target_high_rating"] = (feats["rating"] >= 4).astype(int)

        fmt = request.args.get("format", "csv").lower()
        if fmt == "json":
            return jsonify({"items": feats.to_dict(orient="records"), "total": int(len(feats))})
        else:
            csv = feats.to_csv(index=False)
            return app.response_class(csv, mimetype="text/csv")
        
    # ========= ML-READY: RECEBIMENTO DE PREDIÇÕES =========
    # Forma de payload:
    # {
    #   "model": "nome_modelo_v1",
    #   "predictions": [
    #       {"id": "a-book-id", "y_pred": 0.87},
    #       {"id": "another-id", "y_pred": 0.12}
    #   ]
    # }
    ml_dir = (Path(__file__).resolve().parents[3] / "data" / "ml")
    ml_dir.mkdir(parents=True, exist_ok=True)

    @app.post("/api/v1/ml/predictions")
    def ml_predictions():
        """
        Recebe predições e persiste em JSONL (para avaliação posterior).
        Retorna contagem validada.
        """
        payload = request.get_json(silent=True) or {}
        model = (payload.get("model") or "").strip()
        preds = payload.get("predictions") or []

        if not model or not isinstance(preds, list) or not preds:
            return jsonify({"error": "payload inválido: informe 'model' e lista 'predictions'"}), 400

        # validações simples
        ok, bad = [], []
        for p in preds:
            bid = (p.get("id") or "").strip()
            y  = p.get("y_pred")
            if not bid:
                bad.append({"reason": "missing id", "item": p})
                continue
            try:
                y = float(y)
            except Exception:
                bad.append({"reason": "y_pred não numérico", "item": p})
                continue
            ok.append({"id": bid, "y_pred": y})

        # escreve JSONL com timestamp
        ts = time.strftime("%Y%m%d-%H%M%S")
        out_path = ml_dir / f"predictions_{model}_{ts}.jsonl"
        with open(out_path, "w", encoding="utf-8") as f:
            for r in ok:
                f.write(json.dumps({"model": model, **r}, ensure_ascii=False) + "\n")

        return jsonify({
            "model": model,
            "saved_file": str(out_path),
            "accepted": len(ok),
            "rejected": len(bad),
            "rejected_detail": bad[:5]  # limita retorno
        }), 202

    return app

if __name__ == "__main__":
    app = create_app()
    CORS(app) # Adiciona CORS para testes locais
    app.run(host="127.0.0.1", port=5000, debug=True)
    