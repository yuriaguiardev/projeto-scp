"""
paralelo.py - Versao paralela, com processos, memoria compartilhada e lock.

Desenho
-------
  - Paralelismo de DADOS: o corpus e cortado em lotes e cada trabalhador recebe
    lotes diferentes. A unidade de trabalho e um edital; editais nao dependem
    uns dos outros.
  - PROCESSOS, nao threads: o trabalho e limitado por processador (hashing e
    regex em Python puro). Em CPython o GIL impede que threads executem
    bytecode em paralelo, entao a versao com threads mediria speedup proximo de
    1. Ha um modo --motor thread justamente para demonstrar isso ao vivo.
  - ESTADO COMPARTILHADO: um agregador global, mantido por um Manager e escrito
    por todos os trabalhadores.
  - SECAO CRITICA: a fusao do parcial de um lote no agregador global. E o menor
    trecho que precisa ser indivisivel. Cada trabalhador processa o lote inteiro
    fora da trava e so entra nela para fundir.
  - CARIMBO LOGICO: relogio de Lamport, avancado a cada fusao, gravado no
    registro de eventos.

Modos de demonstracao
---------------------
  --sincronizacao lock    (padrao) secao critica minima, protegida por Lock
  --sincronizacao nenhuma sem trava: mostra a condicao de corrida ao vivo
  --sincronizacao larga   trava em volta do laco inteiro: correto, mas serial

Uso:
    python3 src/paralelo.py --corpus dados/corpus --trabalhadores 4
"""

import argparse
import json
import multiprocessing as mp
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import nucleo
from corpus import listar_corpus

SENTINELA = None


# ---------------------------------------------------------------------------
# Secao critica
# ---------------------------------------------------------------------------

def fundir_no_global(estado, assinaturas, eventos, parcial, relogio_local,
                     identificador, lote_id):
    """
    SECAO CRITICA DO PROJETO.

    Todo o corpo desta funcao e executado sob a trava. Ele faz leitura seguida
    de escrita sobre objetos que os outros trabalhadores tambem escrevem:

      estado["documentos"] = estado["documentos"] + parcial["documentos"]

    Sem trava, dois trabalhadores podem ler o mesmo valor antigo e gravar por
    cima um do outro (atualizacao perdida). O dicionario de assinaturas sofre do
    mesmo problema na forma classica de verificar-entao-agir: dois trabalhadores
    perguntam se a assinatura ja existe, os dois recebem "nao", e o duplicado
    deixa de ser contado.

    Devolve o novo valor do relogio logico local.
    """
    # Relogio de Lamport: evento de fusao. O trabalhador adianta o proprio
    # relogio para depois do ultimo evento ja registrado no estado global.
    relogio = max(relogio_local, estado["relogio"]) + 1
    estado["relogio"] = relogio

    # Escalares: leitura-modificacao-escrita
    estado["documentos"] = estado["documentos"] + parcial["documentos"]
    estado["tokens"] = estado["tokens"] + parcial["tokens"]
    estado["pontuacao_total"] = estado["pontuacao_total"] + parcial["pontuacao_total"]

    # Dicionarios pequenos: leitura-modificacao-escrita do valor inteiro
    termos = estado["termos"]
    for termo, contagem in parcial["termos"].items():
        termos[termo] = termos.get(termo, 0) + contagem
    estado["termos"] = termos

    linhas = estado["linhas"]
    for linha, contagem in parcial["linhas"].items():
        linhas[linha] = linhas.get(linha, 0) + contagem
    estado["linhas"] = linhas

    # Ranking: mantem so os melhores, para nao crescer sem limite
    topo = estado["top"]
    topo.extend(parcial["top"])
    topo.sort(key=lambda par: (-par[0], par[1]))
    estado["top"] = topo[:25]

    # Assinaturas: verificar-entao-agir chave a chave
    duplicados = parcial["duplicados"]
    for chave, doc_id in parcial["assinaturas"].items():
        anterior = assinaturas.get(chave)
        if anterior is None:
            assinaturas[chave] = doc_id
        else:
            duplicados += 1
            if doc_id < anterior:
                assinaturas[chave] = doc_id
    estado["duplicados"] = estado["duplicados"] + duplicados

    # Registro de evento com carimbo logico
    eventos.append({
        "quem": identificador,
        "o_que": "fusao_no_agregador_global",
        "carimbo_logico": relogio,
        "sobre_o_que": f"lote={lote_id} documentos={parcial['documentos']}",
    })
    return relogio


# ---------------------------------------------------------------------------
# Trabalhador
# ---------------------------------------------------------------------------

def trabalhador(identificador, fila, estado, assinaturas, eventos, lock, modo):
    relogio_local = 0
    lotes = 0
    tempo_esperando = 0.0
    tempo_processando = 0.0

    while True:
        item = fila.get()
        if item is SENTINELA:
            break
        lote_id, caminhos = item
        relogio_local += 1  # evento local: recebimento de lote

        if modo == "larga":
            # Trava em volta do laco inteiro. Correto, mas serializa todo o
            # trabalho: existe apenas para a demonstracao de que correcao e
            # paralelismo sao coisas diferentes.
            t_espera = time.perf_counter()
            lock.acquire()
            tempo_esperando += time.perf_counter() - t_espera
            try:
                t0 = time.perf_counter()
                parcial = _processar_lote(caminhos)
                tempo_processando += time.perf_counter() - t0
                relogio_local = fundir_no_global(
                    estado, assinaturas, eventos, parcial,
                    relogio_local, identificador, lote_id)
            finally:
                lock.release()
        else:
            t0 = time.perf_counter()
            parcial = _processar_lote(caminhos)
            tempo_processando += time.perf_counter() - t0

            if modo == "lock":
                t_espera = time.perf_counter()
                lock.acquire()
                tempo_esperando += time.perf_counter() - t_espera
                try:
                    relogio_local = fundir_no_global(
                        estado, assinaturas, eventos, parcial,
                        relogio_local, identificador, lote_id)
                finally:
                    lock.release()
            else:  # modo == "nenhuma": sem protecao, de proposito
                relogio_local = fundir_no_global(
                    estado, assinaturas, eventos, parcial,
                    relogio_local, identificador, lote_id)
        lotes += 1

    estado[f"perfil_{identificador}"] = {
        "lotes": lotes,
        "processando_s": round(tempo_processando, 4),
        "esperando_trava_s": round(tempo_esperando, 4),
        "relogio_final": relogio_local,
    }


def _processar_lote(caminhos):
    """Processa um lote inteiro FORA da trava, acumulando num parcial local."""
    parcial = nucleo.agregado_vazio()
    for caminho in caminhos:
        with open(caminho, "r", encoding="utf-8") as f:
            texto = f.read()
        resultado = nucleo.processar_documento(os.path.basename(caminho), texto)
        nucleo.acumular(parcial, resultado)
    parcial["top"].sort(key=lambda par: (-par[0], par[1]))
    del parcial["top"][25:]
    return parcial


# ---------------------------------------------------------------------------
# Orquestracao
# ---------------------------------------------------------------------------

def dividir_em_lotes(caminhos, tamanho):
    return [(i // tamanho, caminhos[i:i + tamanho])
            for i in range(0, len(caminhos), tamanho)]


def executar(caminhos, trabalhadores, tamanho_lote, modo="lock", motor="processo"):
    if motor == "thread":
        import threading
        import queue
        Fila, Fluxo, Trava = queue.Queue, threading.Thread, threading.Lock
        gerente = None
        estado = {"documentos": 0, "tokens": 0, "pontuacao_total": 0,
                  "termos": {}, "linhas": {}, "top": [], "duplicados": 0,
                  "relogio": 0}
        assinaturas, eventos, lock = {}, [], Trava()
        fila = Fila()
    else:
        gerente = mp.Manager()
        estado = gerente.dict({
            "documentos": 0, "tokens": 0, "pontuacao_total": 0,
            "termos": {}, "linhas": {}, "top": [], "duplicados": 0,
            "relogio": 0,
        })
        assinaturas = gerente.dict()
        eventos = gerente.list()
        lock = mp.Lock()
        fila = mp.Queue()
        Fluxo = mp.Process

    lotes = dividir_em_lotes(caminhos, tamanho_lote)
    for lote in lotes:
        fila.put(lote)
    for _ in range(trabalhadores):
        fila.put(SENTINELA)

    fluxos = []
    for i in range(trabalhadores):
        f = Fluxo(target=trabalhador,
                  args=(f"w{i}", fila, estado, assinaturas, eventos, lock, modo))
        f.start()
        fluxos.append(f)
    for f in fluxos:
        f.join()

    agregado = {
        "documentos": estado["documentos"],
        "tokens": estado["tokens"],
        "pontuacao_total": estado["pontuacao_total"],
        "termos": dict(estado["termos"]),
        "linhas": dict(estado["linhas"]),
        "top": list(estado["top"]),
        "duplicados": estado["duplicados"],
        "assinaturas": dict(assinaturas),
    }
    perfis = {k: estado[k] for k in estado.keys() if str(k).startswith("perfil_")}
    registro = [dict(e) for e in eventos]

    relatorio = nucleo.finalizar(agregado)
    if gerente is not None:
        gerente.shutdown()
    return relatorio, perfis, registro, len(lotes)


def main():
    p = argparse.ArgumentParser(description="Triagem de editais - versao paralela.")
    p.add_argument("--corpus", default="dados/corpus")
    p.add_argument("--trabalhadores", type=int, default=os.cpu_count())
    p.add_argument("--lote", type=int, default=150)
    p.add_argument("--sincronizacao", choices=["lock", "nenhuma", "larga"],
                   default="lock")
    p.add_argument("--motor", choices=["processo", "thread"], default="processo")
    p.add_argument("--saida", default="resultados/relatorio_paralelo.json")
    p.add_argument("--eventos", default=None,
                   help="grava o registro de eventos com carimbo logico")
    p.add_argument("--silencioso", action="store_true")
    a = p.parse_args()

    caminhos = listar_corpus(a.corpus)

    t0 = time.perf_counter()
    relatorio, perfis, registro, n_lotes = executar(
        caminhos, a.trabalhadores, a.lote, a.sincronizacao, a.motor)
    tempo_total = time.perf_counter() - t0

    impressao = nucleo.impressao_do_relatorio(relatorio)
    os.makedirs(os.path.dirname(a.saida) or ".", exist_ok=True)
    with open(a.saida, "w", encoding="utf-8") as f:
        json.dump({"relatorio": relatorio, "sha256": impressao},
                  f, ensure_ascii=False, indent=2, sort_keys=True)

    if a.eventos:
        registro.sort(key=lambda e: (e["carimbo_logico"], e["quem"]))
        os.makedirs(os.path.dirname(a.eventos) or ".", exist_ok=True)
        with open(a.eventos, "w", encoding="utf-8") as f:
            json.dump(registro, f, ensure_ascii=False, indent=2)

    espera = sum(v["esperando_trava_s"] for v in perfis.values())
    medida = {
        "versao": "paralela",
        "motor": a.motor,
        "sincronizacao": a.sincronizacao,
        "trabalhadores": a.trabalhadores,
        "lotes": n_lotes,
        "tamanho_lote": a.lote,
        "documentos": relatorio["documentos"],
        "tempo_total_s": round(tempo_total, 4),
        "espera_acumulada_na_trava_s": round(espera, 4),
        "sha256": impressao,
        "perfil_por_trabalhador": perfis,
    }
    print(json.dumps(medida, ensure_ascii=False,
                     indent=None if a.silencioso else 2))
    return medida


if __name__ == "__main__":
    main()
