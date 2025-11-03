# Tech Challenge FIAP - API Pública de Livros

![Framework: Flask](https://img.shields.io/badge/Framework-Flask-blue)
![Deploy: Render](https://img.shields.io/badge/Deploy-Render-blueviolet)
![Python](https://img.shields.io/badge/Python-3.10%2B-green)
![Status](https://img.shields.io/badge/Status-Completo-brightgreen)

Este projeto é a solução para o Tech Challenge da pós-graduação em Machine Learning Engineering, com o objetivo de demonstrar um fluxo end-to-end de dados: desde o web scraping e ETL até a disponibilização dos dados via API RESTful e seu deploy em um ambiente de produção.

### Links de Referência

* **Link do Deploy (Produção):** [https://tech-challenge-fiap-no1e.onrender.com](https://tech-challenge-fiap-no1e.onrender.com)
* **Link do Vídeo de Apresentação:** `[https://drive.google.com/file/d/1JyQygetNez0KZ_wQ3TOa22CdmupJiNZk/view?usp=sharing]`
* **Link da Documentação (Swagger):** [https://tech-challenge-fiap-no1e.onrender.com/apidocs/](https://tech-challenge-fiap-no1e.onrender.com/apidocs/)

---

## 1. Descrição do Projeto e Arquitetura

### Descrição

Como primeiro desafio para um projeto de recomendação de livros, esta solução foca em construir o pipeline de dados fundamental. O objetivo é extrair dados de livros do site público `https://books.toscrape.com/`, processá-los e disponibilizá-los através de uma API RESTful pública, robusta e documentada (via Swagger/Flasgger), pronta para ser consumida por Cientistas de Dados e serviços de ML.

### Arquitetura do Pipeline

O pipeline de dados segue um fluxo ETL (Extract, Transform, Load) que alimenta a API, com uma clara separação entre as camadas de dados (Bronze e Silver):

1.  **Ingestão (Extract):** O script `services/scraper/src/extractors/scrape_books.py` realiza o web scraping do site, navegando por todas as categorias e páginas para extrair os dados brutos de cada livro.
2.  **Camada Bronze:** Os dados brutos extraídos são salvos em `data/bronze/books.csv`.
3.  **Processamento (Transform):** O script `services/scraper/src/transformers/clean_books.py` lê os dados da camada Bronze. Ele realiza a limpeza e normalização (conversão de preços, normalização de texto, tratamento de ratings).
4.  **Camada Silver (Load):** Os dados limpos e prontos para consumo são salvos em `data/silver/books.parquet`.
5.  **Disponibilização (API):** A API (Flask), definida em `services/api/src/app.py`, carrega o arquivo `books.parquet` da camada Silver para disponibilizar os dados através de endpoints RESTful.
6.  **Deploy:** A aplicação é configurada para deploy na plataforma Render através do arquivo `render.yaml`, que utiliza o Gunicorn como servidor WSGI.

### Diagrama da Arquitetura

```mermaid
graph TD
    subgraph "1. Ingestão (Web Scraping)"
        A[Site: books.toscrape.com] --> B(Script: scrape_books.py);
        B --> C[Salva em: data/bronze/books.csv];
    end

    subgraph "2. Processamento (Transform & Load)"
        C --> D(Script: clean_books.py);
        D --> E{Limpeza e Normalização};
        E --> F[Salva em: data/silver/books.parquet];
    end

    subgraph "3. Disponibilização (API RESTful)"
        F --> G(API Flask: app.py);
        G --> H{Carrega data/silver/books.parquet};
        H --> I[Endpoints RESTful: /api/v1/...];
    end

    subgraph "4. Deploy & Consumo"
        I --> J(Deploy: render.yaml);
        J --> K(Serviço Público no Render);
        K --> L["Consumidores (Cientistas de Dados, ML)"];
    end
````

-----

## 2\. Instruções de Instalação e Configuração

Para executar este projeto localmente, siga os passos abaixo.

**Pré-requisitos:**

  * Python 3.10+
  * Git

**Passos:**

1.  **Clone o repositório:**

    ```bash
    git clone [https://github.com/mayara-canaver/tech-challenge-1-fiap.git](https://github.com/mayara-canaver/tech-challenge-1-fiap.git)
    cd tech-challenge-1-fiap
    ```

2.  **Crie e ative um ambiente virtual:**

      * No macOS/Linux:
        ```bash
        python3 -m venv .venv
        source .venv/bin/activate
        ```
      * No Windows:
        ```bash
        python -m venv .venv
        .\.venv\Scripts\activate
        ```

3.  **Instale as dependências:**
    O arquivo `requirements.txt` contém todas as bibliotecas necessárias.

    ```bash
    pip install -r requirements.txt
    ```

4.  **Crie um arquivo `.env`:**
    A API utiliza variáveis de ambiente para configuração, principalmente para a segurança JWT. Crie um arquivo `.env` na raiz do projeto:

    ```.env
    # Chave secreta para o JWT (pode ser qualquer string segura)
    JWT_SECRET="************************"

    # Credenciais do usuário administrador da API
    ADMIN_USER="admin"
    ADMIN_PASS="*********"
    ```

-----

## 3\. Instruções de Execução

O projeto é dividido em duas etapas: a geração dos dados (ETL) e a execução da API.

### 1\. Executando o Pipeline de ETL

Antes de iniciar a API, é necessário executar os scripts de scraping e transformação para criar os arquivos de dados nas camadas Bronze e Silver.

```bash
# 1. Extrair dados brutos do site (Salva em data/bronze/books.csv)
python services/scraper/src/extractors/scrape_books.py

# 2. Transformar dados brutos em dados limpos (Salva em data/silver/books.parquet)
python services/scraper/src/transformers/clean_books.py
```

### 2\. Executando a API Localmente

Após os arquivos de dados serem gerados, é possível iniciar o servidor da API:

```bash
python services/api/src/app.py
```

O servidor estará disponível localmente no endereço: `http://127.0.0.1:5000`.
A documentação Swagger estará disponível em: `http://127.0.0.1:5000/apidocs/`

-----

## 4\. Documentação das Rotas da API

A API utiliza **Flasgger** para gerar a documentação interativa (Swagger UI), disponível na rota `/apidocs/`.

### Endpoints Obrigatórios

#### `GET /api/v1/health`

  * **Descrição:** Verifica o status da API e a conectividade com o dataset (camada Silver).
  * **Resposta (200 OK):**
    ```json
    {
      "status": "ok",
      "details": {
        "dataset_path": ".../data/silver/books.parquet",
        "exists": true,
        "rows": 1000,
        "columns_present": [],
        "columns_required_ok": true
      }
    }
    ```

#### `GET /api/v1/categories`

  * **Descrição:** Lista todas as categorias de livros únicas disponíveis na base de dados.
  * **Resposta (200 OK):**
    ```json
    {
      "items": [
        "add a comment",
        "art",
        "business",
      ],
      "total": 50
    }
    ```

#### `GET /api/v1/books`

  * **Descrição:** Lista todos os livros disponíveis, com paginação.
  * **Query Params:**
      * `q` (string, opcional): Filtra livros cujo título contém a string de busca.
      * `page` (int, opcional, default=1): Número da página.
      * `size` (int, opcional, default=20): Itens por página.
  * **Resposta (200 OK):**
    ```json
    {
      "items": [
        {
          "id": "a897fe39b1053632",
          "title": "a light in the attic",
          "category": "poetry",
          "price": 51.77,
          "rating": 3
        },
      ],
      "page": 1,
      "size": 20,
      "total": 1000
    }
    ```

#### `GET /api/v1/books/<string:book_id>`

  * **Descrição:** Retorna detalhes completos de um livro específico pelo ID.
  * **Resposta (200 OK):**
    ```json
    {
      "UPC": "a897fe39b1053632",
      "book_title": "a light in the attic",
      "category": "poetry",
      "id": "a897fe39b1053632",
      "image_url": "...",
      "instock": 22,
      "price": 51.77,
      "product_url": "...",
      "rating": 3,
      "title": "a light in the attic"
    }
    ```
  * **Resposta (404 Not Found):**
    ```json
    {
      "error": "book id 'ID_INEXISTENTE' não encontrado"
    }
    ```

#### `GET /api/v1/books/search`

  * **Descrição:** Busca livros por título e/ou categoria, com paginação.
  * **Query Params:**
      * `title` (string, opcional): Filtra por substring no título.
      * `category` (string, opcional): Filtra por substring na categoria.
      * `page` (int, opcional, default=1): Número da página.
      * `size` (int, opcional, default=20): Itens por página.
  * **Resposta (200 OK):**
    ```json
    {
      "items": [
        {
          "id": "c21f5533b3187122",
          "title": "the secret garden",
          "category": "classic",
        }
      ],
      "page": 1,
      "size": 20,
      "total": 1
    }
    ```

### Endpoints de Insights (Opcionais)

  * **`GET /api/v1/books/top-rated`**: Filtra livros com base em uma nota mínima (`min_rating`).
  * **`GET /api/v1/books/price-range`**: Filtra livros dentro de uma faixa de preço (`min`, `max`).
  * **`GET /api/v1/stats/overview`**: Retorna estatísticas gerais da coleção (total de livros, categorias, estatísticas de preço e distribuição de ratings).
  * **`GET /api/v1/stats/categories`**: Retorna estatísticas detalhadas por categoria (contagem de livros, média/mediana/min/max de preço).

-----

### Desafio 1: Sistema de Autenticação (JWT)

Endpoints protegidos (como os de *Insights* e *Admin*) requerem um Token JWT no header `Authorization: Bearer <token>`.

#### `POST /api/v1/auth/login`

  * **Descrição:** Autentica um usuário (definido nas variáveis de ambiente `ADMIN_USER` e `ADMIN_PASS`) e retorna um `access_token` e `refresh_token`.
  * **Request Body:**
    ```json
    {
      "username": "admin",
      "password": "*******"
    }
    ```
  * **Resposta (200 OK):**
    ```json
    {
      "access_token": "...",
      "refresh_token": "..."
    }
    ```

#### `POST /api/v1/auth/refresh`

  * **Descrição:** 🔒 Permite renovar um `access_token` expirado. Requer um `refresh_token` válido no header `Authorization`.
  * **Resposta (200 OK):**
    ```json
    {
      "access_token": "..."
    }
    ```

#### `POST /api/v1/scraping/trigger`

  * **Descrição:** 🔒 [Admin] Endpoint protegido (stub) que, em um cenário de produção, acionaria o pipeline de ETL (scraping + cleaning). Requer privilégios de admin.
  * **Resposta (202 Accepted):**
    ```json
    {
      "msg": "trigger recebido (stub). Em produção chamaria o job ETL."
    }
    ```

-----

### Desafio 2: Pipeline ML-Ready

Endpoints criados para facilitar o consumo direto por Cientistas de Dados e modelos de ML.

#### `GET /api/v1/ml/features`

  * **Descrição:** 🔒 Retorna dados formatados (features) para inferência ou análise.
  * **Query Params:**
      * `format` (string, opcional, default=json): Pode ser alterado para `csv` para baixar o dataset.
  * **Resposta (200 OK - JSON):**
    ```json
    {
      "items": [
        {
          "id": "a897fe39b1053632",
          "price": 51.77,
          "rating": 3,
          "category_idx": 3,
          "title_len": 17,
          "has_image": true
        }, 
      ],
      "page": 1,
      "size": 100,
      "total": 1000
    }
    ```

#### `GET /api/v1/ml/training-data`

  * **Descrição:** 🔒 Retorna um dataset de treinamento completo, com features e um alvo sintético (`target_high_rating`).
  * **Query Params:**
      * `format` (string, opcional, default=csv): Retorna o dataset de treino em formato CSV (default) ou JSON.
  * **Resposta (200 OK - CSV):**
    ```csv
    id,price,rating,category_idx,title_len,has_image,target_high_rating
    a897fe39b1053632,51.77,3,3,17,1,0
    ce60436f52c5ee68,53.74,1,1,16,1,0
    ...
    ```

#### `POST /api/v1/ml/predictions`

  * **Descrição:** 🔒 Endpoint para receber e persistir predições de um modelo de ML.
  * **Request Body:**
    ```json
    {
      "model": "model_v1_teste",
      "predictions": [
          {"id": "a897fe39b1053632", "y_pred": 0.87},
          {"id": "ce60436f52c5ee68", "y_pred": 0.12}
      ]
    }
    ```
  * **Resposta (202 Accepted):**
    ```json
    {
      "model": "model_v1_teste",
      "saved_file": ".../data/ml/predictions_model_v1_teste_....jsonl",
      "accepted": 2,
      "rejected": 0
    }
    ```

-----

## 5\. 💡 Exemplos de Chamadas (Requests/Responses)

Substitua `[URL_BASE]` por `http://127.0.0.1:5000` (local) ou pela URL do seu deploy público.

### Usando `curl` (Terminal)

**1. Verificar Saúde da API**

```bash
curl -X 'GET' '[URL_BASE]/api/v1/health'
```

**2. Buscar por Título (que contenha "Music")**

```bash
curl -X 'GET' '[URL_BASE]/api/v1/books/search?title=Music'
```

**3. Testando a Autenticação (Desafio 1)**

```bash
# 3.1. Fazer login e salvar o token (ajuste usuário/senha se necessário)
# (Este comando usa 'jq' para extrair o token, ou você pode copiar manualmente)
TOKEN=$(curl -s -X 'POST' '[URL_BASE]/api/v1/auth/login' \
  -H 'Content-Type: application/json' \
  -d '{"username": "admin", "password": "*******"}' \
  | jq -r .access_token)

echo "Token obtido: $TOKEN"

# 3.2. Usar o token para acessar um endpoint protegido (ex: /stats/overview)
curl -X 'GET' '[URL_BASE]/api/v1/stats/overview' \
  -H "Authorization: Bearer $TOKEN"
```

**4. Testando o Pipeline ML-Ready (Desafio 2)**

```bash
# (Requer o $TOKEN do passo anterior)

# 4.1. Obter dados de features em formato CSV
curl -X 'GET' '[URL_BASE]/api/v1/ml/training-data?format=csv' \
  -H "Authorization: Bearer $TOKEN" \
  -o "training_data.csv"

# 4.2. Enviar predições (stub)
curl -X 'POST' '[URL_BASE]/api/v1/ml/predictions' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
        "model": "local_test_v1",
        "predictions": [
            {"id": "a897fe39b1053632", "y_pred": 0.99},
            {"id": "ce60436f52c5ee68", "y_pred": 0.01}
        ]
      }'
```

### Usando Python (Cenário do Cientista de Dados)

```python
import requests
import pandas as pd
import json

# Use a URL do deploy ou a URL local
BASE_URL = "https://tech-challenge-fiap-no1e.onrender.com"  # Ex: "http://127.0.0.1:5000"

try:
    # 1. Verificar a saúde da API
    health_check = requests.get(f"{BASE_URL}/api/v1/health")
    health_check.raise_for_status()
    print("API Status:", health_check.json()['status'])

    # 2. Fazer a requisição para o endpoint de busca (público)
    print("\nBuscando livros de 'Science Fiction'...")
    params = {
        "category": "Science Fiction",
        "size": 100 
    }
    response = requests.get(f"{BASE_URL}/api/v1/books/search", params=params)
    response.raise_for_status() 
    data = response.json()
    df_books = pd.DataFrame(data['items'])
    print(f"Total de livros encontrados: {data['total']}")
    
    # 3. Autenticar para acessar endpoints protegidos (Desafio 1)
    print("\nAutenticando...")
    auth_payload = {
        "username": "admin", # Use suas credenciais
        "password": "*******"
    }
    auth_resp = requests.post(f"{BASE_URL}/api/v1/auth/login", json=auth_payload)
    auth_resp.raise_for_status()
    TOKEN = auth_resp.json()['access_token']
    
    # 4. Usar o token para buscar dados de ML (Desafio 2)
    print("Buscando dados de features (ML-Ready)...")
    headers = {
        "Authorization": f"Bearer {TOKEN}"
    }
    ml_params = {
        "format": "json",
        "size": 5
    }
    ml_resp = requests.get(f"{BASE_URL}/api/v1/ml/features", headers=headers, params=ml_params)
    ml_resp.raise_for_status()
    
    print("\nFeatures (ML-Ready) - Primeiras 5 linhas:")
    print(json.dumps(ml_resp.json()['items'], indent=2))
    
except requests.exceptions.RequestException as e:
    print(f"Erro ao conectar-se à API: {e}")
```

## 👥 Contribuidores

[mayara-canaver](https://github.com/mayara-canaver)
[eduardohenrik](https://github.com/eduardohenrik)