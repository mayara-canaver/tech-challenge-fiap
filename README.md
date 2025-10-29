# Tech Challenge FIAP - API Pública de Livros

![Framework: Flask](https://img.shields.io/badge/Framework-Flask-blue)
![Deploy: Render](https://img.shields.io/badge/Deploy-Render-blueviolet)
![Python](https://img.shields.io/badge/Python-3.10%2B-green)
![Status](https://img.shields.io/badge/Status-Completo-brightgreen)

Este projeto é a solução para o Tech Challenge da pós-graduação em Machine Learning Engineering, com o objetivo de demonstrar um fluxo end-to-end de dados: desde o web scraping e ETL até a disponibilização dos dados via API RESTful e seu deploy em um ambiente de produção.

### Links de Referência

* **Link do Deploy (Produção):** `[https://tech-challenge-fiap-no1e.onrender.com]`
* **Link do Vídeo de Apresentação:** `[]`

---

## 1. Descrição do Projeto e Arquitetura

### Descrição

Como primeiro desafio para um projeto de recomendação de livros, esta solução foca em construir o pipeline de dados fundamental. O objetivo é extrair dados de livros do site público `https://books.toscrape.com/`, processá-los e disponibilizá-los através de uma API RESTful pública, robusta e documentada, pronta para ser consumida por Cientistas de Dados e serviços de ML.

### Arquitetura do Pipeline

O pipeline de dados segue um fluxo ETL (Extract, Transform, Load) que alimenta a API, com uma clara separação entre as camadas de dados (Bronze e Silver):

1.  **Ingestão (Extract):** O script `services/scraper/src/extractors/scrape_books.py` realiza o web scraping do site, navegando por todas as categorias e páginas para extrair os dados brutos de cada livro.
2.  **Camada Bronze:** Os dados brutos extraídos são salvos em `data/bronze/books.csv`.
3.  **Processamento (Transform):** O script `services/scraper/src/transformers/clean_books.py` lê os dados da camada Bronze. Ele realiza a limpeza e normalização (conversão de preços, normalização de texto, tratamento de ratings).
4.  **Camada Silver (Load):** Os dados limpos e prontos para consumo são salvos em `data/silver/books.csv` e `data/silver/books.parquet`.
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
        K --> L[Consumidores (Cientistas de Dados, ML)];
    end
````

-----

## 2\. ⚙️ Instruções de Instalação e Configuração

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
    JWT_SECRET="S3CR3T_K3Y_F0R_JWT_!@#"

    # Credenciais do usuário administrador da API
    ADMIN_USER="admin"
    ADMIN_PASS="admin123"
    ```

-----

## 3\. 🚀 Instruções de Execução

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
# O 'app.py' contém a lógica para rodar em modo debug
python services/api/src/app.py
```

O servidor estará disponível localmente no endereço: `http://127.0.0.1:5000`.

*(Nota: O deploy em produção utiliza o `gunicorn` conforme definido no `render.yaml`, mas para desenvolvimento local, executar o `app.py` é suficiente.)*

-----

## 4\. 📚 Documentação das Rotas da API

A API é implementada com Flask e não possui o Swagger configurado. Abaixo está a documentação manual dos endpoints disponíveis.

*(Nota: Alguns endpoints (como `/trigger`) exigem autenticação. Você pode obter um token fazendo um POST em `/api/v1/auth/login` com o `ADMIN_USER` e `ADMIN_PASS` definidos no seu `.env` file.)*

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
        "columns_present": [...],
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
        ...
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
        ...
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
      "image_path": null,
      "image_url": "[https://books.toscrape.com/media/cache/2c/da/2cdad67c44b002e7ead0cc35693c0e8b.jpg](https://books.toscrape.com/media/cache/2c/da/2cdad67c44b002e7ead0cc35693c0e8b.jpg)",
      "instock": 22,
      "price": 51.77,
      "product_url": "[https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html](https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html)",
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
          "price": 15.08,
          "rating": 4
        }
      ],
      "page": 1,
      "size": 20,
      "total": 1
    }
    ```

### Endpoints de Insights (Opcionais)

A API também implementa os endpoints de insights:

  * **`GET /api/v1/books/top-rated`**: Filtra livros com base em uma nota mínima (`min_rating`).
  * **`GET /api/v1/books/price-range`**: Filtra livros dentro de uma faixa de preço (`min`, `max`).
  * **`GET /api/v1/stats/overview`**: Retorna estatísticas gerais da coleção (total de livros, categorias, estatísticas de preço e distribuição de ratings).
  * **`GET /api/v1/stats/categories`**: Retorna estatísticas detalhadas por categoria (contagem de livros, média/mediana/min/max de preço).

-----

## 5\. 💡 Exemplos de Chamadas (Requests/Responses)

Substitua `https://tech-challenge-fiap-no1e.onrender.com` por `http://127.0.0.1:5000` (local) ou pela URL do seu deploy público.

### Usando `curl` (Terminal)

**1. Verificar Saúde da API**

```bash
curl -X 'GET' 'https://tech-challenge-fiap-no1e.onrender.com/api/v1/health'
```

**2. Listar Categorias**

```bash
curl -X 'GET' 'https://tech-challenge-fiap-no1e.onrender.com/api/v1/categories'
```

**3. Obter um Livro por ID** (Exemplo: "A Light in the Attic")

```bash
curl -X 'GET' 'https://tech-challenge-fiap-no1e.onrender.com/api/v1/books/a897fe39b1053632'
```

**4. Buscar por Título (que contenha "Music")**

```bash
curl -X 'GET' 'https://tech-challenge-fiap-no1e.onrender.com/api/v1/books/search?title=Music'
```

**5. Buscar por Categoria (exata: "History")**

```bash
curl -X 'GET' 'https://tech-challenge-fiap-no1e.onrender.com/api/v1/books/search?category=History'
```

**6. Buscar Livros de "Mystery" que contenham "The" no título**

```bash
curl -X 'GET' 'https://tech-challenge-fiap-no1e.onrender.com/api/v1/books/search?title=The&category=Mystery'
```

### Usando Python (Cenário do Cientista de Dados)

Este é um exemplo de como um Cientista de Dados consumiria a API para carregar os dados em um DataFrame do Pandas para análise.

```python
import requests
import pandas as pd

# Use a URL do deploy ou a URL local
BASE_URL = "https://tech-challenge-fiap-no1e.onrender.com"  # Ex: "[http://127.0.0.1:5000](http://127.0.0.1:5000)"

try:
    # 1. Verificar a saúde da API
    health_check = requests.get(f"{BASE_URL}/api/v1/health")
    health_check.raise_for_status()
    print("API Status:", health_check.json()['status'])

    # 2. Fazer a requisição para o endpoint de busca
    # Buscar todos os livros da categoria "Science Fiction"
    print("\nBuscando livros de 'Science Fiction'...")
    params = {
        "category": "Science Fiction",
        "size": 100 # Pedir um tamanho grande para pegar todos
    }
    response = requests.get(f"{BASE_URL}/api/v1/books/search", params=params)
    response.raise_for_status() 
    
    data = response.json()
    
    # 3. Converter os dados JSON em um DataFrame do Pandas
    df_books = pd.DataFrame(data['items'])
    
    # 4. Iniciar a Análise
    print(f"Total de livros encontrados: {data['total']}")
    
    print("\nInformações do DataFrame:")
    print(df_books.info())
    
    print("\nEstatísticas de Preço para 'Science Fiction':")
    print(df_books['price'].describe())
    
    print("\nTop 5 livros com melhor avaliação na categoria:")
    print(df_books.nlargest(5, 'rating')[['title', 'price', 'rating']])

except requests.exceptions.RequestException as e:
    print(f"Erro ao conectar-se à API: {e}")
```

```
```

## 👥 Contribuidores

[mayara-canaver](https://github.com/mayara-canaver)
[eduardohenrik](https://github.com/eduardohenrik)
