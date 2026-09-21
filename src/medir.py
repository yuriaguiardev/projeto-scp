"""
medir.py - Bancada de medicao.

Mede o tempo sequencial e o tempo paralelo na MESMA maquina, com a MESMA
entrada, repetindo cada configuracao, e calcula:

  speedup medido      S(n) = T(1) / T(n), com T(1) da versao sequencial
  eficiencia          E(n) = S(n) / n
  teto de Amdahl      S_max(n) = 1 / ( (1-p) + p/n )
  fracao serial       e(n) = (1/S - 1/n) / (1 - 1/n)        [metrica de Karp-Flatt]

A fracao paralelizavel p e estimada de duas formas independentes, e as duas
entram no relatorio:

  p_instrumentado  medido dentro da versao sequencial, como a razao entre o
                   tempo gasto no trabalho por documento e o tempo total.
  p_karp_flatt     deduzido do proprio speedup medido, por e = 1 - p.

Uso:
    python3 src/medir.py --corpus dados/corpus --trabalhadores 1 2 4 --repeticoes 3
"""

import argparse
import json
import os
import platform
import statistics
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import nucleo
import paralelo
import sequencial
from corpus import listar_corpus


def amdahl(p, n):
    return 1.0 / ((1.0 - p) + p / n)


def karp_flatt(speedup, n):
    if n <= 1:
        return None
    return ((1.0 / speedup) - (1.0 / n)) / (1.0 - (1.0 / n))


def descrever_maquina():
    info = {
        "sistema": f"{platform.system()} {platform.release()}",
        "python": platform.python_version(),
        "arquitetura": platform.machine(),
        "nucleos_logicos": os.cpu_count(),
    }
    # Sem lscpu o pipeline abaixo nao falha: ele devolve zero, porque `wc -l`
    # conta as linhas de uma saida vazia. Um zero aqui viraria "8 vCPU sobre 0
    # nucleos fisicos" no relatorio, entao qualquer valor nao positivo e
    # tratado como ausencia de informacao e a busca continua.
    info["nucleos_fisicos"] = None
    for comando, usa_shell in (
            ("lscpu -p=CORE | grep -v '^#' | sort -u | wc -l", True),   # Linux
            (["sysctl", "-n", "hw.physicalcpu"], False),                # macOS
    ):
        try:
            valor = int(subprocess.check_output(
                comando, shell=usa_shell, text=True,
                stderr=subprocess.DEVNULL).strip())
        except Exception:
            continue
        if valor > 0:
            info["nucleos_fisicos"] = valor
            break
    try:
        with open("/proc/cpuinfo") as f:
            for linha in f:
                if linha.startswith("model name"):
                    info["modelo"] = linha.split(":", 1)[1].strip()
                    break
    except Exception:
        pass
    if "modelo" not in info:
        try:
            info["modelo"] = subprocess.check_output(
                ["sysctl", "-n", "machdep.cpu.brand_string"], text=True).strip()
        except Exception:
            pass
    try:
        info["tipo_instancia"] = subprocess.check_output(
            ["curl", "-s", "--max-time", "2",
             "http://169.254.169.254/latest/meta-data/instance-type"],
            text=True).strip() or None
        info["zona"] = subprocess.check_output(
            ["curl", "-s", "--max-time", "2",
             "http://169.254.169.254/latest/meta-data/placement/availability-zone"],
            text=True).strip() or None
    except Exception:
        pass
    return info


def main():
    p = argparse.ArgumentParser(description="Medicao de desempenho.")
    p.add_argument("--corpus", default="dados/corpus")
    p.add_argument("--trabalhadores", type=int, nargs="+", default=[1, 2, 4])
    p.add_argument("--repeticoes", type=int, default=3)
    p.add_argument("--lote", type=int, default=150)
    p.add_argument("--com-thread", action="store_true",
                   help="mede tambem a versao com threads, para mostrar o GIL")
    p.add_argument("--saida", default="resultados/medicao.json")
    p.add_argument("--eventos", default="resultados/eventos.json",
                   help="registro de eventos com carimbo logico de Lamport")
    a = p.parse_args()

    caminhos = listar_corpus(a.corpus)
    maquina = descrever_maquina()
    print(json.dumps(maquina, ensure_ascii=False, indent=2))
    print(f"\ncorpus: {len(caminhos)} documentos\n")

    # ---------------- sequencial ----------------
    tempos_seq, fracoes = [], []
    impressao_ref = None
    for i in range(a.repeticoes):
        t0 = time.perf_counter()
        relatorio, t_io, t_cpu = sequencial.executar(caminhos)
        dt = time.perf_counter() - t0
        tempos_seq.append(dt)
        fracoes.append(t_cpu / dt)
        impressao = nucleo.impressao_do_relatorio(relatorio)
        impressao_ref = impressao_ref or impressao
        print(f"sequencial  rep {i+1}: {dt:8.2f} s   "
              f"(trabalho por documento: {100*t_cpu/dt:5.1f} %)", flush=True)

    t1 = statistics.median(tempos_seq)
    p_instrumentado = statistics.median(fracoes)
    print(f"\nT(1) mediano = {t1:.2f} s   p instrumentado = {p_instrumentado:.4f}\n",
          flush=True)

    # ---------------- paralelo ----------------
    linhas = []
    configuracoes = [("processo", n) for n in a.trabalhadores]
    if a.com_thread:
        configuracoes += [("thread", n) for n in a.trabalhadores if n > 1]

    registro_exemplo = None      # eventos da maior configuracao de processos
    n_maior = max(a.trabalhadores)
    for motor, n in configuracoes:
        tempos, esperas, impressoes = [], [], set()
        for i in range(a.repeticoes):
            t0 = time.perf_counter()
            relatorio, perfis, registro, n_lotes = paralelo.executar(
                caminhos, n, a.lote, "lock", motor)
            if motor == "processo" and n == n_maior and registro_exemplo is None:
                registro_exemplo = registro
            dt = time.perf_counter() - t0
            tempos.append(dt)
            esperas.append(sum(v["esperando_trava_s"] for v in perfis.values()))
            impressoes.add(nucleo.impressao_do_relatorio(relatorio))
            print(f"{motor:9} n={n}  rep {i+1}: {dt:8.2f} s", flush=True)

        tn = statistics.median(tempos)
        s = t1 / tn
        linha = {
            "motor": motor,
            "trabalhadores": n,
            "tempos_s": [round(x, 3) for x in tempos],
            "tempo_mediano_s": round(tn, 3),
            "speedup": round(s, 3),
            "eficiencia": round(s / n, 3),
            "amdahl_teto": round(amdahl(p_instrumentado, n), 3),
            "karp_flatt_e": (round(karp_flatt(s, n), 4)
                             if karp_flatt(s, n) is not None else None),
            "espera_na_trava_s": round(statistics.median(esperas), 3),
            "resultado_estavel": len(impressoes) == 1,
            "igual_ao_sequencial": impressoes == {impressao_ref},
        }
        linhas.append(linha)
        print(f"          -> S={s:.2f}  E={s/n:.2f}  teto Amdahl="
              f"{amdahl(p_instrumentado, n):.2f}\n", flush=True)

    medicao = {
        "gerado_em": time.strftime("%Y-%m-%d %H:%M:%S"),
        "maquina": maquina,
        "corpus": {"diretorio": a.corpus, "documentos": len(caminhos),
                   "bytes": sum(os.path.getsize(c) for c in caminhos)},
        "tamanho_lote": a.lote,
        "repeticoes": a.repeticoes,
        "trabalhadores_medidos": list(a.trabalhadores),
        "sequencial": {
            "tempos_s": [round(x, 3) for x in tempos_seq],
            "tempo_mediano_s": round(t1, 3),
            "p_instrumentado": round(p_instrumentado, 4),
            "sha256": impressao_ref,
        },
        "paralelo": linhas,
    }
    os.makedirs(os.path.dirname(a.saida) or ".", exist_ok=True)
    with open(a.saida, "w", encoding="utf-8") as f:
        json.dump(medicao, f, ensure_ascii=False, indent=2)

    # Registro de eventos com carimbo logico. E citado na ficha (secao C) e no
    # relatorio (secao 3.2) como parte da entrega, entao a bancada o grava junto
    # com a medicao, ordenado por carimbo de Lamport.
    if registro_exemplo:
        registro_exemplo.sort(key=lambda e: (e["carimbo_logico"], e["quem"]))
        with open(a.eventos, "w", encoding="utf-8") as f:
            json.dump(registro_exemplo, f, ensure_ascii=False, indent=2)
        medicao["eventos"] = {
            "arquivo": a.eventos,
            "fusoes": len(registro_exemplo),
            "trabalhadores": n_maior,
            "carimbo_maximo": max(e["carimbo_logico"] for e in registro_exemplo),
        }
        with open(a.saida, "w", encoding="utf-8") as f:
            json.dump(medicao, f, ensure_ascii=False, indent=2)
        print(f"eventos gravados em {a.eventos} "
              f"({len(registro_exemplo)} fusoes, carimbo maximo "
              f"{medicao['eventos']['carimbo_maximo']})")

    # ---------------- tabela final ----------------
    print("=" * 78)
    print(f"{'motor':10}{'n':>3}{'T(n) s':>10}{'S medido':>10}{'teto Amdahl':>13}"
          f"{'E':>7}{'e Karp-Flatt':>14}{'estavel':>9}")
    print("-" * 78)
    print(f"{'sequencial':10}{1:>3}{t1:>10.2f}{1.0:>10.2f}{1.0:>13.2f}"
          f"{1.0:>7.2f}{'-':>14}{'sim':>9}")
    for l in linhas:
        e = f"{l['karp_flatt_e']:.4f}" if l["karp_flatt_e"] is not None else "-"
        print(f"{l['motor']:10}{l['trabalhadores']:>3}{l['tempo_mediano_s']:>10.2f}"
              f"{l['speedup']:>10.2f}{l['amdahl_teto']:>13.2f}"
              f"{l['eficiencia']:>7.2f}{e:>14}"
              f"{('sim' if l['resultado_estavel'] else 'NAO'):>9}")
    print("=" * 78)
    print(f"\nmedicao gravada em {a.saida}")


if __name__ == "__main__":
    main()
