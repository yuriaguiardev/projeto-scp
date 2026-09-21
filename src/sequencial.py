"""
sequencial.py - Versao sequencial de referencia.

Um unico fluxo de execucao percorre o corpus inteiro, documento a documento, e
acumula tudo em um agregado local. Nao ha estado compartilhado, logo nao ha
secao critica e nao ha primitiva de sincronizacao: e exatamente essa ausencia
que faz desta versao a referencia contra a qual a versao paralela e comparada.

O tempo medido aqui e o T1 usado no calculo do speedup.

Uso:
    python3 src/sequencial.py --corpus dados/corpus --saida resultados/seq.json
"""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import nucleo
from corpus import listar_corpus


def executar(caminhos):
    """Devolve (relatorio, tempo_io, tempo_cpu)."""
    agregado = nucleo.agregado_vazio()
    tempo_io = 0.0
    tempo_cpu = 0.0

    for caminho in caminhos:
        t0 = time.perf_counter()
        with open(caminho, "r", encoding="utf-8") as f:
            texto = f.read()
        t1 = time.perf_counter()

        doc_id = os.path.basename(caminho)
        resultado = nucleo.processar_documento(doc_id, texto)
        nucleo.acumular(agregado, resultado)
        t2 = time.perf_counter()

        tempo_io += t1 - t0
        tempo_cpu += t2 - t1

    return nucleo.finalizar(agregado), tempo_io, tempo_cpu


def main():
    p = argparse.ArgumentParser(description="Triagem de editais - versao sequencial.")
    p.add_argument("--corpus", default="dados/corpus")
    p.add_argument("--saida", default="resultados/relatorio_sequencial.json")
    p.add_argument("--silencioso", action="store_true")
    a = p.parse_args()

    caminhos = listar_corpus(a.corpus)

    t0 = time.perf_counter()
    relatorio, t_io, t_cpu = executar(caminhos)
    tempo_total = time.perf_counter() - t0

    impressao = nucleo.impressao_do_relatorio(relatorio)
    os.makedirs(os.path.dirname(a.saida) or ".", exist_ok=True)
    with open(a.saida, "w", encoding="utf-8") as f:
        json.dump({"relatorio": relatorio, "sha256": impressao},
                  f, ensure_ascii=False, indent=2, sort_keys=True)

    medida = {
        "versao": "sequencial",
        "trabalhadores": 1,
        "documentos": relatorio["documentos"],
        "tempo_total_s": round(tempo_total, 4),
        "tempo_leitura_s": round(t_io, 4),
        "tempo_processamento_s": round(t_cpu, 4),
        "sha256": impressao,
    }
    if not a.silencioso:
        print(json.dumps(medida, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(medida, ensure_ascii=False))
    return medida


if __name__ == "__main__":
    main()
