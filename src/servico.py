"""
servico.py - Servico HTTP da aplicacao, na porta 8000.

E a unica porta que o grupo de seguranca abre para a internet. A porta 22 fica
restrita ao endereco da equipe. O servico existe para que a demonstracao ao vivo
dispare as execucoes e mostre os tempos pelo navegador, sem depender de um
terminal aberto na instancia.

Rotas
    GET  /                    painel em HTML
    GET  /api/estado          estado atual em JSON
    GET  /api/executar?...    dispara uma execucao em segundo plano
    GET  /api/saude           verificacao de vida, para o grupo de seguranca

Parametros de /api/executar
    versao         sequencial | paralela
    trabalhadores  inteiro
    sincronizacao  lock | nenhuma | larga
    motor          processo | thread

Uso:
    python3 src/servico.py --corpus dados/corpus --porta 8000
"""

import argparse
import html
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import nucleo
import paralelo
import sequencial
from corpus import listar_corpus
from medir import amdahl, descrever_maquina, karp_flatt

ESTADO = {
    "ocupado": False,
    "corpus": None,
    "documentos": 0,
    "maquina": {},
    "historico": [],
    "tempo_sequencial_s": None,
    # Fracao paralelizavel usada para o teto de Amdahl mostrado no painel.
    # Nunca e arbitrada: vem de resultados/medicao.json quando a bancada ja
    # rodou, ou da propria execucao sequencial disparada pelo painel, que
    # cronometra separadamente a leitura e o trabalho por documento. Enquanto
    # nenhuma das duas existir, a coluna do teto fica vazia, em vez de exibir
    # um numero inventado.
    "p_paralelizavel": None,
    "origem_p": "ainda nao medido",
    # A ultima triagem produzida. O painel mostrava so o desempenho e descartava
    # o resultado - que e o que a aplicacao existe para produzir. Guarda-se o
    # relatorio da execucao mais recente para exibi-lo.
    "ultimo_relatorio": None,
}
TRAVA_ESTADO = threading.Lock()


def carregar_p_da_medicao(caminho="resultados/medicao.json"):
    """Le a fracao paralelizavel instrumentada da ultima medicao, se houver."""
    try:
        with open(caminho, encoding="utf-8") as arq:
            medicao = json.load(arq)
        valor = medicao["sequencial"]["p_instrumentado"]
    except Exception:
        return False
    if not isinstance(valor, (int, float)):
        return False
    ESTADO["p_paralelizavel"] = valor
    ESTADO["origem_p"] = f"instrumentado em {caminho}"
    return True


def executar_em_segundo_plano(parametros):
    caminhos = listar_corpus(ESTADO["corpus"])
    versao = parametros.get("versao", ["paralela"])[0]
    n = int(parametros.get("trabalhadores", [os.cpu_count()])[0])
    modo = parametros.get("sincronizacao", ["lock"])[0]
    motor = parametros.get("motor", ["processo"])[0]
    lote = int(parametros.get("lote", [150])[0])

    inicio = time.perf_counter()
    p_medido = None
    if versao == "sequencial":
        relatorio, _, t_cpu = sequencial.executar(caminhos)
        n, modo, motor = 1, "nao_se_aplica", "unico_fluxo"
        espera = 0.0
    else:
        relatorio, perfis, _, _ = paralelo.executar(caminhos, n, lote, modo, motor)
        espera = sum(v["esperando_trava_s"] for v in perfis.values())
    duracao = time.perf_counter() - inicio
    if versao == "sequencial" and duracao > 0:
        # p instrumentado: razao entre o trabalho por documento e o tempo total
        # desta mesma execucao. E a definicao usada em medir.py.
        p_medido = t_cpu / duracao

    entrada = {
        "quando": time.strftime("%H:%M:%S"),
        "versao": versao,
        "motor": motor,
        "sincronizacao": modo,
        "trabalhadores": n,
        "tempo_s": round(duracao, 2),
        "documentos": relatorio["documentos"],
        "duplicados": relatorio["documentos_duplicados"],
        "sha256": nucleo.impressao_do_relatorio(relatorio),
        "espera_na_trava_s": round(espera, 2),
        "speedup": None,
        "teto_amdahl": None,
        "karp_flatt_e": None,
    }

    with TRAVA_ESTADO:
        ESTADO["ultimo_relatorio"] = relatorio
        if versao == "sequencial":
            ESTADO["tempo_sequencial_s"] = duracao
            if p_medido is not None:
                ESTADO["p_paralelizavel"] = round(p_medido, 4)
                ESTADO["origem_p"] = "instrumentado na execucao sequencial deste painel"
        t1 = ESTADO["tempo_sequencial_s"]
        if t1 and versao != "sequencial":
            entrada["speedup"] = round(t1 / duracao, 2)
            entrada["karp_flatt_e"] = (round(karp_flatt(t1 / duracao, n), 4)
                                       if n > 1 else None)
            p = ESTADO["p_paralelizavel"]
            if p:
                entrada["teto_amdahl"] = round(amdahl(p, n), 2)
        ESTADO["historico"].insert(0, entrada)
        del ESTADO["historico"][20:]
        ESTADO["ocupado"] = False


PAGINA = """<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Triagem de editais - Sistemas Distribuidos e Paralelos</title>
<style>
 :root {{ color-scheme: light dark; --linha: #d6d3cd; --fundo: #faf9f7;
          --texto: #1c1b19; --suave: #6b6862; --destaque: #8a4b2a; }}
 @media (prefers-color-scheme: dark) {{ :root {{ --linha:#3a3733; --fundo:#1a1917;
          --texto:#ece9e3; --suave:#9b968d; --destaque:#d99a6c; }} }}
 * {{ box-sizing: border-box; }}
 body {{ margin:0; padding:2rem 1.25rem; background:var(--fundo); color:var(--texto);
        font:15px/1.55 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;
        max-width: 60rem; margin-inline:auto; }}
 h1 {{ font-size:1.35rem; margin:0 0 .25rem; }}
 p.sub {{ color:var(--suave); margin:0 0 1.5rem; font-size:.9rem; }}
 fieldset {{ border:1px solid var(--linha); border-radius:8px; padding:1rem;
             margin:0 0 1.25rem; }}
 legend {{ font-size:.8rem; text-transform:uppercase; letter-spacing:.06em;
           color:var(--suave); padding:0 .4rem; }}
 a.botao {{ display:inline-block; margin:.2rem .35rem .2rem 0; padding:.5rem .85rem;
            border:1px solid var(--linha); border-radius:6px; text-decoration:none;
            color:var(--texto); background:transparent; font-size:.88rem; }}
 a.botao:hover {{ border-color:var(--destaque); color:var(--destaque); }}
 table {{ border-collapse:collapse; width:100%; font-size:.85rem; }}
 th,td {{ text-align:left; padding:.45rem .5rem; border-bottom:1px solid var(--linha);
          white-space:nowrap; }}
 th {{ color:var(--suave); font-weight:600; font-size:.78rem; }}
 td.mono {{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:.8rem; }}
 .rolagem {{ overflow-x:auto; }}
 .estado {{ font-size:.85rem; color:var(--suave); margin-bottom:1rem; }}
 .ocupado {{ color:var(--destaque); font-weight:600; }}
</style></head><body>
<h1>Triagem paralela de editais de compra publica</h1>
<p class="sub">070080 Sistemas Distribuidos e Paralelos &middot; Etapa 1 &middot;
 {maquina}</p>
<div class="estado">Corpus: <strong>{documentos}</strong> documentos em
 <span class="mono">{corpus}</span> &middot; nucleos logicos:
 <strong>{nucleos}</strong> &middot; estado: <span class="{classe}">{situacao}</span></div>
<div class="estado">Fracao paralelizavel p = <strong>{p}</strong>
 <span title="{origem_p}">({origem_p})</span> &middot; o teto de Amdahl da tabela
 usa este p, e S = T(1)/T(n) usa o T(1) da versao sequencial.</div>
<fieldset><legend>Executar</legend>
 <a class="botao" href="/api/executar?versao=sequencial">sequencial (1 fluxo)</a>
 {botoes}
 <a class="botao" href="/api/executar?versao=paralela&amp;sincronizacao=nenhuma&amp;trabalhadores={nucleos}">sem trava (condicao de corrida)</a>
 <a class="botao" href="/api/executar?versao=paralela&amp;sincronizacao=larga&amp;trabalhadores={nucleos}">trava larga (serializa)</a>
 <a class="botao" href="/api/executar?versao=paralela&amp;motor=thread&amp;trabalhadores={nucleos}">threads (GIL)</a>
</fieldset>
<fieldset><legend>Execucoes</legend><div class="rolagem">{tabela}</div></fieldset>
<fieldset><legend>Resultado da triagem</legend>{triagem}</fieldset>
<script>setTimeout(function(){{location.reload();}}, 3000);</script>
</body></html>"""


def montar_triagem(relatorio):
    """A saida da aplicacao: ranking, linhas de produto e termos."""
    if not relatorio:
        return ("<p style='color:var(--suave)'>Rode uma execucao para ver o "
                "resultado da triagem.</p>")

    topo = "".join(
        f"<tr><td>{i}</td><td class='mono'>{html.escape(e['doc_id'])}</td>"
        f"<td style='text-align:right'><strong>{e['pontuacao']}</strong></td></tr>"
        for i, e in enumerate(relatorio["top"][:10], 1))

    total = max(relatorio["documentos"], 1)
    linhas = "".join(
        f"<tr><td>{html.escape(nome)}</td>"
        f"<td style='text-align:right'>{n}</td>"
        f"<td style='width:55%'><span style='display:inline-block; height:.7rem; "
        f"background:var(--destaque); width:{100*n/total:.1f}%'></span></td></tr>"
        for nome, n in sorted(relatorio["linhas"], key=lambda p: -p[1]))

    termos = "".join(
        f"<tr><td class='mono'>{html.escape(t)}</td>"
        f"<td style='text-align:right'>{n}</td></tr>"
        for t, n in relatorio["termos"][:12])

    return (
        "<div style='display:flex; gap:2rem; flex-wrap:wrap; align-items:start'>"
        "<div style='flex:1; min-width:19rem'>"
        "<h2 style='font-size:.8rem; text-transform:uppercase; letter-spacing:.06em;"
        " color:var(--suave); font-weight:600; margin:0 0 .5rem'>Editais mais aderentes</h2>"
        f"<table><tr><th>#</th><th>documento</th><th style='text-align:right'>pontuacao</th></tr>{topo}</table></div>"
        "<div style='flex:1; min-width:19rem'>"
        "<h2 style='font-size:.8rem; text-transform:uppercase; letter-spacing:.06em;"
        " color:var(--suave); font-weight:600; margin:0 0 .5rem'>Linha de produto</h2>"
        f"<table>{linhas}</table>"
        "<h2 style='font-size:.8rem; text-transform:uppercase; letter-spacing:.06em;"
        " color:var(--suave); font-weight:600; margin:1.25rem 0 .5rem'>Termos da taxonomia</h2>"
        f"<table>{termos}</table></div></div>"
        f"<p style='margin-top:1rem; font-size:.85rem; color:var(--suave)'>"
        f"{relatorio['documentos']} documentos &middot; "
        f"{relatorio['assinaturas_distintas']} assinaturas distintas &middot; "
        f"<strong>{relatorio['documentos_duplicados']}</strong> republicacoes "
        f"reconhecidas pelo MinHash &middot; {relatorio['tokens']:,} tokens</p>".replace(",", "."))


def montar_pagina():
    with TRAVA_ESTADO:
        historico = list(ESTADO["historico"])
        ocupado = ESTADO["ocupado"]
        relatorio = ESTADO["ultimo_relatorio"]
    nucleos = os.cpu_count()

    botoes = "".join(
        f'<a class="botao" href="/api/executar?versao=paralela&amp;'
        f'trabalhadores={n}">paralela n={n}</a>'
        for n in sorted({1, 2, nucleos // 2 or 1, nucleos}) if n >= 1
    )

    if historico:
        cabecalho = ("<tr><th>hora</th><th>versao</th><th>motor</th><th>sincr.</th>"
                     "<th>n</th><th>T (s)</th><th>speedup</th><th>teto</th>"
                     "<th>e (Karp-Flatt)</th>"
                     "<th>docs</th><th>dup.</th><th>espera trava</th>"
                     "<th>sha256</th></tr>")
        corpo = "".join(
            "<tr>"
            f"<td>{e['quando']}</td><td>{e['versao']}</td><td>{e['motor']}</td>"
            f"<td>{e['sincronizacao']}</td><td>{e['trabalhadores']}</td>"
            f"<td><strong>{e['tempo_s']}</strong></td>"
            f"<td>{e['speedup'] if e['speedup'] else '-'}</td>"
            f"<td>{e['teto_amdahl'] if e['teto_amdahl'] else '-'}</td>"
            f"<td>{e.get('karp_flatt_e') if e.get('karp_flatt_e') else '-'}</td>"
            f"<td>{e['documentos']}</td><td>{e['duplicados']}</td>"
            f"<td>{e['espera_na_trava_s']}</td>"
            f"<td class='mono'>{e['sha256'][:16]}</td></tr>"
            for e in historico)
        tabela = f"<table>{cabecalho}{corpo}</table>"
    else:
        tabela = "<p style='color:var(--suave)'>Nenhuma execucao ainda.</p>"

    with TRAVA_ESTADO:
        p_atual = ESTADO["p_paralelizavel"]
        origem_p = ESTADO["origem_p"]
    maquina = ESTADO["maquina"]
    descricao = maquina.get("tipo_instancia") or maquina.get("modelo") or \
        maquina.get("arquitetura", "")
    if maquina.get("zona"):
        descricao = f"{descricao} &middot; {maquina['zona']}"

    return PAGINA.format(
        maquina=html.escape(str(descricao), quote=False),
        documentos=ESTADO["documentos"],
        corpus=html.escape(str(ESTADO["corpus"])),
        nucleos=nucleos,
        classe="ocupado" if ocupado else "",
        situacao="executando..." if ocupado else "ocioso",
        botoes=botoes,
        tabela=tabela,
        triagem=montar_triagem(relatorio),
        p=(f"{p_atual:.4f}".replace(".", ",") if p_atual else "&mdash;"),
        origem_p=html.escape(origem_p, quote=True),
    )


class Manipulador(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _responder(self, codigo, corpo, tipo="application/json; charset=utf-8",
                   cabecalhos=None):
        dados = corpo.encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(dados)))
        for chave, valor in (cabecalhos or {}).items():
            self.send_header(chave, valor)
        self.end_headers()
        self.wfile.write(dados)

    def do_GET(self):
        rota = urlparse(self.path)
        parametros = parse_qs(rota.query)

        if rota.path == "/":
            self._responder(200, montar_pagina(), "text/html; charset=utf-8")

        elif rota.path == "/api/saude":
            self._responder(200, json.dumps({"estado": "vivo"}))

        elif rota.path == "/api/estado":
            with TRAVA_ESTADO:
                self._responder(200, json.dumps(ESTADO, ensure_ascii=False,
                                                default=str))

        elif rota.path == "/api/executar":
            with TRAVA_ESTADO:
                if ESTADO["ocupado"]:
                    self._responder(409, json.dumps(
                        {"erro": "ja existe uma execucao em andamento"}))
                    return
                ESTADO["ocupado"] = True
            threading.Thread(target=executar_em_segundo_plano,
                             args=(parametros,), daemon=True).start()
            self._responder(303, "{}", cabecalhos={"Location": "/"})

        else:
            self._responder(404, json.dumps({"erro": "rota inexistente"}))

    def log_message(self, formato, *args):
        sys.stderr.write(f"[{self.log_date_time_string()}] "
                         f"{self.address_string()} {formato % args}\n")


def main():
    p = argparse.ArgumentParser(description="Servico HTTP da aplicacao.")
    p.add_argument("--corpus", default="dados/corpus")
    p.add_argument("--porta", type=int, default=8000)
    p.add_argument("--endereco", default="0.0.0.0")
    p.add_argument("--medicao", default="resultados/medicao.json",
                   help="de onde ler a fracao paralelizavel instrumentada")
    a = p.parse_args()

    ESTADO["corpus"] = a.corpus
    ESTADO["documentos"] = len(listar_corpus(a.corpus))
    ESTADO["maquina"] = descrever_maquina()
    if carregar_p_da_medicao(a.medicao):
        print(f"p paralelizavel = {ESTADO['p_paralelizavel']} "
              f"({ESTADO['origem_p']})")
    else:
        print(f"{a.medicao} ausente: o teto de Amdahl so aparece depois que o "
              f"painel rodar a versao sequencial ao menos uma vez.")

    servidor = ThreadingHTTPServer((a.endereco, a.porta), Manipulador)
    print(f"servico em http://{a.endereco}:{a.porta}  "
          f"({ESTADO['documentos']} documentos em {a.corpus})")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nencerrando")
        servidor.shutdown()


if __name__ == "__main__":
    main()
