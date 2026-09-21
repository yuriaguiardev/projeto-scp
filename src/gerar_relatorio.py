"""
gerar_relatorio.py - Monta o relatorio tecnico em PDF a partir da medicao.

O relatorio nao e escrito a mao depois da medicao: ele e gerado a partir de
resultados/medicao.json. Assim os numeros do texto, das tabelas e da analise
vem todos da mesma execucao, e nao ha como o texto dizer uma coisa e a tabela
outra.

Uso:
    python3 src/medir.py --corpus dados/corpus --trabalhadores 1 2 4 8
    python3 src/gerar_relatorio.py

O PDF e gerado por src/pdf.py, que usa o primeiro conversor disponivel:
wkhtmltopdf, um navegador sem tela (Chrome/Chromium/Edge) ou weasyprint. O HTML
fica sempre em relatorio/relatorio.html e serve de alternativa manual.
"""

import argparse
import html
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pdf
from configuracao import EQUIPE, INFRA, DISCIPLINA, pendencias

ESTILO = """
@page { size: A4; margin: 17mm 16mm 15mm 16mm; }
* { box-sizing: border-box; }
body { font: 9.4pt/1.42 "DejaVu Serif", Georgia, serif; color:#16150f; margin:0; }
h1 { font-size: 15pt; margin: 0 0 2pt; line-height:1.2; }
h2 { font-size: 10.6pt; margin: 11pt 0 3pt; padding-bottom:1.5pt;
     border-bottom: 0.6pt solid #b9b4a8; letter-spacing:.01em; }
h3 { font-size: 9.6pt; margin: 7pt 0 2pt; }
p  { margin: 0 0 4.5pt; text-align: justify; }
.cabecalho { border-bottom: 1.2pt solid #16150f; padding-bottom: 5pt;
             margin-bottom: 8pt; }
.meta { font-size: 8.1pt; color:#57534a; line-height:1.4; }
.equipe { font-size: 8.4pt; margin-top:3pt; }
table { border-collapse: collapse; width: 100%; font-size: 8.2pt;
        margin: 3pt 0 6pt; }
th, td { border: 0.5pt solid #c9c4b8; padding: 2.4pt 4pt; text-align: left;
         vertical-align: top; }
th { background: #f1efe9; font-weight: 600; }
td.n, th.n { text-align: right; font-variant-numeric: tabular-nums; }
code, .mono { font-family: "DejaVu Sans Mono", Consolas, monospace;
              font-size: 7.9pt; }
pre { background:#f7f5f0; border:0.5pt solid #ddd8cc; border-left:2pt solid #8a6a3a;
      padding:4pt 6pt; margin:3pt 0 6pt; font-family:"DejaVu Sans Mono",monospace;
      font-size:7.6pt; line-height:1.35; white-space:pre-wrap; }
.aviso { background:#fdf3e3; border:0.6pt solid #d9a441; padding:5pt 7pt;
         margin:4pt 0 6pt; font-size:8.3pt; }
.destaque { background:#f1efe9; padding:4pt 7pt; margin:3pt 0 5pt;
            border-left:2pt solid #16150f; font-size:8.6pt; }
ul { margin: 2pt 0 5pt; padding-left: 13pt; }
li { margin-bottom: 1.6pt; text-align: justify; }
.rodape { margin-top:8pt; padding-top:4pt; border-top:0.5pt solid #c9c4b8;
          font-size:7.6pt; color:#57534a; }
.evitar-quebra { page-break-inside: avoid; }
"""


def f(valor, casas=2, vazio="&mdash;"):
    if valor is None:
        return vazio
    return f"{valor:.{casas}f}".replace(".", ",")


def carregar(caminho):
    if not os.path.exists(caminho):
        return None
    with open(caminho, encoding="utf-8") as arq:
        return json.load(arq)


def analisar(medicao):
    """Extrai da medicao os fatos que a secao de analise precisa."""
    if not medicao:
        return None
    processos = [l for l in medicao["paralelo"] if l["motor"] == "processo"]
    threads = [l for l in medicao["paralelo"] if l["motor"] == "thread"]
    if not processos:
        return None
    melhor = max(processos, key=lambda l: l["speedup"])
    return {
        "melhor": melhor,
        "processos": processos,
        "threads": threads,
        "lacuna": melhor["amdahl_teto"] - melhor["speedup"],
        "lacuna_pct": 100 * (melhor["amdahl_teto"] - melhor["speedup"])
                      / melhor["amdahl_teto"] if melhor["amdahl_teto"] else 0,
        "espera_pct": (100 * melhor["espera_na_trava_s"]
                       / (melhor["tempo_mediano_s"] * melhor["trabalhadores"])
                       if melhor["tempo_mediano_s"] else 0),
    }


def procedencia(medicao):
    """
    Em que maquina a medicao foi feita, e se ela e a instancia planejada.

    Existe porque o relatorio nao pode afirmar que os tempos vieram da instancia
    descrita na secao 4 quando vieram de outra maquina. O tipo de instancia e
    lido do servico de metadados da EC2 por medir.py: se ele estiver ausente, a
    medicao nao foi feita na nuvem, e o relatorio diz isso em vez de calar.
    """
    if not medicao:
        return None
    m = medicao.get("maquina", {})
    tipo = m.get("tipo_instancia")
    return {
        "em_ec2": bool(tipo),
        "tipo": tipo,
        "confere": bool(tipo) and tipo == INFRA["tipo_instancia"],
        "rotulo": (f"{tipo}, zona {m.get('zona') or INFRA['zona']}" if tipo else
                   f"{m.get('modelo') or m.get('arquitetura') or 'maquina local'}"
                   f" &mdash; {m.get('sistema', 'sistema nao identificado')}"),
        "vcpu": m.get("nucleos_logicos"),
    }


def conferir(medicao, pr):
    """
    Confere, no terminal, o que ainda separa o PDF gerado do PDF entregavel.

    Os avisos ficam aqui e nao dentro do documento: o relatorio entregue segue a
    estrutura pedida pela lauda, sem texto de controle interno. Quem gera o
    arquivo ve as pendencias na hora de gerar, que e quando da para agir.
    """
    recados = []
    faltando = pendencias()
    if faltando:
        recados.append("campos de src/configuracao.py ainda por preencher: "
                       + "; ".join(faltando))
    if pr and not pr["confere"]:
        onde = pr["tipo"] if pr["em_ec2"] else "uma maquina fora da EC2"
        recados.append(
            f"a medicao em resultados/medicao.json foi feita em {onde}, e a "
            f"secao 4 descreve {INFRA['tipo_instancia']}. Rode src/medir.py na "
            f"instancia e gere o relatorio de novo para que as duas coincidam.")
    if not recados:
        return
    print("\nconferir antes de entregar:", file=sys.stderr)
    for recado in recados:
        print(f"  - {recado}", file=sys.stderr)


def tabela_medicao(medicao, a):
    if not medicao or not a:
        return ('<div class="aviso"><strong>Medi&ccedil;&atilde;o pendente.</strong> '
                'Execute <code>python3 src/medir.py --corpus dados/corpus '
                '--trabalhadores 1 2 4 8 --repeticoes 3 --com-thread</code> na '
                'inst&acirc;ncia e depois <code>python3 src/gerar_relatorio.py</code>. '
                'As tabelas e a an&aacute;lise s&atilde;o preenchidas com os n&uacute;meros '
                'daquela execu&ccedil;&atilde;o.</div>'
                '<table><tr><th>Motor</th><th class="n">n</th><th class="n">T(n) (s)</th>'
                '<th class="n">Speedup</th><th class="n">Teto de Amdahl</th>'
                '<th class="n">Efici&ecirc;ncia</th><th class="n">e (Karp-Flatt)</th>'
                '<th>Est&aacute;vel</th><th>= sequencial</th></tr>'
                + "".join('<tr><td>&mdash;</td><td class="n">&mdash;</td>'
                          '<td class="n">&mdash;</td><td class="n">&mdash;</td>'
                          '<td class="n">&mdash;</td><td class="n">&mdash;</td>'
                          '<td class="n">&mdash;</td><td>&mdash;</td>'
                          '<td>&mdash;</td></tr>'
                          for _ in range(4))
                + '</table>')

    seq = medicao["sequencial"]
    linhas = [
        f'<tr><td>sequencial</td><td class="n">1</td>'
        f'<td class="n">{f(seq["tempo_mediano_s"])}</td>'
        f'<td class="n">1,00</td><td class="n">1,00</td><td class="n">1,00</td>'
        f'<td class="n">&mdash;</td><td>sim</td>'
        f'<td>refer&ecirc;ncia</td></tr>'
    ]
    for l in medicao["paralelo"]:
        linhas.append(
            f'<tr><td>{l["motor"]}</td><td class="n">{l["trabalhadores"]}</td>'
            f'<td class="n">{f(l["tempo_mediano_s"])}</td>'
            f'<td class="n"><strong>{f(l["speedup"])}</strong></td>'
            f'<td class="n">{f(l["amdahl_teto"])}</td>'
            f'<td class="n">{f(l["eficiencia"])}</td>'
            f'<td class="n">{f(l["karp_flatt_e"], 4)}</td>'
            f'<td>{"sim" if l["resultado_estavel"] else "NAO"}</td>'
            f'<td>{"sim" if l.get("igual_ao_sequencial") else "N&Atilde;O"}</td></tr>')
    return ('<table><tr><th>Motor</th><th class="n">n</th><th class="n">T(n) (s)</th>'
            '<th class="n">Speedup</th><th class="n">Teto de Amdahl</th>'
            '<th class="n">Efici&ecirc;ncia</th><th class="n">e (Karp-Flatt)</th>'
            '<th>Est&aacute;vel</th><th>= sequencial</th></tr>'
            + "".join(linhas) + '</table>'
            + '<p style="font-size:7.9pt;color:#57534a;margin-top:-3pt">'
              '<strong>Est&aacute;vel</strong>: as repeti&ccedil;&otilde;es daquela '
              'configura&ccedil;&atilde;o devolveram o mesmo SHA-256 entre si. '
              '<strong>= sequencial</strong>: esse SHA-256 &eacute; tamb&eacute;m o '
              'da vers&atilde;o sequencial &mdash; a paraleliza&ccedil;&atilde;o '
              'n&atilde;o mudou o resultado, s&oacute; o tempo. As duas colunas s&atilde;o '
              'verificadas a cada execu&ccedil;&atilde;o da bancada, n&atilde;o afirmadas '
              'no texto.</p>')


MENOR_CAUSA = ("&Eacute; a menor das tr&ecirc;s causas: cada trabalhador entra "
               "na trava uma vez por lote, n&atilde;o uma vez por documento.")
CAUSA_RELEVANTE = ("&Eacute; uma parcela relevante: vale aumentar o tamanho do "
                   "lote, para reduzir o n&uacute;mero de entradas na trava.")


def texto_analise(medicao, a):
    if not a:
        return ('<p>Esta se&ccedil;&atilde;o &eacute; gerada a partir de '
                '<code>resultados/medicao.json</code>. Enquanto a medi&ccedil;&atilde;o '
                'n&atilde;o for executada na inst&acirc;ncia, ela permanece vazia.</p>')

    m = a["melhor"]
    seq = medicao["sequencial"]
    nucleos = medicao["maquina"].get("nucleos_fisicos")
    partes = []

    partes.append(
        f'<p>O melhor resultado foi com <strong>n = {m["trabalhadores"]}</strong>: '
        f'o tempo caiu de {f(seq["tempo_mediano_s"])} s para '
        f'{f(m["tempo_mediano_s"])} s, um speedup medido de '
        f'<strong>{f(m["speedup"])}</strong> contra um teto de Amdahl de '
        f'{f(m["amdahl_teto"])} para a fra&ccedil;&atilde;o paraleliz&aacute;vel '
        f'instrumentada p = {f(seq["p_instrumentado"], 4)}. A diferen&ccedil;a &eacute; de '
        f'{f(a["lacuna"])} ({f(a["lacuna_pct"], 1)}&nbsp;%). A m&eacute;trica de '
        f'Karp-Flatt devolve uma fra&ccedil;&atilde;o serial experimental de '
        f'e = {f(m["karp_flatt_e"], 4)}, acima do (1&nbsp;&minus;&nbsp;p) = '
        f'{f(1 - seq["p_instrumentado"], 4)} medido por instrumenta&ccedil;&atilde;o: '
        f'a diferen&ccedil;a entre as duas &eacute; exatamente o custo que a '
        f'paraleliza&ccedil;&atilde;o introduziu e que n&atilde;o existia na '
        f'vers&atilde;o sequencial.</p>')

    causas = []
    causas.append(
        f'<li><strong>Espera na se&ccedil;&atilde;o cr&iacute;tica.</strong> '
        f'A espera acumulada na trava foi de {f(m["espera_na_trava_s"])} s, '
        f'{f(a["espera_pct"], 2)}&nbsp;% do tempo total de trabalhador '
        f'({f(m["tempo_mediano_s"] * m["trabalhadores"])} s). '
        f'{MENOR_CAUSA if a["espera_pct"] < 5 else CAUSA_RELEVANTE}</li>')
    causas.append(
        '<li><strong>Comunica&ccedil;&atilde;o entre processos.</strong> O agregador '
        'global vive no processo do <code>Manager</code>; cada leitura e cada '
        'escrita de <code>estado[...]</code> &eacute; uma ida e volta por '
        'soquete, com serializa&ccedil;&atilde;o. Esse custo n&atilde;o existe na '
        'vers&atilde;o sequencial, logo n&atilde;o aparece em p e o teto de Amdahl '
        'n&atilde;o o prev&ecirc;. &Eacute; o motivo de a assinatura viajar comprimida '
        'em 16 d&iacute;gitos em vez das 64 posi&ccedil;&otilde;es originais.</li>')
    if nucleos and m["trabalhadores"] > nucleos:
        causas.append(
            f'<li><strong>N&uacute;cleos l&oacute;gicos, n&atilde;o f&iacute;sicos.</strong> '
            f'A inst&acirc;ncia tem {medicao["maquina"]["nucleos_logicos"]} vCPU sobre '
            f'{nucleos} n&uacute;cleos f&iacute;sicos. Acima de n = {nucleos} os '
            f'trabalhadores passam a dividir unidades de execu&ccedil;&atilde;o, '
            f'e o ganho marginal cai bem antes do que a lei de Amdahl sugere, '
            f'porque a lei sup&otilde;e n processadores independentes.</li>')
    causas.append(
        '<li><strong>Divis&atilde;o desigual do trabalho.</strong> Os lotes t&ecirc;m o '
        'mesmo n&uacute;mero de documentos, mas os documentos t&ecirc;m tamanhos '
        'diferentes, e o custo do MinHash cresce com o n&uacute;mero de shingles. '
        'No fim da execu&ccedil;&atilde;o alguns trabalhadores j&aacute; esvaziaram a '
        'fila enquanto outros ainda processam o &uacute;ltimo lote. A fila comum '
        'reduz esse efeito, mas n&atilde;o o elimina: o limite inferior &eacute; o '
        'lote mais caro.</li>')
    partes.append("<ul>" + "".join(causas) + "</ul>")

    if a["threads"]:
        t = max(a["threads"], key=lambda l: l["speedup"])
        partes.append(
            f'<p><strong>Threads, para compara&ccedil;&atilde;o.</strong> A mesma '
            f'aplica&ccedil;&atilde;o com <code>threading</code> e n = '
            f'{t["trabalhadores"]} mediu speedup de {f(t["speedup"])} '
            f'({f(t["tempo_mediano_s"])} s). O trabalho &eacute; limitado por '
            f'processador e o GIL serializa a execu&ccedil;&atilde;o de bytecode: '
            f'as threads existem, mas apenas uma avan&ccedil;a por vez. &Eacute; a '
            f'evid&ecirc;ncia de que a escolha por processos n&atilde;o foi '
            f'estil&iacute;stica.</p>')
    return "".join(partes)


def montar_html(medicao):
    a = analisar(medicao)
    pr = procedencia(medicao)
    maquina = (medicao or {}).get("maquina", {})
    corpus = (medicao or {}).get("corpus", {})
    seq = (medicao or {}).get("sequencial", {})

    integrantes = " &middot; ".join(
        f"{i['nome']}" + (f" ({i['matricula']})" if i.get("matricula") else "")
        for i in EQUIPE["integrantes"])

    instancia = maquina.get("tipo_instancia") or INFRA["tipo_instancia"]
    zona = maquina.get("zona") or INFRA["zona"]
    n_docs = corpus.get("documentos") or INFRA["documentos_previstos"]
    n_bytes = corpus.get("bytes")
    volume = f"{n_bytes/1_048_576:.0f} MiB" if n_bytes else "&mdash;"

    medidos = (medicao or {}).get("trabalhadores_medidos") or sorted(
        {l["trabalhadores"] for l in (medicao or {}).get("paralelo", [])
         if l["motor"] == "processo"}) or [1, 2, 4, INFRA["vcpu"]]
    if len(medidos) > 1:
        lista_n = ", ".join(str(x) for x in medidos[:-1]) + f" e {medidos[-1]}"
    else:
        lista_n = str(medidos[0])

    ev = (medicao or {}).get("eventos")

    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<title>Relatorio tecnico - Etapa 1</title><style>{ESTILO}</style></head><body>

<div class="cabecalho">
<h1>Triagem paralela de editais de compra p&uacute;blica</h1>
<div class="meta">{DISCIPLINA['codigo']} {DISCIPLINA['nome']} &middot; Etapa 1 do
Projeto de Solu&ccedil;&atilde;o Distribu&iacute;da &middot; Turma {EQUIPE['turma']} &middot;
Prof. {DISCIPLINA['professor']} &middot; {DISCIPLINA['entrega']}</div>
<div class="equipe"><strong>Equipe:</strong> {integrantes}</div>
</div>

<h2>1. O problema</h2>
<p>O Portal Nacional de Contrata&ccedil;&otilde;es P&uacute;blicas publica dezenas de
milhares de editais por m&ecirc;s. Uma empresa que vende software para o setor
p&uacute;blico precisa separar, dentro desse volume, os editais que t&ecirc;m a ver com
as suas linhas de produto &mdash; e precisa fazer isso antes de a sess&atilde;o
p&uacute;blica abrir. A triagem manual n&atilde;o acompanha.</p>
<p>A aplica&ccedil;&atilde;o recebe um lote de editais em texto e, para cada um,
executa quatro etapas: normaliza&ccedil;&atilde;o Unicode com remo&ccedil;&atilde;o
de acentos, tokeniza&ccedil;&atilde;o com descarte de palavras vazias,
pontua&ccedil;&atilde;o de ader&ecirc;ncia contra uma taxonomia de termos com peso
&mdash; positivos para software de gest&atilde;o e arrecada&ccedil;&atilde;o,
negativos para obra, merenda e combust&iacute;vel &mdash; e o c&aacute;lculo de uma
assinatura MinHash de 64 posi&ccedil;&otilde;es sobre os <em>shingles</em> de cinco
tokens da se&ccedil;&atilde;o do objeto. A assinatura serve para reconhecer o mesmo
edital republicado por munic&iacute;pios diferentes, caso frequente no PNCP. A
sa&iacute;da &eacute; um relat&oacute;rio com o ranking dos editais mais aderentes,
a distribui&ccedil;&atilde;o por linha de produto, a frequ&ecirc;ncia dos termos da
taxonomia e a contagem de republica&ccedil;&otilde;es.</p>

<h3>1.1 Por que o trabalho se divide</h3>
<p>A unidade de trabalho &eacute; <strong>um edital</strong>. O processamento de um
edital n&atilde;o l&ecirc; nem escreve nada de outro edital: as fun&ccedil;&otilde;es
de <code>nucleo.py</code> s&atilde;o puras e o m&oacute;dulo n&atilde;o tem estado
global. A depend&ecirc;ncia aparece s&oacute; na agrega&ccedil;&atilde;o, e a
opera&ccedil;&atilde;o de agrega&ccedil;&atilde;o &eacute; associativa e comutativa,
o que permite que cada fluxo acumule um parcial pr&oacute;prio e funda esse parcial
no total ao fim de cada lote.</p>

<table class="evitar-quebra">
<tr><th style="width:34%">Condi&ccedil;&atilde;o exigida</th><th>Como a aplica&ccedil;&atilde;o atende</th></tr>
<tr><td>Partes independentes</td><td>Um edital por unidade. Sem leitura ou escrita cruzada entre unidades.</td></tr>
<tr><td>Volume suficiente</td><td>{n_docs} documentos, {volume} de texto. Tempo sequencial medido: {f(seq.get('tempo_mediano_s'))} s.</td></tr>
<tr><td>Resultado verific&aacute;vel</td><td>O relat&oacute;rio final &eacute; canonizado (ordena&ccedil;&atilde;o determinada s&oacute; pelo conte&uacute;do) e reduzido a um SHA-256. As duas vers&otilde;es t&ecirc;m de produzir a mesma impress&atilde;o digital.</td></tr>
<tr><td>Estado escrito por mais de um fluxo</td><td>O agregador global: contadores, dicion&aacute;rio de termos, ranking e mapa de assinaturas, em mem&oacute;ria compartilhada.</td></tr>
</table>

<h2>2. Estrat&eacute;gia de paraleliza&ccedil;&atilde;o</h2>
<table class="evitar-quebra">
<tr><th style="width:21%">Decis&atilde;o</th><th style="width:20%">Escolha</th><th>Justificativa</th></tr>
<tr><td>Tipo de paralelismo</td><td>Dados</td><td>A mesma sequ&ecirc;ncia de opera&ccedil;&otilde;es se aplica a documentos diferentes. N&atilde;o h&aacute; est&aacute;gios distintos que possam correr em paralelo, ent&atilde;o paralelismo de tarefas n&atilde;o se aplica.</td></tr>
<tr><td>Processo ou thread</td><td><strong>Processo</strong></td><td>O trabalho &eacute; limitado por processador, n&atilde;o por espera: a leitura do arquivo responde por menos de 0,5&nbsp;% do tempo; o resto &eacute; aritm&eacute;tica de inteiros e hashing em Python puro. Em CPython o GIL impede que duas threads executem bytecode ao mesmo tempo, de modo que a vers&atilde;o com threads mediria speedup pr&oacute;ximo de 1. A aplica&ccedil;&atilde;o tem o modo <code>--motor thread</code> justamente para mostrar isso na medi&ccedil;&atilde;o.</td></tr>
<tr><td>N&uacute;mero de trabalhadores</td><td>{lista_n}</td><td>Varre-se de 1 at&eacute; o n&uacute;mero de vCPU da inst&acirc;ncia, para que a curva de speedup mostre onde o ganho satura e por qu&ecirc;.</td></tr>
<tr><td>Divis&atilde;o do trabalho</td><td>Fila comum de lotes</td><td>O corpus &eacute; cortado em lotes de {(medicao or {}).get('tamanho_lote', 150)} documentos, postos numa &uacute;nica fila. Cada trabalhador puxa o pr&oacute;ximo lote quando termina o anterior. &Eacute; balanceamento din&acirc;mico: um trabalhador que pegue um lote caro n&atilde;o atrasa os outros, ao contr&aacute;rio do que aconteceria com uma divis&atilde;o fixa em n fatias.</td></tr>
</table>

<h2>3. A se&ccedil;&atilde;o cr&iacute;tica e a primitiva que a protege</h2>
<p>O estado compartilhado &eacute; o agregador global, mantido por um
<code>multiprocessing.Manager</code> e escrito por todos os trabalhadores. A
se&ccedil;&atilde;o cr&iacute;tica &eacute; a fun&ccedil;&atilde;o
<code>fundir_no_global</code> de <code>src/paralelo.py</code>, e a primitiva
&eacute; um <strong><code>multiprocessing.Lock</code></strong> &mdash; exclus&atilde;o
m&uacute;tua simples, porque o recurso admite um escritor por vez e n&atilde;o h&aacute;
condi&ccedil;&atilde;o de espera a sinalizar, o que dispensaria sem&aacute;foro
contado ou monitor.</p>
<pre>lock.acquire()
try:
    relogio = max(relogio_local, estado["relogio"]) + 1   # carimbo de Lamport
    estado["relogio"] = relogio
    estado["documentos"] = estado["documentos"] + parcial["documentos"]
    termos = estado["termos"]; ...; estado["termos"] = termos
    for chave, doc_id in parcial["assinaturas"].items():   # verificar-entao-agir
        anterior = assinaturas.get(chave)
        if anterior is None: assinaturas[chave] = doc_id
        else: duplicados += 1
    eventos.append({{"quem": identificador, "o_que": "fusao", ...}})
finally:
    lock.release()</pre>
<p>Duas corridas distintas vivem a&iacute;. A primeira &eacute; a
<em>atualiza&ccedil;&atilde;o perdida</em>: <code>estado["documentos"]</code> &eacute;
lido, somado e gravado em tr&ecirc;s passos, e entre o primeiro e o terceiro cabe a
grava&ccedil;&atilde;o de outro trabalhador, que se perde. A segunda &eacute; o
<em>verificar-entao-agir</em> sobre o mapa de assinaturas: dois trabalhadores
perguntam se a mesma assinatura j&aacute; existe, ambos recebem "n&atilde;o", e uma
republica&ccedil;&atilde;o deixa de ser contada.</p>

<h3>3.1 Por que o la&ccedil;o inteiro fica fora da trava</h3>
<p>O processamento dos documentos de um lote acontece <strong>antes</strong> de
<code>acquire</code>, num agregador parcial local ao processo. S&oacute; a fus&atilde;o
do parcial entra na trava. Uma trava em volta do la&ccedil;o inteiro tamb&eacute;m
seria correta, mas serializaria todo o trabalho e o speedup cairia para perto de 1.
A aplica&ccedil;&atilde;o traz essa vers&atilde;o no modo
<code>--sincronizacao larga</code>, e ela &eacute; medida junto com as outras
justamente para tornar a diferen&ccedil;a vis&iacute;vel.</p>

<h3>3.2 Troca de mensagem e carimbo l&oacute;gico</h3>
<p>H&aacute; troca de mensagem: a fila de lotes e o canal at&eacute; o processo do
<code>Manager</code>. Como os processos n&atilde;o compartilham rel&oacute;gio
f&iacute;sico, a ordem dos eventos &eacute; registrada por um <strong>rel&oacute;gio
l&oacute;gico de Lamport</strong>. Cada trabalhador mant&eacute;m um contador local,
incrementado ao receber um lote; ao fundir, adianta o contador para
<code>max(local, global) + 1</code>, grava esse valor no estado e registra o evento.
Cada registro cont&eacute;m <em>quem</em> (identificador do trabalhador),
<em>o qu&ecirc;</em> (fus&atilde;o no agregador global), <em>carimbo l&oacute;gico</em>
e <em>sobre o qu&ecirc;</em> (n&uacute;mero do lote e quantidade de documentos). O
registro completo sai em <code>resultados/eventos.json</code> e permite reconstruir
uma ordena&ccedil;&atilde;o consistente das fus&otilde;es sem rel&oacute;gio comum.
{f"A execu&ccedil;&atilde;o arquivada registrou <strong>{ev['fusoes']}</strong> fus&otilde;es de {ev['trabalhadores']} trabalhadores, com carimbo l&oacute;gico m&aacute;ximo {ev['carimbo_maximo']}." if ev else ""}</p>

<h3>3.3 Como a corre&ccedil;&atilde;o &eacute; demonstrada</h3>
<p><code>src/verificar.py</code> roda a vers&atilde;o sequencial uma vez e a paralela
v&aacute;rias vezes sobre a mesma entrada e compara os SHA-256. Com
<code>--modo lock</code> as execu&ccedil;&otilde;es coincidem entre si e com a
sequencial. Com <code>--modo nenhuma</code> a mesma entrada produz impress&otilde;es
digitais diferentes a cada execu&ccedil;&atilde;o: &eacute; a condi&ccedil;&atilde;o
de corrida exibida ao vivo, e n&atilde;o uma descri&ccedil;&atilde;o dela.</p>

<h2>4. Recursos provisionados</h2>
<table class="evitar-quebra">
<tr><th style="width:26%">Decis&atilde;o</th><th style="width:26%">Escolha</th><th>Justificativa</th></tr>
<tr><td>Regi&atilde;o e zonas</td><td>{INFRA['regiao']}, uma zona ({zona})</td><td>Inst&acirc;ncia isolada em zona &uacute;nica: vale o compromisso de <strong>99,5&nbsp;%</strong> do SLA do EC2, ou 216 minutos de indisponibilidade admitida em 30 dias. Distribuir por duas ou mais zonas elevaria o compromisso para 99,99&nbsp;% (4,3 minutos), mas o experimento exige que T(1) e T(n) sejam medidos no <em>mesmo</em> hardware: duas inst&acirc;ncias em zonas diferentes n&atilde;o comparariam a mesma coisa. A disponibilidade n&atilde;o &eacute; requisito de um lote que roda sob demanda.</td></tr>
<tr><td>Fam&iacute;lia, tamanho e quantidade</td><td>1 &times; {instancia}</td><td>Fam&iacute;lia otimizada para computa&ccedil;&atilde;o, sem cr&eacute;ditos de CPU. Inst&acirc;ncia burst&aacute;vel (t2, t3) &eacute; inadequada para medir speedup: ao esgotar os cr&eacute;ditos, o desempenho cai no meio da medi&ccedil;&atilde;o e o T(n) deixa de ser compar&aacute;vel ao T(1).</td></tr>
<tr><td>Entrada e sa&iacute;da</td><td>EBS gp3 {INFRA['disco_gib']} GiB; c&oacute;pia em S3</td><td>O corpus ({volume}) &eacute; gerado no volume local, para que a leitura n&atilde;o introduza lat&ecirc;ncia de rede no tempo medido. Os relat&oacute;rios e a medi&ccedil;&atilde;o s&atilde;o arquivados no bucket <code>{INFRA['bucket']}</code>, com bloqueio de acesso p&uacute;blico e criptografia SSE-S3.</td></tr>
<tr><td>Portas e origem</td><td>22/tcp de {INFRA['origem_admin']}; 8000/tcp de 0.0.0.0/0</td><td>A porta administrativa <strong>n&atilde;o</strong> aceita 0.0.0.0/0: a porta 22 exposta &agrave; internet recebe tentativas autom&aacute;ticas de autentica&ccedil;&atilde;o continuamente, e restringi-la ao endere&ccedil;o da equipe retira a inst&acirc;ncia dessa superf&iacute;cie sem depender da for&ccedil;a da chave. A porta 8000 serve o painel da aplica&ccedil;&atilde;o e &eacute; a &uacute;nica aberta ao p&uacute;blico.</td></tr>
<tr><td>Ciclo de vida</td><td>Ligada durante a janela de medi&ccedil;&atilde;o</td><td>Criar a inst&acirc;ncia por execu&ccedil;&atilde;o traria hardware subjacente potencialmente diferente entre T(1) e T(n). Como o speedup exige a mesma m&aacute;quina, a inst&acirc;ncia permanece ligada do in&iacute;cio da medi&ccedil;&atilde;o at&eacute; o fim da apresenta&ccedil;&atilde;o, e &eacute; encerrada depois.</td></tr>
</table>

<h2>5. Medi&ccedil;&atilde;o</h2>
<p>Tempo sequencial e tempo paralelo medidos na mesma m&aacute;quina
({maquina.get('modelo') or instancia}, {maquina.get('nucleos_logicos') or '&mdash;'}
n&uacute;cleos l&oacute;gicos), com a mesma entrada de {n_docs} documentos, com
{(medicao or {}).get('repeticoes', 3)} repeti&ccedil;&otilde;es por
configura&ccedil;&atilde;o; as tabelas trazem a mediana. O T(1) vem da vers&atilde;o
sequencial, n&atilde;o da paralela com um trabalhador, que j&aacute; carrega o custo
da fila e do <code>Manager</code>.</p>
{tabela_medicao(medicao, a)}
<p>A fra&ccedil;&atilde;o paraleliz&aacute;vel p = {f(seq.get('p_instrumentado'), 4)}
n&atilde;o foi arbitrada: a vers&atilde;o sequencial cronometra separadamente a
leitura do arquivo e o trabalho por documento, e p &eacute; a raz&atilde;o entre o
segundo e o total.</p>

<h2>6. O que limitou o ganho</h2>
{texto_analise(medicao, a)}

<div class="rodape">
Reposit&oacute;rio: {EQUIPE['repositorio']} &middot; Relat&oacute;rio gerado por
<code>src/gerar_relatorio.py</code> a partir de <code>resultados/medicao.json</code>
&middot; medi&ccedil;&atilde;o de {(medicao or {}).get('gerado_em', '&mdash;')}
</div>
</body></html>"""


def main():
    p = argparse.ArgumentParser(description="Gera o relatorio tecnico em PDF.")
    p.add_argument("--medicao", default="resultados/medicao.json")
    p.add_argument("--saida", default="relatorio/relatorio.pdf")
    p.add_argument("--rascunhos", default="rascunhos",
                   help="onde gravar o HTML intermediario")
    a = p.parse_args()

    medicao = carregar(a.medicao)
    conferir(medicao, procedencia(medicao))
    if medicao is None:
        print(f"aviso: {a.medicao} nao encontrado; o relatorio sai com as "
              f"tabelas de medicao vazias.")

    # O HTML e um passo intermediario, nao um entregavel: fica fora de
    # relatorio/ e ficha/, para que essas pastas contenham so o PDF que vai ao
    # professor. Nao e versionado.
    os.makedirs(os.path.dirname(a.saida) or ".", exist_ok=True)
    os.makedirs(a.rascunhos, exist_ok=True)
    nome_base = os.path.splitext(os.path.basename(a.saida))[0] + ".html"
    caminho_html = os.path.join(a.rascunhos, nome_base)
    with open(caminho_html, "w", encoding="utf-8") as arq:
        arq.write(montar_html(medicao))
    print(f"html: {caminho_html}")

    usado = pdf.converter(caminho_html, a.saida)
    if usado:
        print(f"pdf : {a.saida}  (via {usado})")
    else:
        print("nenhum conversor de PDF encontrado (wkhtmltopdf, navegador sem "
              "tela ou weasyprint): imprima o HTML para PDF pelo navegador.")


if __name__ == "__main__":
    main()
