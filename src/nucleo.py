"""
nucleo.py - Unidade de trabalho do projeto.

Contem o processamento de UM documento (um edital de compra publica).
As versoes sequencial e paralela importam exatamente estas funcoes, para que o
trabalho por documento seja identico nas duas e a comparacao de tempo seja justa.

Nao ha nenhum estado global neste modulo: toda funcao e pura. Isso e proposital,
porque o unico estado compartilhado do projeto e o agregador global, que vive em
memoria compartilhada e e protegido por lock (ver paralelo.py).
"""

import hashlib
import random
import re
import unicodedata
from collections import Counter

# ---------------------------------------------------------------------------
# Configuracao do trabalho por documento
# ---------------------------------------------------------------------------

TAMANHO_SHINGLE = 5          # tokens por shingle (n-grama de palavras)
TAMANHO_ASSINATURA = 64      # quantos hashes minimos formam a assinatura MinHash
_TOKEN = re.compile(r"[a-z0-9]{3,}")
INICIO_OBJETO = "objeto:"
FIM_OBJETO = "das condicoes gerais"

STOPWORDS = frozenset("""
que para com uma dos das nos nas por pelo pela como mais mas nao seu sua seus
suas este esta estes estas esse essa isso aquele aquela ser ter estar foi sao
sera serao deve devera podera quando onde qual quais sobre entre ate apos antes
cada todo toda todos todas outro outra outros outras mesmo mesma ainda apenas
tambem porque entao assim desde durante conforme mediante perante salvo exceto
art inciso alinea paragrafo caput item subitem anexo
""".split())

# Taxonomia de triagem: termo -> peso. Serve para pontuar a aderencia de um
# edital a uma linha de produto de software. Os pesos sao arbitrarios mas fixos,
# o que mantem o resultado deterministico e portanto verificavel.
TAXONOMIA = {
    # nucleo de gestao publica
    "erp": 10, "gestao": 3, "integrada": 4, "administrativa": 3,
    "contabil": 6, "orcamentaria": 6, "financeira": 5, "patrimonial": 5,
    "almoxarifado": 5, "protocolo": 4, "folha": 5, "pagamento": 3,
    # arrecadacao e tributos
    "tributario": 10, "arrecadacao": 9, "iptu": 8, "issqn": 8, "iss": 6,
    "itbi": 7, "divida": 6, "ativa": 4, "nota": 3, "fiscal": 6,
    "eletronica": 4, "cadastro": 4, "imobiliario": 6, "mobiliario": 5,
    # modalidade e forma de contratacao
    "licitacao": 4, "pregao": 5, "presencial": 2, "dispensa": 4,
    "inexigibilidade": 5, "credenciamento": 4, "adesao": 3, "registro": 3,
    "precos": 3, "contratacao": 3, "termo": 2, "referencia": 2,
    # tecnologia
    "software": 8, "sistema": 5, "licenca": 5, "nuvem": 6, "saas": 7,
    "hospedagem": 5, "migracao": 6, "implantacao": 6, "treinamento": 4,
    "suporte": 4, "manutencao": 3, "customizacao": 5, "api": 5,
    "banco": 3, "dados": 3, "backup": 4, "integracao": 5,
    # sinais negativos (edital que NAO e de software)
    "pavimentacao": -12, "asfalto": -12, "merenda": -10, "medicamento": -10,
    "combustivel": -10, "veiculo": -8, "reforma": -8, "obra": -8,
    "limpeza": -8, "vigilancia": -6, "uniforme": -8, "mobiliario_escolar": -8,
}

LINHAS_PRODUTO = {
    "erp_publico": ("erp", "contabil", "orcamentaria", "patrimonial",
                    "almoxarifado", "folha", "protocolo"),
    "arrecadacao": ("tributario", "arrecadacao", "iptu", "issqn", "itbi",
                    "divida", "imobiliario"),
    "nota_fiscal": ("nota", "fiscal", "eletronica", "issqn", "iss"),
    "infraestrutura": ("nuvem", "saas", "hospedagem", "migracao", "backup",
                       "banco", "integracao"),
}


# ---------------------------------------------------------------------------
# Etapas do processamento
# ---------------------------------------------------------------------------

def normalizar(texto):
    """Remove acentos e caixa alta. NFKD + descarte de combinantes."""
    decomposto = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in decomposto if not unicodedata.combining(c))
    return sem_acento.lower()


def tokenizar(texto_normalizado):
    """Quebra em tokens de 3+ caracteres alfanumericos e remove stopwords."""
    return [t for t in _TOKEN.findall(texto_normalizado) if t not in STOPWORDS]


# Permutacoes do MinHash. Geradas uma unica vez, com semente fixa, para que a
# assinatura de um documento seja sempre a mesma em qualquer maquina e em
# qualquer das duas versoes do programa.
_PRIMO = (1 << 61) - 1
_PERMUTACOES = None


def _permutacoes():
    global _PERMUTACOES
    if _PERMUTACOES is None:
        rng = random.Random(70080)
        _PERMUTACOES = tuple(
            (rng.randrange(1, _PRIMO), rng.randrange(0, _PRIMO))
            for _ in range(TAMANHO_ASSINATURA)
        )
    return _PERMUTACOES


def assinatura_minhash(tokens, k=TAMANHO_SHINGLE, n=TAMANHO_ASSINATURA):
    """
    Assinatura MinHash do documento (Broder, 1997), usada para detectar editais
    duplicados ou quase duplicados. O mesmo edital republicado por varios
    municipios, com alteracao apenas de cabecalho, e um caso comum no PNCP.

    O documento vira um conjunto de shingles de k tokens. Para cada uma das n
    permutacoes h_i(x) = (a_i*x + b_i) mod p, a assinatura guarda o menor valor
    observado. A probabilidade de duas assinaturas coincidirem na posicao i e
    igual a similaridade de Jaccard entre os conjuntos de shingles, o que e o
    que torna a tecnica util.

    Duas propriedades importam para este projeto:

      1. O resultado depende apenas do CONJUNTO de shingles, nunca da ordem em
         que foram vistos. E isso que garante que a versao paralela produza
         exatamente a mesma assinatura que a sequencial.
      2. O laco interno e aritmetica de inteiros em Python puro: n operacoes por
         shingle, dezenas de milhares por documento. E esta etapa que domina o
         tempo e que torna o trabalho limitado por processador.
    """
    if len(tokens) < k:
        return ()
    permutacoes = _permutacoes()
    assinatura = [_PRIMO] * n
    b2 = hashlib.blake2b
    primo = _PRIMO
    for i in range(len(tokens) - k + 1):
        shingle = " ".join(tokens[i:i + k]).encode("utf-8")
        h = int.from_bytes(b2(shingle, digest_size=8).digest(), "big")
        assinatura = [
            valor if valor < (novo := (a * h + b) % primo) else novo
            for valor, (a, b) in zip(assinatura, permutacoes)
        ]
    return tuple(assinatura)


def digest_assinatura(assinatura):
    """Comprime a assinatura em 16 caracteres hexadecimais.

    Nao e uma exigencia do problema: e uma decisao de projeto para que a chave
    que viaja ate a memoria compartilhada seja curta. Guardar a tupla inteira
    faria cada fusao carregar dezenas de kilobytes pelo canal do Manager, e o
    custo de comunicacao passaria a dominar o tempo paralelo.
    """
    if not assinatura:
        return ""
    h = hashlib.blake2b(digest_size=8)
    for valor in assinatura:
        h.update(valor.to_bytes(8, "big"))
    return h.hexdigest()


def pontuar(contagem):
    """Pontuacao de aderencia do edital a taxonomia."""
    return sum(TAXONOMIA[t] * c for t, c in contagem.items() if t in TAXONOMIA)


def classificar(contagem):
    """Linha de produto com maior evidencia no documento."""
    melhor, melhor_valor = "nao_classificado", 0
    for linha, termos in LINHAS_PRODUTO.items():
        valor = sum(contagem.get(t, 0) for t in termos)
        if valor > melhor_valor:
            melhor, melhor_valor = linha, valor
    return melhor


def processar_documento(doc_id, texto):
    """
    Unidade de trabalho indivisivel do projeto.

    Recebe o texto de um edital e devolve um dicionario com o resultado.
    Nao toca em nada fora de si: e por isso que o trabalho se divide em partes
    independentes e pode ser distribuido entre processos sem coordenacao.
    """
    normalizado = normalizar(texto)
    tokens = tokenizar(normalizado)
    contagem = Counter(tokens)

    # A impressao digital cobre apenas o corpo do edital, do campo "Objeto:" em
    # diante. O cabecalho traz numero do processo, modalidade e data, que mudam
    # a cada republicacao do MESMO edital: incluir o cabecalho faria a assinatura
    # deixar de reconhecer justamente o caso que ela existe para reconhecer.
    corpo = normalizado.split(INICIO_OBJETO, 1)[-1]
    tokens_do_corpo = tokenizar(corpo)

    # A pontuacao e a classificacao olham SO para a descricao do objeto. O
    # restante do edital e texto padrao de pagamento, vigencia e sancoes, que
    # aparece igual em todo edital e so introduziria ruido: sem esse recorte,
    # "nota fiscal" da clausula de pagamento classificaria qualquer obra como
    # projeto de nota fiscal eletronica.
    objeto = corpo.split(FIM_OBJETO, 1)[0]
    contagem_objeto = Counter(tokenizar(objeto))
    relevantes = Counter({t: c for t, c in contagem.items() if t in TAXONOMIA})
    return {
        "doc_id": doc_id,
        "tokens": len(tokens),
        "pontuacao": pontuar(contagem_objeto),
        "linha": classificar(contagem_objeto),
        "assinatura": digest_assinatura(assinatura_minhash(tokens_do_corpo)),
        "termos": relevantes,
    }


# ---------------------------------------------------------------------------
# Agregacao (executada dentro da secao critica na versao paralela)
# ---------------------------------------------------------------------------

def agregado_vazio():
    return {
        "documentos": 0,
        "tokens": 0,
        "pontuacao_total": 0,
        "termos": Counter(),
        "linhas": Counter(),
        "top": [],          # lista de (pontuacao, doc_id)
        "assinaturas": {},  # assinatura -> menor doc_id que a produziu
        "duplicados": 0,
    }


def acumular(agregado, resultado, limite_top=25):
    """Funde UM resultado de documento no agregado. Operacao associativa e
    comutativa, o que e o que permite que cada trabalhador acumule localmente e
    so depois funda o seu parcial no agregado global."""
    agregado["documentos"] += 1
    agregado["tokens"] += resultado["tokens"]
    agregado["pontuacao_total"] += resultado["pontuacao"]
    agregado["termos"].update(resultado["termos"])
    agregado["linhas"][resultado["linha"]] += 1

    chave = resultado["assinatura"]
    if chave:
        anterior = agregado["assinaturas"].get(chave)
        if anterior is None:
            agregado["assinaturas"][chave] = resultado["doc_id"]
        else:
            agregado["duplicados"] += 1
            if resultado["doc_id"] < anterior:
                agregado["assinaturas"][chave] = resultado["doc_id"]

    agregado["top"].append((resultado["pontuacao"], resultado["doc_id"]))
    if len(agregado["top"]) > limite_top * 4:
        agregado["top"].sort(key=lambda p: (-p[0], p[1]))
        del agregado["top"][limite_top:]
    return agregado


def fundir(destino, parcial, limite_top=25):
    """Funde um agregado parcial inteiro em outro. E exatamente este trecho que
    a versao paralela executa dentro da secao critica."""
    destino["documentos"] += parcial["documentos"]
    destino["tokens"] += parcial["tokens"]
    destino["pontuacao_total"] += parcial["pontuacao_total"]
    destino["termos"].update(parcial["termos"])
    destino["linhas"].update(parcial["linhas"])
    destino["duplicados"] += parcial["duplicados"]

    for chave, doc_id in parcial["assinaturas"].items():
        anterior = destino["assinaturas"].get(chave)
        if anterior is None:
            destino["assinaturas"][chave] = doc_id
        else:
            destino["duplicados"] += 1
            if doc_id < anterior:
                destino["assinaturas"][chave] = doc_id

    destino["top"].extend(parcial["top"])
    destino["top"].sort(key=lambda p: (-p[0], p[1]))
    del destino["top"][limite_top:]
    return destino


def finalizar(agregado, limite_top=25, limite_termos=30):
    """
    Reduz o agregado a um relatorio canonico, em ordem determinada apenas pelo
    conteudo. Como nao depende da ordem de chegada dos documentos, a versao
    sequencial e a paralela produzem o MESMO relatorio, byte a byte.
    """
    agregado["top"].sort(key=lambda p: (-p[0], p[1]))
    return {
        "documentos": agregado["documentos"],
        "tokens": agregado["tokens"],
        "pontuacao_total": agregado["pontuacao_total"],
        "documentos_duplicados": agregado["duplicados"],
        "assinaturas_distintas": len(agregado["assinaturas"]),
        "linhas": sorted(agregado["linhas"].items()),
        "termos": sorted(
            agregado["termos"].items(), key=lambda p: (-p[1], p[0])
        )[:limite_termos],
        "top": [
            {"doc_id": d, "pontuacao": p}
            for p, d in agregado["top"][:limite_top]
        ],
    }


def impressao_do_relatorio(relatorio):
    """SHA-256 do relatorio canonico. E a prova de que as duas versoes
    produziram o mesmo resultado."""
    import json
    bruto = json.dumps(relatorio, sort_keys=True, ensure_ascii=False,
                       separators=(",", ":"))
    return hashlib.sha256(bruto.encode("utf-8")).hexdigest()
