"""
gerar_ficha.py - Monta a Ficha da Etapa 1 preenchida, em PDF.

A ficha segue a estrutura do documento entregue pelo professor: secoes A a E,
com as mesmas perguntas, preenchidas com as decisoes da equipe.

Uso:
    python3 src/gerar_ficha.py
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pdf
from configuracao import DISCIPLINA, EQUIPE, INFRA, pendencias

# Fracao paralelizavel. Enquanto a bancada nao roda, e a estimativa da equipe;
# assim que resultados/medicao.json existe, o valor instrumentado toma o lugar
# dela e a ficha passa a dizer "medido" em vez de "estimado".
P_ESTIMADO = 0.995


def carregar_p(caminho):
    """Devolve (p, rotulo). Prefere o p instrumentado da medicao."""
    try:
        with open(caminho, encoding="utf-8") as arq:
            valor = json.load(arq)["sequencial"]["p_instrumentado"]
        if isinstance(valor, (int, float)):
            return float(valor), "medido por instrumenta&ccedil;&atilde;o"
    except Exception:
        pass
    return P_ESTIMADO, "estimado pela equipe"


def conferir():
    """
    Confere, no terminal, o que ainda falta preencher.

    Fica aqui e nao dentro da ficha: a ficha entregue segue a estrutura das
    secoes A a E pedidas pelo professor, sem texto de controle interno.
    """
    faltando = pendencias()
    if not faltando:
        return
    print("\nconferir antes de entregar:", file=sys.stderr)
    for item in faltando:
        print(f"  - {item}", file=sys.stderr)
    print(f"  - confirmar se a conta AWS permite {INFRA['tipo_instancia']}; se "
          f"nao permitir, ajustar tipo_instancia, vcpu e nucleos_fisicos",
          file=sys.stderr)


ESTILO = """
@page { size: A4; margin: 15mm 14mm; }
body { font: 9.3pt/1.4 "DejaVu Serif", Georgia, serif; color:#16150f; margin:0; }
h1 { font-size: 14pt; margin: 0 0 2pt; }
h2 { font-size: 10.4pt; margin: 10pt 0 3pt; padding-bottom:1.5pt;
     border-bottom: 0.6pt solid #b9b4a8; }
p { margin: 0 0 4pt; text-align: justify; }
.cabecalho { border-bottom: 1.2pt solid #16150f; padding-bottom: 5pt;
             margin-bottom: 8pt; }
.meta { font-size: 8.1pt; color:#57534a; }
table { border-collapse: collapse; width:100%; font-size:8.3pt; margin:3pt 0 6pt; }
th, td { border:0.5pt solid #c9c4b8; padding:2.6pt 4pt; text-align:left;
         vertical-align: top; }
th { background:#f1efe9; font-weight:600; }
code { font-family:"DejaVu Sans Mono",monospace; font-size:7.9pt; }
.evitar-quebra { page-break-inside: avoid; }
"""


def linhas_integrantes():
    saida = []
    for i, pessoa in enumerate(EQUIPE["integrantes"], start=1):
        matricula = pessoa.get("matricula") or "PREENCHER"
        saida.append(f'<tr><td style="width:6%">{i}</td>'
                     f'<td style="width:54%">{pessoa["nome"]}</td>'
                     f'<td>{matricula}</td></tr>')
    return "".join(saida)


def amdahl(p, n):
    return 1.0 / ((1 - p) + p / n)


def virgula(x, casas=2):
    return f"{x:.{casas}f}".replace(".", ",")


def montar_html(caminho_medicao="resultados/medicao.json"):
    n = INFRA["vcpu"]
    p_valor, p_rotulo = carregar_p(caminho_medicao)
    teto_n = virgula(amdahl(p_valor, n))
    teto_4 = virgula(amdahl(p_valor, 4))
    teto_2 = virgula(amdahl(p_valor, 2))

    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<title>Ficha da Etapa 1</title><style>{ESTILO}</style></head><body>

<div class="cabecalho">
<h1>Ficha da Etapa 1 &mdash; Projeto de Solu&ccedil;&atilde;o Distribu&iacute;da</h1>
<div class="meta"><strong>Disciplina:</strong> {DISCIPLINA['codigo']}
{DISCIPLINA['nome']} &middot; <strong>Oficina:</strong> {DISCIPLINA['oficina']}
&middot; <strong>Turma:</strong> {EQUIPE['turma']} &middot;
<strong>Professor:</strong> {DISCIPLINA['professor']} &middot;
<strong>Etapa 1 completa:</strong> {DISCIPLINA['entrega']}</div>
</div>

<h2>A. Equipe e problema</h2>
<table class="evitar-quebra"><tr><th>#</th><th>Nome</th><th>Matr&iacute;cula</th></tr>
{linhas_integrantes()}</table>

<p><strong>Problema escolhido:</strong> triagem autom&aacute;tica de editais de
compra p&uacute;blica. A aplica&ccedil;&atilde;o l&ecirc; um lote de editais em
texto, pontua cada um contra uma taxonomia de termos ligados a software de
gest&atilde;o e arrecada&ccedil;&atilde;o p&uacute;blica, classifica por linha de
produto e calcula uma assinatura MinHash do objeto para identificar o mesmo
edital republicado por munic&iacute;pios diferentes. A sa&iacute;da &eacute; um
relat&oacute;rio com ranking, distribui&ccedil;&atilde;o por linha,
frequ&ecirc;ncia de termos e contagem de republica&ccedil;&otilde;es.</p>

<table class="evitar-quebra">
<tr><th style="width:32%">Condi&ccedil;&atilde;o</th><th>Resposta da equipe</th></tr>
<tr><td>O trabalho se divide em partes independentes? Em que unidade?</td>
<td>Sim. A unidade &eacute; <strong>um edital</strong>. O processamento de um
edital n&atilde;o l&ecirc; nem escreve nada de outro: as fun&ccedil;&otilde;es de
<code>src/nucleo.py</code> s&atilde;o puras e o m&oacute;dulo n&atilde;o tem
estado global. A depend&ecirc;ncia s&oacute; aparece na agrega&ccedil;&atilde;o
dos resultados, e a agrega&ccedil;&atilde;o &eacute; associativa e comutativa.</td></tr>
<tr><td>Qual &eacute; o volume da entrada, e quanto tempo a vers&atilde;o
sequencial deve levar?</td>
<td>{INFRA['documentos_previstos']} editais de cerca de 10 KiB cada, aproximadamente
150 MiB de texto. O volume n&atilde;o foi arbitrado: <code>src/calibrar.py</code>
mede o custo por documento na pr&oacute;pria inst&acirc;ncia e calcula quantos
documentos s&atilde;o precisos para o alvo de <strong>4 minutos</strong> de
execu&ccedil;&atilde;o sequencial.</td></tr>
<tr><td>Como se verifica que o resultado est&aacute; correto?</td>
<td>O relat&oacute;rio final &eacute; canonizado &mdash; a ordena&ccedil;&atilde;o
depende s&oacute; do conte&uacute;do, nunca da ordem de chegada &mdash; e reduzido
a um <strong>SHA-256</strong>. <code>src/verificar.py</code> roda a vers&atilde;o
sequencial uma vez e a paralela v&aacute;rias vezes sobre a mesma entrada e
compara as impress&otilde;es digitais. S&atilde;o duas verifica&ccedil;&otilde;es
distintas: <em>equival&ecirc;ncia</em> (paralela = sequencial) e
<em>estabilidade</em> (todas as execu&ccedil;&otilde;es paralelas iguais entre si).</td></tr>
<tr><td>Que estado &eacute; escrito por mais de um fluxo?</td>
<td>O agregador global, em mem&oacute;ria compartilhada por um
<code>multiprocessing.Manager</code>: contador de documentos e de tokens, soma de
pontua&ccedil;&atilde;o, dicion&aacute;rio de frequ&ecirc;ncia dos termos da
taxonomia, contagem por linha de produto, ranking dos 25 melhores, mapa de
assinaturas e rel&oacute;gio l&oacute;gico.</td></tr>
</table>

<h2>B. Estrat&eacute;gia de paraleliza&ccedil;&atilde;o</h2>
<table class="evitar-quebra">
<tr><th style="width:21%">Decis&atilde;o</th><th style="width:17%">Escolha</th><th>Justificativa</th></tr>
<tr><td>Paralelismo de dados ou de tarefas</td><td><strong>Dados</strong></td>
<td>A mesma sequ&ecirc;ncia de opera&ccedil;&otilde;es se aplica a documentos
diferentes. N&atilde;o existem est&aacute;gios heterog&ecirc;neos que pudessem
correr simultaneamente, ent&atilde;o paralelismo de tarefas n&atilde;o se aplica.</td></tr>
<tr><td>Processo ou thread</td><td><strong>Processo</strong></td>
<td>O trabalho &eacute; <strong>limitado por processador</strong>, n&atilde;o por
espera: a leitura do arquivo responde por menos de 0,5&nbsp;% do tempo total e o
restante &eacute; normaliza&ccedil;&atilde;o Unicode, express&atilde;o regular,
hashing e aritm&eacute;tica de inteiros em Python puro. Em CPython o GIL impede
que duas threads executem bytecode ao mesmo tempo, de modo que a vers&atilde;o com
threads mediria speedup pr&oacute;ximo de 1 e a an&aacute;lise concluiria o oposto
do correto. A aplica&ccedil;&atilde;o tem o modo <code>--motor thread</code> para
que essa afirma&ccedil;&atilde;o seja medida, e n&atilde;o apenas citada.</td></tr>
<tr><td>Quantos trabalhadores em paralelo</td><td>1, 2, 4 e {n}</td>
<td>A inst&acirc;ncia {INFRA['tipo_instancia']} tem {n} vCPU sobre
{INFRA['nucleos_fisicos']} n&uacute;cleos f&iacute;sicos. Mede-se a curva inteira
para localizar onde o ganho satura: espera-se escala pr&oacute;xima da linear
at&eacute; n = {INFRA['nucleos_fisicos']} e ganho marginal pequeno de
{INFRA['nucleos_fisicos']} para {n}, quando os trabalhadores passam a dividir
n&uacute;cleos f&iacute;sicos.</td></tr>
<tr><td>Como o trabalho &eacute; dividido entre eles</td>
<td>Fila comum de lotes</td>
<td>O corpus &eacute; cortado em lotes de 150 documentos, todos postos numa
&uacute;nica <code>multiprocessing.Queue</code>. Cada trabalhador puxa o
pr&oacute;ximo lote quando termina o anterior: balanceamento din&acirc;mico.
Divis&atilde;o fixa em n fatias deixaria o tempo total refem da fatia mais cara.</td></tr>
</table>

<h2>C. Sincroniza&ccedil;&atilde;o</h2>
<table class="evitar-quebra">
<tr><th style="width:32%">Item</th><th>Resposta da equipe</th></tr>
<tr><td>Que estrutura &eacute; compartilhada e escrita por mais de um fluxo</td>
<td>O agregador global (<code>estado</code>, <code>assinaturas</code> e
<code>eventos</code>, todos proxies de <code>Manager</code>), escrito por todos os
trabalhadores ao fim de cada lote.</td></tr>
<tr><td>Qual &eacute; o menor trecho que precisa ser indivis&iacute;vel (a
se&ccedil;&atilde;o cr&iacute;tica)</td>
<td>A fun&ccedil;&atilde;o <code>fundir_no_global</code>, em
<code>src/paralelo.py</code>: a fus&atilde;o de <strong>um agregado parcial</strong>
no agregado global. O processamento dos 150 documentos do lote acontece fora da
trava, num parcial local ao processo. Dentro da trava ocorrem duas
opera&ccedil;&otilde;es que n&atilde;o toleram entrelaçamento: a
leitura-modifica&ccedil;&atilde;o-escrita dos contadores
(<code>estado["documentos"] = estado["documentos"] + k</code>) e o
verificar-entao-agir sobre o mapa de assinaturas.</td></tr>
<tr><td>Que primitiva vai proteg&ecirc;-la: lock, sem&aacute;foro ou monitor</td>
<td><strong><code>multiprocessing.Lock</code></strong>. O recurso admite um escritor
por vez e n&atilde;o h&aacute; condi&ccedil;&atilde;o de espera a sinalizar nem
contagem de permiss&otilde;es a administrar, o que dispensa sem&aacute;foro contado
e monitor. A trava &eacute; liberada em <code>finally</code>, para que uma
exce&ccedil;&atilde;o dentro da se&ccedil;&atilde;o cr&iacute;tica n&atilde;o trave
os demais processos.</td></tr>
<tr><td>Como a equipe vai demonstrar que o resultado ficou est&aacute;vel</td>
<td>Ao vivo, com <code>src/verificar.py</code>: a mesma entrada, oito
execu&ccedil;&otilde;es paralelas, oito SHA-256 id&ecirc;nticos e iguais ao da
vers&atilde;o sequencial. Em seguida a mesma verifica&ccedil;&atilde;o com
<code>--modo nenhuma</code>, que remove a trava: a&iacute; aparecem
impress&otilde;es digitais diferentes a cada execu&ccedil;&atilde;o e contagens de
documentos menores que o total, porque atualiza&ccedil;&otilde;es se perdem. A
corrida &eacute; exibida, n&atilde;o descrita.</td></tr>
</table>

<p><strong>Registro de evento e carimbo l&oacute;gico.</strong> H&aacute; troca de
mensagem: a fila de lotes e o canal at&eacute; o processo do <code>Manager</code>.
Como os processos n&atilde;o compartilham rel&oacute;gio f&iacute;sico, a ordem
das fus&otilde;es &eacute; registrada por um <strong>rel&oacute;gio l&oacute;gico
de Lamport</strong>: cada trabalhador mant&eacute;m um contador local,
incrementa-o ao receber um lote e, ao fundir, adianta-o para
<code>max(local, global) + 1</code>, grava esse valor no estado compartilhado e
registra o evento. Cada registro cont&eacute;m:</p>
<table class="evitar-quebra">
<tr><th style="width:18%">Campo</th><th>Conte&uacute;do</th></tr>
<tr><td>quem</td><td>identificador do trabalhador (<code>w0</code> a <code>w{n-1}</code>)</td></tr>
<tr><td>o qu&ecirc;</td><td><code>fusao_no_agregador_global</code></td></tr>
<tr><td>carimbo l&oacute;gico</td><td>valor do rel&oacute;gio de Lamport ap&oacute;s o avan&ccedil;o</td></tr>
<tr><td>sobre o qu&ecirc;</td><td>n&uacute;mero do lote e quantidade de documentos fundidos</td></tr>
</table>
<p>O registro completo &eacute; gravado em <code>resultados/eventos.json</code>,
ordenado por carimbo, e permite reconstruir uma ordena&ccedil;&atilde;o consistente
das fus&otilde;es sem rel&oacute;gio comum.</p>

<h2>D. Medi&ccedil;&atilde;o de desempenho</h2>
<table class="evitar-quebra">
<tr><th style="width:32%">Item</th><th>Resposta da equipe</th></tr>
<tr><td>M&aacute;quina em que as duas vers&otilde;es ser&atilde;o medidas</td>
<td>Inst&acirc;ncia &uacute;nica {INFRA['tipo_instancia']} ({INFRA['provedor']}),
regi&atilde;o {INFRA['regiao']}, zona {INFRA['zona']}. As duas vers&otilde;es
rodam na mesma inst&acirc;ncia, na mesma sess&atilde;o, sem outra carga.</td></tr>
<tr><td>N&uacute;mero de n&uacute;cleos dispon&iacute;veis nela</td>
<td>{n} vCPU sobre {INFRA['nucleos_fisicos']} n&uacute;cleos f&iacute;sicos
(SMT ativo). A distin&ccedil;&atilde;o importa: a lei de Amdahl sup&otilde;e n
processadores independentes, e dois vCPU sobre o mesmo n&uacute;cleo f&iacute;sico
n&atilde;o s&atilde;o independentes para trabalho limitado por processador.</td></tr>
<tr><td>Volume de entrada fixado para as medi&ccedil;&otilde;es</td>
<td>{INFRA['documentos_previstos']} editais, gerados por
<code>src/corpus.py</code> com semente fixa. A mesma semente reproduz byte a byte
o mesmo corpus, o que garante que T(1) e T(n) sejam medidos sobre a mesma entrada.</td></tr>
<tr><td>Como o tempo sequencial ser&aacute; obtido</td>
<td>Executando <code>src/sequencial.py</code>, que n&atilde;o tem fila,
<code>Manager</code> nem trava, tr&ecirc;s vezes, tomando a mediana. N&atilde;o se
usa a vers&atilde;o paralela com um trabalhador como T(1): ela j&aacute; carrega o
custo da infraestrutura de paraleliza&ccedil;&atilde;o e inflaria o speedup.</td></tr>
<tr><td>Fra&ccedil;&atilde;o do trabalho que a equipe estima ser
paraleliz&aacute;vel</td>
<td><strong>p &asymp; {virgula(p_valor, 4)}</strong> ({p_rotulo}).
Fica fora do trecho
paralelo: a listagem do diret&oacute;rio, a partida dos processos, a
redu&ccedil;&atilde;o final e a grava&ccedil;&atilde;o do relat&oacute;rio. A
vers&atilde;o sequencial cronometra separadamente a leitura e o trabalho por
documento, de modo que o valor instrumentado entra no relat&oacute;rio de 22/09
junto com a fra&ccedil;&atilde;o serial experimental de Karp-Flatt,
e = (1/S &minus; 1/n) / (1 &minus; 1/n).</td></tr>
<tr><td>Speedup previsto pela lei de Amdahl</td>
<td>S = 1 / ((1 &minus; p) + p/n), com p = {virgula(p_valor, 4)}:
<strong>n = 2 &rarr; {teto_2}</strong>;
<strong>n = 4 &rarr; {teto_4}</strong>;
<strong>n = {n} &rarr; {teto_n}</strong>.
A equipe espera ficar <em>abaixo</em> desses tetos, e o relat&oacute;rio vai
explicar a diferen&ccedil;a pelas tr&ecirc;s causas que a lei n&atilde;o modela:
comunica&ccedil;&atilde;o entre processos, espera na se&ccedil;&atilde;o
cr&iacute;tica e vCPU que n&atilde;o s&atilde;o n&uacute;cleos independentes.</td></tr>
</table>

<h2>E. Arquitetura na nuvem</h2>
<table class="evitar-quebra">
<tr><th style="width:21%">Decis&atilde;o</th><th style="width:21%">Escolha da equipe</th><th>Justificativa</th></tr>
<tr><td>Regi&atilde;o, e em quantas zonas de disponibilidade</td>
<td>{INFRA['regiao']}<br>uma zona ({INFRA['zona']})</td>
<td>Inst&acirc;ncia isolada em zona &uacute;nica: passa a valer o compromisso de
<strong>{INFRA['sla_uma_zona']}</strong>. Distribuir por duas ou mais zonas
elevaria o compromisso para {INFRA['sla_multi_zona']}, mas o experimento exige
que T(1) e T(n) sejam medidos no mesmo hardware &mdash; duas inst&acirc;ncias em
zonas diferentes n&atilde;o comparariam a mesma coisa &mdash; e a aplica&ccedil;&atilde;o
&eacute; um lote sob demanda, sem requisito de disponibilidade cont&iacute;nua.
A regi&atilde;o de S&atilde;o Paulo foi escolhida por lat&ecirc;ncia at&eacute; a
equipe e porque os dados tratados s&atilde;o de compras p&uacute;blicas brasileiras.</td></tr>
<tr><td>Fam&iacute;lia, tamanho e quantidade de inst&acirc;ncias</td>
<td>1 &times; {INFRA['tipo_instancia']}<br>({n} vCPU, otimizada para
computa&ccedil;&atilde;o)</td>
<td>Fam&iacute;lia sem cr&eacute;ditos de CPU. Inst&acirc;ncia burst&aacute;vel
(t2, t3) &eacute; inadequada para medir speedup: ao esgotar os cr&eacute;ditos o
desempenho cai no meio da medi&ccedil;&atilde;o e T(n) deixa de ser
compar&aacute;vel a T(1). Uma s&oacute; inst&acirc;ncia, porque o objeto da medida
&eacute; o ganho por n&uacute;cleo dentro de uma m&aacute;quina.</td></tr>
<tr><td>Onde ficam a entrada e a sa&iacute;da, e qual o volume</td>
<td>EBS gp3 de {INFRA['disco_gib']} GiB; c&oacute;pia no bucket S3
<code>{INFRA['bucket']}</code></td>
<td>O corpus (aprox. 150 MiB) &eacute; gerado no volume local, para que a leitura
n&atilde;o introduza lat&ecirc;ncia de rede dentro do tempo medido. Relat&oacute;rios,
registro de eventos e <code>medicao.json</code> (menos de 5 MiB) s&atilde;o
arquivados no S3 com bloqueio de acesso p&uacute;blico e criptografia SSE-S3, para
que sobrevivam ao encerramento da inst&acirc;ncia.</td></tr>
<tr><td>Portas abertas, e a origem de cada regra</td>
<td>22/tcp &larr; {INFRA['origem_admin']}<br>
{INFRA['porta_servico']}/tcp &larr; 0.0.0.0/0<br>
sa&iacute;da: liberada</td>
<td>A porta administrativa <strong>n&atilde;o</strong> est&aacute; aberta para
0.0.0.0/0 porque a porta 22 exposta &agrave; internet recebe tentativas
autom&aacute;ticas de autentica&ccedil;&atilde;o de forma cont&iacute;nua; restringir
a origem ao endere&ccedil;o da equipe retira a inst&acirc;ncia dessa superf&iacute;cie
sem depender da for&ccedil;a da chave. A porta {INFRA['porta_servico']} serve o
painel da aplica&ccedil;&atilde;o e &eacute; a &uacute;nica aberta ao p&uacute;blico.
A sa&iacute;da fica liberada para instalar pacotes e enviar os resultados ao S3.</td></tr>
<tr><td>A inst&acirc;ncia fica ligada, ou &eacute; criada por execu&ccedil;&atilde;o</td>
<td>Ligada durante a janela de medi&ccedil;&atilde;o e apresenta&ccedil;&atilde;o</td>
<td>Criar por execu&ccedil;&atilde;o traria hardware subjacente potencialmente
diferente entre T(1) e T(n), e o speedup exige a mesma m&aacute;quina. A
inst&acirc;ncia &eacute; encerrada ap&oacute;s a apresenta&ccedil;&atilde;o.</td></tr>
</table>


</body></html>"""


def main():
    p = argparse.ArgumentParser(description="Gera a ficha preenchida em PDF.")
    p.add_argument("--saida", default="ficha/ficha-etapa1-preenchida.pdf")
    p.add_argument("--medicao", default="resultados/medicao.json",
                   help="de onde ler a fracao paralelizavel instrumentada")
    p.add_argument("--rascunhos", default="rascunhos",
                   help="onde gravar o HTML intermediario")
    a = p.parse_args()

    conferir()

    # O HTML e um passo intermediario, nao um entregavel: fica fora de
    # relatorio/ e ficha/, para que essas pastas contenham so o PDF que vai ao
    # professor. Nao e versionado.
    os.makedirs(os.path.dirname(a.saida) or ".", exist_ok=True)
    os.makedirs(a.rascunhos, exist_ok=True)
    nome_base = os.path.splitext(os.path.basename(a.saida))[0] + ".html"
    caminho_html = os.path.join(a.rascunhos, nome_base)
    with open(caminho_html, "w", encoding="utf-8") as arq:
        arq.write(montar_html(a.medicao))
    print(f"html: {caminho_html}")

    usado = pdf.converter(caminho_html, a.saida)
    if usado:
        print(f"pdf : {a.saida}  (via {usado})")
    else:
        print("nenhum conversor de PDF encontrado (wkhtmltopdf, navegador sem "
              "tela ou weasyprint): imprima o HTML para PDF pelo navegador.")


if __name__ == "__main__":
    main()
