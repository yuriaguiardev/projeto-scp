"""
corpus.py - Gera o corpus de entrada de forma deterministica.

O corpus imita um lote de editais de compra publica baixados do PNCP. Usamos um
gerador com semente fixa em vez de arquivos baixados por dois motivos:

  1. Qualquer pessoa reproduz exatamente a mesma entrada com um comando, o que e
     condicao para comparar o tempo sequencial e o paralelo "com a mesma entrada".
  2. O volume e um parametro, entao a mesma aplicacao serve para calibrar a
     medicao em maquinas de porte diferente.

Uso:
    python3 src/corpus.py --docs 9000 --saida dados/corpus
"""

import argparse
import os
import random
import time

ORGAOS = [
    "Prefeitura Municipal", "Camara Municipal", "Secretaria Municipal de Financas",
    "Secretaria de Administracao", "Instituto de Previdencia dos Servidores",
    "Fundo Municipal de Saude", "Autarquia Municipal de Agua e Esgoto",
    "Secretaria Municipal de Educacao", "Departamento de Estradas de Rodagem",
    "Consorcio Intermunicipal de Saude",
]

MUNICIPIOS = [
    "Ananindeua", "Marituba", "Castanhal", "Abaetetuba", "Braganca",
    "Santarem", "Maraba", "Paragominas", "Tucurui", "Altamira",
    "Barcarena", "Cameta", "Itaituba", "Redencao", "Breves",
]

MODALIDADES = [
    "Pregao Eletronico", "Pregao Presencial", "Dispensa de Licitacao",
    "Inexigibilidade", "Concorrencia", "Credenciamento",
    "Adesao a Ata de Registro de Precos",
]

BLOCOS_SOFTWARE = [
    "contratacao de empresa especializada no fornecimento de licenca de uso de "
    "sistema integrado de gestao publica erp contemplando os modulos contabil "
    "orcamentaria financeira patrimonial e almoxarifado",
    "aquisicao de solucao de software para gestao tributaria e arrecadacao "
    "municipal abrangendo iptu issqn itbi cadastro imobiliario cadastro "
    "mobiliario e divida ativa",
    "implantacao de plataforma de nota fiscal de servicos eletronica com "
    "emissao escrituracao e integracao com o sistema de arrecadacao do "
    "municipio",
    "servico de hospedagem em nuvem no modelo saas incluindo backup diario "
    "monitoramento e disponibilidade do banco de dados do sistema de gestao",
    "prestacao de servico de migracao de dados legados implantacao "
    "customizacao treinamento e suporte tecnico do sistema contratado",
    "fornecimento de api de integracao entre o sistema de protocolo eletronico "
    "e o sistema de gestao de folha de pagamento dos servidores",
    "manutencao evolutiva e corretiva do software de gestao contabil e "
    "orcamentaria com atendimento remoto e presencial",
]

BLOCOS_NAO_SOFTWARE = [
    "contratacao de empresa para execucao de servicos de pavimentacao asfaltica "
    "em vias urbanas do municipio com fornecimento de material e mao de obra",
    "aquisicao de generos alimenticios destinados a merenda escolar da rede "
    "municipal de ensino conforme cronograma anexo",
    "registro de precos para aquisicao de medicamento da atencao basica "
    "destinado as unidades de saude do municipio",
    "contratacao de servico continuado de limpeza conservacao e vigilancia "
    "das unidades administrativas",
    "aquisicao de combustivel para abastecimento da frota de veiculo oficial da "
    "administracao direta e indireta",
    "contratacao de empresa para reforma e ampliacao de obra predial em unidade "
    "escolar do municipio",
    "aquisicao de uniforme escolar destinado aos alunos matriculados na rede "
    "publica municipal de ensino",
]

BLOCOS_JURIDICOS = [
    "o presente termo de referencia tem por objeto estabelecer as condicoes "
    "gerais e as especificacoes tecnicas minimas exigidas para a contratacao",
    "a licitante devera comprovar aptidao para o desempenho de atividade "
    "pertinente e compativel em caracteristicas quantidades e prazos com o "
    "objeto desta licitacao",
    "o prazo de vigencia do contrato sera de doze meses contados da data de sua "
    "assinatura podendo ser prorrogado na forma da legislacao vigente",
    "a contratada ficara obrigada a manter durante toda a execucao do contrato "
    "as condicoes de habilitacao e qualificacao exigidas na fase de licitacao",
    "o pagamento sera efetuado mediante apresentacao de nota fiscal devidamente "
    "atestada pelo fiscal do contrato no prazo de trinta dias",
    "a inexecucao total ou parcial do contrato sujeitara a contratada as "
    "sancoes administrativas previstas no instrumento convocatorio",
    "os recursos orcamentarios correran a conta da dotacao consignada no "
    "orcamento vigente do orgao requisitante",
    "a sessao publica sera realizada por meio do sistema eletronico no sitio "
    "oficial no dia e horario indicados no preambulo deste edital",
    "e vedada a subcontratacao total do objeto admitida a subcontratacao "
    "parcial mediante previa e expressa autorizacao da contratante",
    "a garantia contratual quando exigida sera prestada em uma das modalidades "
    "previstas na legislacao a criterio da contratada",
]


def gerar_documento(rng, indice):
    orgao = rng.choice(ORGAOS)
    municipio = rng.choice(MUNICIPIOS)
    modalidade = rng.choice(MODALIDADES)
    numero = f"{rng.randint(1, 400):03d}/{rng.choice([2023, 2024, 2025])}"

    # 45% dos editais sao de software; o resto e ruido, como no mundo real
    if rng.random() < 0.45:
        tema = BLOCOS_SOFTWARE
    else:
        tema = BLOCOS_NAO_SOFTWARE

    partes = [
        f"{orgao} de {municipio} Estado do Para",
        f"{modalidade} numero {numero}",
        f"Processo administrativo {rng.randint(1000, 99999)}/{rng.choice([2023, 2024, 2025])}",
        "Objeto:",
        rng.choice(tema),
    ]
    for _ in range(rng.randint(4, 7)):
        partes.append(rng.choice(tema))

    partes.append("Das condicoes gerais")
    corpo = rng.sample(BLOCOS_JURIDICOS, k=len(BLOCOS_JURIDICOS))
    for _ in range(rng.randint(48, 76)):
        partes.append(rng.choice(corpo))
        if rng.random() < 0.35:
            partes.append(
                f"Item {rng.randint(1, 60)} valor estimado "
                f"{rng.randint(10, 900)} mil reais quantidade "
                f"{rng.randint(1, 50)} unidade"
            )
    partes.append(f"{municipio} {rng.randint(1, 28)} de mes de {rng.choice([2023, 2024, 2025])}")
    return "\n".join(partes)


def gerar(docs, saida, semente=20250922, fracao_duplicada=0.06):
    os.makedirs(saida, exist_ok=True)
    rng = random.Random(semente)
    originais = []
    n_dup = int(docs * fracao_duplicada)
    n_orig = docs - n_dup

    bytes_totais = 0
    for i in range(n_orig):
        texto = gerar_documento(rng, i)
        originais.append(texto)
        caminho = os.path.join(saida, f"edital_{i:06d}.txt")
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(texto)
        bytes_totais += len(texto)

    # republicacoes: o mesmo edital reaparece com pequena alteracao de cabecalho.
    # O corpo continua identico, entao a assinatura MinHash tem de reconhece-lo.
    for j in range(n_dup):
        base = originais[rng.randrange(n_orig)]
        linhas = base.split("\n")
        linhas[1] = f"{rng.choice(MODALIDADES)} numero {rng.randint(1, 400):03d}/2025"
        texto = "\n".join(linhas)
        caminho = os.path.join(saida, f"edital_{n_orig + j:06d}.txt")
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(texto)
        bytes_totais += len(texto)

    return docs, bytes_totais


def listar_corpus(diretorio):
    """Lista ordenada dos caminhos do corpus. A ordem e sempre a mesma, o que
    torna a divisao do trabalho reproduzivel."""
    nomes = sorted(n for n in os.listdir(diretorio) if n.endswith(".txt"))
    return [os.path.join(diretorio, n) for n in nomes]


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Gera o corpus de editais.")
    p.add_argument("--docs", type=int, default=9000)
    p.add_argument("--saida", default="dados/corpus")
    p.add_argument("--semente", type=int, default=20250922)
    a = p.parse_args()

    t0 = time.perf_counter()
    n, b = gerar(a.docs, a.saida, a.semente)
    dt = time.perf_counter() - t0
    print(f"corpus gerado: {n} documentos, {b/1_048_576:.1f} MiB, "
          f"em {dt:.1f} s, em {a.saida}")
