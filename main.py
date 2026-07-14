from flask import Flask, render_template, request
import requests
import csv
from io import StringIO
from bs4 import BeautifulSoup
import unicodedata

app = Flask(__name__)

# --- Normalização de texto ---
def normalizar(texto):
    if not texto:
        return ""
    texto = unicodedata.normalize("NFKD", texto).encode("ASCII", "ignore").decode("utf-8")
    return texto.strip()

# --- Validação de links ---
def validar_link(url):
    try:
        resp = requests.head(url, timeout=5, allow_redirects=True)
        return resp.status_code == 200
    except:
        return False

# --- IA simples para classificação ---
def classificar_vaga(titulo):
    titulo = titulo.lower()
    if any(p in titulo for p in ["administrativo", "escritorio", "financeiro", "contabil"]):
        return "Administrativo"
    elif any(p in titulo for p in ["producao", "operador", "industrial", "fabrica", "manutencao"]):
        return "Produção"
    elif any(p in titulo for p in ["atendimento", "vendas", "cliente", "suporte", "comercial"]):
        return "Atendimento"
    else:
        return "Outros"

# --- Fontes oficiais (exemplos simplificados) ---
def buscar_govbr():
    url = "https://dados.gov.br/dataset/jovem-aprendiz.csv"
    vagas = []
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            f = StringIO(resp.text)
            reader = csv.reader(f, delimiter=",")
            next(reader)
            for row in reader:
                if len(row) >= 4 and validar_link(row[3]):
                    vagas.append({
                        "titulo": row[0],
                        "empresa": row[1],
                        "regiao": row[2],
                        "link": row[3],
                        "fonte": "Gov.br",
                        "setor": classificar_vaga(row[0])
                    })
    except Exception as e:
        print("Erro Gov.br:", e)
    return vagas

def buscar_linkedin():
    url = "https://www.linkedin.com/jobs/search/?keywords=jovem%20aprendiz&location=Brazil"
    vagas = []
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.select("div.base-card")
            for card in cards[:10]:
                titulo = card.select_one("h3.base-search-card__title")
                empresa = card.select_one("h4.base-search-card__subtitle")
                link = card.select_one("a.base-card__full-link")
                regiao = card.select_one("span.job-search-card__location")
                if titulo and empresa and link and validar_link(link["href"]):
                    vagas.append({
                        "titulo": titulo.get_text(strip=True),
                        "empresa": empresa.get_text(strip=True),
                        "regiao": regiao.get_text(strip=True) if regiao else "Brasil",
                        "link": link["href"],
                        "fonte": "LinkedIn",
                        "setor": classificar_vaga(titulo.get_text(strip=True))
                    })
    except Exception as e:
        print("Erro LinkedIn:", e)
    return vagas

def buscar_ciee():
    url = "https://portal.ciee.org.br/vagas"
    if validar_link(url):
        return [{
            "titulo": "Aprendiz Atendimento",
            "empresa": "CIEE",
            "regiao": "São Paulo",
            "link": url,
            "fonte": "CIEE",
            "setor": classificar_vaga("Aprendiz Atendimento")
        }]
    return []

def buscar_espro():
    url = "https://espro.org.br/vagas"
    if validar_link(url):
        return [{
            "titulo": "Aprendiz Administrativo",
            "empresa": "Espro",
            "regiao": "Campinas",
            "link": url,
            "fonte": "Espro",
            "setor": classificar_vaga("Aprendiz Administrativo")
        }]
    return []

# --- Função principal ---
def buscar_todas_vagas():
    vagas = []
    vagas.extend(buscar_govbr())
    vagas.extend(buscar_ciee())
    vagas.extend(buscar_espro())
    vagas.extend(buscar_linkedin())
    return vagas

@app.route("/", methods=["GET", "POST"])
def index():
    filtro_regiao = request.form.get("regiao", "todas")
    vagas = buscar_todas_vagas()

    # gerar lista dinâmica de regiões
    regioes = sorted(set([normalizar(v["regiao"]) for v in vagas if v.get("regiao")]))

    # aplicar filtro
    if filtro_regiao != "todas":
        vagas = [v for v in vagas if normalizar(filtro_regiao).lower() in normalizar(v["regiao"]).lower()]

    return render_template("index.html", vagas=vagas, filtro=filtro_regiao, regioes=regioes)

@app.route("/buscar", methods=["GET", "POST"])
def buscar():
    termo = request.form.get("termo", "")
    vagas = buscar_todas_vagas()
    if termo:
        vagas = [v for v in vagas if termo.lower() in v["titulo"].lower() or termo.lower() in v["empresa"].lower()]
    return render_template("buscar.html", vagas=vagas, termo=termo)

@app.route("/detalhes")
def detalhes():
    titulo = request.args.get("titulo")
    empresa = request.args.get("empresa")
    regiao = request.args.get("regiao")
    fonte = request.args.get("fonte")
    setor = request.args.get("setor")
    link = request.args.get("link")
    return render_template("detalhes.html", titulo=titulo, empresa=empresa, regiao=regiao, fonte=fonte, setor=setor, link=link)

if __name__ == "__main__":
    app.run(debug=True)
