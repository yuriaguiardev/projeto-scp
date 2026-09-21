# Triagem paralela de editais de compra pública

Etapa 1 do Projeto de Solução Distribuída — **070080 Sistemas Distribuídos e
Paralelos**, turma CC6MA, Prof. Fábio Rocha de Araújo.

Equipe: Yuri Aguiar · Pedro Paulo · João Rath · Fábio Gabriel

---

## O que a aplicação faz

Lê um lote de editais de compra pública em texto e, para cada um:

1. normaliza (NFKD, remove acentos, caixa baixa);
2. tokeniza e descarta palavras vazias;
3. pontua a aderência contra uma taxonomia de termos com peso — positivos para
   software de gestão e arrecadação, negativos para obra, merenda, combustível;
4. calcula uma **assinatura MinHash** de 64 posições sobre os *shingles* de
   cinco tokens da seção do objeto, para reconhecer o mesmo edital republicado
   por municípios diferentes.

A saída é um relatório com ranking dos editais mais aderentes, distribuição por
linha de produto, frequência dos termos e contagem de republicações.

A etapa 4 é aritmética de inteiros em Python puro, dezenas de milhares de
operações por documento: é ela que domina o tempo e torna o trabalho **limitado
por processador**.

---

## Como as duas versões se relacionam

| | `src/sequencial.py` | `src/paralelo.py` |
|---|---|---|
| Fluxos | 1 | n processos |
| Trabalho por documento | `nucleo.processar_documento` | `nucleo.processar_documento` — o mesmo |
| Estado compartilhado | nenhum | agregador em `Manager` |
| Seção crítica | não existe | `fundir_no_global` |
| Primitiva | — | `multiprocessing.Lock` |

O trabalho por documento é literalmente a mesma função nas duas, importada de
`src/nucleo.py`. É o que torna a comparação de tempos honesta.

---

## Estrutura

O que vai ao professor fica na raiz; o que é material de trabalho da equipe
fica em `apresentacao/`.

**Entregue** — código-fonte em repositório, relatório em PDF e a ficha:

```
src/
  nucleo.py          trabalho por documento (puro, sem estado global)
  corpus.py          gerador determinístico da entrada
  sequencial.py      versão de referência — dá o T(1)
  paralelo.py        processos, fila de lotes, memória compartilhada e Lock
  verificar.py       equivalência (par == seq) e estabilidade (par == par)
  medir.py           bancada: speedup, Amdahl, Karp-Flatt
  calibrar.py        dimensiona o corpus para a máquina da medição
  servico.py         painel HTTP na porta 8000
  configuracao.py    dados da equipe e da infraestrutura
  gerar_relatorio.py monta relatorio/relatorio.pdf a partir da medição
  gerar_ficha.py     monta ficha/ficha-etapa1-preenchida.pdf
  pdf.py             converte HTML em PDF pelo conversor que houver na máquina
infra/
  provisionar.md     passo a passo na AWS (console e CLI)
  user-data.sh       bootstrap da instância
relatorio/relatorio.pdf
ficha/ficha-etapa1-preenchida.pdf
resultados/
  medicao.json       a medição que sustenta a tabela do relatório
  eventos.json       as fusões com carimbo lógico, citadas na seção C da ficha
```

**Interno** — nada aqui é entregue:

```
apresentacao/
  LEIAME.md          o que é entregue e o que não é
  roteiro.md         roteiro dos 10 minutos e preparo para a arguição
  rascunhos/         o HTML que os geradores produzem antes do PDF
```

`dados/` guarda o corpus gerado e não é versionado: são 79 MiB que
`python3 src/corpus.py` reproduz byte a byte a partir da semente fixa.

Só biblioteca padrão: nada a instalar além do Python (3.8 ou mais novo; a
instância roda 3.12, e o projeto foi exercitado também em 3.9).

A única dependência externa é opcional e serve só para fechar os PDFs:
`src/pdf.py` tenta, nesta ordem, `wkhtmltopdf`, um navegador sem tela
(Chrome/Chromium/Edge) e `weasyprint`. Não havendo nenhum, o HTML fica em
`apresentacao/rascunhos/` e pode ser impresso para PDF pelo navegador.

---

## Uso

```bash
# 1. dimensionar a entrada para esta máquina
python3 src/calibrar.py --alvo-minutos 4

# 2. gerar o corpus (use o número que a calibração indicou)
python3 src/corpus.py --docs 15000 --saida dados/corpus
python3 src/corpus.py --docs 400   --saida dados/amostra   # para a demo ao vivo

# 3. rodar
python3 src/sequencial.py --corpus dados/corpus
python3 src/paralelo.py   --corpus dados/corpus --trabalhadores 8

# 4. provar que dá no mesmo
python3 src/verificar.py --corpus dados/amostra --trabalhadores 8 --repeticoes 5

# 5. mostrar a condição de corrida
python3 src/verificar.py --corpus dados/amostra --trabalhadores 8 \
        --lote 3 --repeticoes 8 --modo nenhuma --pular-sequencial

# 6. medir e gerar o relatório com os números medidos
#    (-u para ver o progresso: a medição leva dezenas de minutos)
python3 -u src/medir.py --corpus dados/corpus --trabalhadores 1 2 4 8 \
        --repeticoes 3 --com-thread
python3 src/gerar_relatorio.py
python3 src/gerar_ficha.py

# 7. painel
python3 src/servico.py --corpus dados/corpus --porta 8000
```

### O que a medição produz

| Arquivo | Conteúdo |
|---|---|
| `resultados/medicao.json` | tempos, speedup, teto de Amdahl, Karp-Flatt, máquina e corpus. É a única fonte dos números do relatório. |
| `resultados/eventos.json` | registro das fusões no agregador global: quem, o quê, carimbo lógico de Lamport e sobre o quê. É o que a seção C da ficha descreve. |

`gerar_relatorio.py` e `gerar_ficha.py` leem esses arquivos. Enquanto eles não
existirem, o relatório sai com as tabelas vazias e a ficha usa a fração
paralelizável estimada em vez da medida. Os avisos saem no terminal, na hora de
gerar; o PDF nunca carrega texto de controle interno.

### Modos de sincronização

`src/paralelo.py --sincronizacao <modo>`

| Modo | O que faz | Para quê |
|---|---|---|
| `lock` | seção crítica mínima, protegida por `Lock` | o correto; é o modo medido |
| `nenhuma` | sem trava | expor a condição de corrida ao vivo |
| `larga` | trava em volta do laço inteiro | mostrar que correto ≠ paralelo |

`--motor thread` roda a mesma coisa com `threading`, para medir o efeito do GIL.

---

## Antes de entregar

1. Preencher `src/configuracao.py`: matrículas, URL do repositório, IP público
   da equipe, nome do bucket e — se a conta AWS não permitir `c6i.2xlarge` — o
   tipo de instância e a contagem de núcleos. Os geradores conferem sozinhos:
   o que faltar sai listado no terminal na hora de gerar, e não entra no PDF.
   Para conferir sem gerar nada:

   ```bash
   python3 -c "import sys; sys.path.insert(0,'src'); import configuracao as c; print(c.pendencias() or 'nada pendente')"
   ```

2. Rodar a medição **na instância** e gerar o relatório:
   `python3 -u src/medir.py ... && python3 src/gerar_relatorio.py`.
   Sem isso o PDF sai com as tabelas vazias. Se a medição não vier da instância
   descrita em `configuracao.py`, `gerar_relatorio.py` avisa no terminal — o PDF
   sai limpo de qualquer jeito, mas a medição precisa ser a da instância.
3. Gerar a ficha: `python3 src/gerar_ficha.py`.
4. Subir repositório e os dois PDFs no ambiente virtual **antes** do início do
   encontro de apresentação.
