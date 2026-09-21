"""
calibrar.py - Dimensiona o corpus para a maquina onde a medicao vai acontecer.

O enunciado exige que a versao sequencial leve minutos, e nao segundos. Quantos
documentos sao necessarios para isso depende da maquina. Em vez de chutar um
numero, medimos o custo por documento na propria instancia e calculamos.

Uso (na instancia EC2, antes de gerar o corpus definitivo):
    python3 src/calibrar.py --alvo-minutos 4
"""

import argparse
import os
import shutil
import statistics
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import corpus as mod_corpus
import sequencial


def main():
    p = argparse.ArgumentParser(description="Calibra o volume da entrada.")
    p.add_argument("--alvo-minutos", type=float, default=4.0)
    p.add_argument("--amostra", type=int, default=150)
    p.add_argument("--repeticoes", type=int, default=3)
    a = p.parse_args()

    temporario = tempfile.mkdtemp(prefix="calibracao_")
    try:
        mod_corpus.gerar(a.amostra, temporario)
        caminhos = mod_corpus.listar_corpus(temporario)
        bytes_totais = sum(os.path.getsize(c) for c in caminhos)

        tempos = []
        for _ in range(a.repeticoes):
            t0 = time.perf_counter()
            sequencial.executar(caminhos)
            tempos.append(time.perf_counter() - t0)
        mediano = statistics.median(tempos)
    finally:
        shutil.rmtree(temporario, ignore_errors=True)

    por_documento = mediano / a.amostra
    alvo_s = a.alvo_minutos * 60
    recomendado = int(round(alvo_s / por_documento / 500.0)) * 500
    recomendado = max(recomendado, 1000)
    tamanho_gb = recomendado * (bytes_totais / a.amostra) / 1_073_741_824

    print(f"nucleos logicos      : {os.cpu_count()}")
    print(f"amostra              : {a.amostra} documentos")
    print(f"custo por documento  : {por_documento*1000:.1f} ms")
    print(f"tamanho medio do doc : {bytes_totais/a.amostra/1024:.1f} KiB")
    print()
    print(f"para {a.alvo_minutos:.0f} minutos de execucao sequencial:")
    print(f"  documentos recomendados : {recomendado}")
    print(f"  espaco em disco         : {tamanho_gb:.2f} GiB")
    print(f"  tempo sequencial previsto: {recomendado*por_documento/60:.1f} min")
    print()
    print(f"  python3 src/corpus.py --docs {recomendado} --saida dados/corpus")


if __name__ == "__main__":
    main()
