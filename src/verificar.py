"""
verificar.py - Prova de que a versao paralela produz o mesmo que a sequencial.

Faz duas coisas, que sao coisas diferentes:

  EQUIVALENCIA  roda a versao sequencial uma vez e a paralela uma vez, sobre a
                mesma entrada, e compara o SHA-256 do relatorio canonico.

  ESTABILIDADE  roda a versao paralela varias vezes sobre a mesma entrada e
                verifica se todas as execucoes devolvem o mesmo SHA-256. E isso
                que o criterio "resultado estavel" pede.

Com --modo nenhuma a estabilidade quebra de proposito: e a demonstracao ao vivo
da condicao de corrida. Com --modo lock ela se mantem.

Uso:
    python3 src/verificar.py --corpus dados/corpus --trabalhadores 4
    python3 src/verificar.py --corpus dados/amostra --modo nenhuma --repeticoes 10
"""

import argparse
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import nucleo
import paralelo
import sequencial
from corpus import listar_corpus

VERDE = "\033[32m"
VERMELHO = "\033[31m"
FIM = "\033[0m"


def main():
    p = argparse.ArgumentParser(description="Verificacao de equivalencia e estabilidade.")
    p.add_argument("--corpus", default="dados/corpus")
    p.add_argument("--trabalhadores", type=int, default=4)
    p.add_argument("--lote", type=int, default=150)
    p.add_argument("--repeticoes", type=int, default=5)
    p.add_argument("--modo", choices=["lock", "nenhuma", "larga"], default="lock")
    p.add_argument("--pular-sequencial", action="store_true")
    a = p.parse_args()

    caminhos = listar_corpus(a.corpus)
    print(f"corpus: {len(caminhos)} documentos em {a.corpus}")
    print(f"sincronizacao: {a.modo} | trabalhadores: {a.trabalhadores} | lote: {a.lote}")
    print("-" * 66)

    referencia = None
    if not a.pular_sequencial:
        relatorio_seq, _, _ = sequencial.executar(caminhos)
        referencia = nucleo.impressao_do_relatorio(relatorio_seq)
        print(f"sequencial          docs={relatorio_seq['documentos']:>7}  "
              f"sha256={referencia[:24]}")

    impressoes = Counter()
    for i in range(a.repeticoes):
        relatorio, _, _, _ = paralelo.executar(
            caminhos, a.trabalhadores, a.lote, a.modo)
        impressao = nucleo.impressao_do_relatorio(relatorio)
        impressoes[impressao] += 1
        marca = ""
        if referencia is not None:
            marca = "  igual ao sequencial" if impressao == referencia else \
                    "  DIFERENTE do sequencial"
        print(f"paralela  execucao {i+1:>2}  docs={relatorio['documentos']:>7}  "
              f"sha256={impressao[:24]}{marca}")

    print("-" * 66)
    estavel = len(impressoes) == 1
    equivalente = referencia is None or (estavel and referencia in impressoes)

    if estavel:
        print(f"{VERDE}ESTAVEL{FIM}: as {a.repeticoes} execucoes paralelas "
              f"produziram o mesmo resultado.")
    else:
        print(f"{VERMELHO}INSTAVEL{FIM}: {len(impressoes)} resultados distintos "
              f"em {a.repeticoes} execucoes.")
        for impressao, vezes in impressoes.most_common():
            print(f"    {impressao[:24]}  ocorreu {vezes}x")
        print("    Isto e uma condicao de corrida: os trabalhadores leem e")
        print("    escrevem o agregador global sem exclusao mutua, e uma")
        print("    atualizacao sobrescreve a outra.")

    if referencia is not None:
        if equivalente:
            print(f"{VERDE}EQUIVALENTE{FIM}: paralela e sequencial produzem o "
                  f"mesmo relatorio.")
        else:
            print(f"{VERMELHO}NAO EQUIVALENTE{FIM}: o relatorio paralelo difere "
                  f"do sequencial.")

    return 0 if (estavel and equivalente) else 1


if __name__ == "__main__":
    sys.exit(main())
