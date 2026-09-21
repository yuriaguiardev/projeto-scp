# Roteiro da apresentação — 10 minutos

**Formato:** os dez slides primeiro, sem interrupção; depois as três
demonstrações ao vivo, seguidas; o fecho no fim.

Deck: <https://claude.ai/artifact/F4cBDWrypS59uB7hCk5UxH>

O slide 9 (**"Tudo o que foi dito, agora acontecendo"**) é a única passagem
entre os dois blocos. Depois dele ninguém volta ao deck até o fecho.

> **Por que assim.** A lauda lista as cinco partes "nesta ordem", e agrupar as
> demonstrações no fim inverte duas delas: o ganho aparece antes da execução.
> Isso é uma escolha, não um descuido — e tem de ser **dita em voz alta** no
> slide 9: *"até aqui foi o que medimos; agora as três provas"*. Sem essa frase
> a inversão parece desorganização.

---

## Quem faz o quê

Cada um apresenta um bloco de slides **e** conduz a demonstração
correspondente. Na arguição, cada um responde sobre a parte de **outro** — a
seção de arguição prepara isso.

| Integrante | Slides | Demonstração |
|---|---|---|
| Yuri Aguiar | 1, 2, 3, a passagem (9) e o fecho (10) | — |
| Pedro Paulo | 4, 5 | 1 · a condição de corrida |
| João Rath | 6 | 2 · o console da AWS |
| Fábio Gabriel | 7, 8 | 3 · o painel |

---

## Antes de entrar na sala

Na instância, com tudo já rodado:

```bash
python3 src/corpus.py --docs 15000 --saida dados/corpus    # medição (minutos)
python3 src/corpus.py --docs 400   --saida dados/amostra   # demo (segundos)
sudo systemctl start triagem
curl -s http://localhost:8000/api/saude
```

`resultados/medicao.json` e `resultados/eventos.json` já no lugar: a medição é
trabalho de antes, a execução ao vivo é a prova.

Na máquina que projeta, abertos e **já carregados**, nesta ordem de abas:

1. o deck, em modo apresentação;
2. um terminal com SSH na instância, no diretório do projeto;
3. o console da AWS, **já na página do grupo de segurança** (não na tela de login);
4. o navegador em `http://<IP>:8000`, já respondendo.

Deixe o `htop` rodando num segundo painel do terminal.

---

## Bloco 1 — Slides · 5 min 50

O tempo acumulado está à direita. Se passar de **6 min 10** no slide 9, corte o
slide 8 na hora: as três causas estão no relatório.

| | Slide | Quem | Tempo | Acum. |
|---|---|---|---|---|
| 1 | Capa | Yuri | 0:15 | 0:15 |
| 2 | O problema | Yuri | 0:40 | 0:55 |
| 3 | A unidade de trabalho | Yuri | 0:50 | 1:45 |
| 4 | A seção crítica | Pedro Paulo | 0:55 | 2:40 |
| 5 | As duas corridas | Pedro Paulo | 0:40 | 3:20 |
| 6 | As decisões na nuvem | João Rath | 0:45 | 4:05 |
| 7 | O ganho medido | Fábio Gabriel | 0:45 | 4:50 |
| 8 | O que Amdahl não modela | Fábio Gabriel | 0:45 | 5:35 |
| 9 | A passagem | Yuri | 0:15 | 5:50 |

As falas de cada slide estão na seção **Falas**, e também nas notas do
apresentador do deck.

---

## Bloco 2 — Demonstração ao vivo · 3 min 40

**A partir daqui, nada de slides.** Nada gravado, nada em captura de tela: a
lauda tira nota por isso, e o console por captura zera o critério de
provisionamento.

### Demonstração 1 — a condição de corrida · Pedro Paulo · 1:10 → 7:00

Terminal. Nesta ordem, sem pular a primeira:

```bash
# 1. com trava — a mesma entrada, oito execuções
python3 src/verificar.py --corpus dados/amostra --trabalhadores 8 \
        --lote 25 --repeticoes 8
```

Quando terminar, apontar `ESTÁVEL` e `EQUIVALENTE`.

```bash
# 2. sem trava — a mesma entrada, resultados diferentes
python3 src/verificar.py --corpus dados/amostra --trabalhadores 8 \
        --lote 3 --repeticoes 8 --modo nenhuma --pular-sequencial
```

Sai `INSTÁVEL` e a lista de impressões digitais distintas.

Se alguma linha mostrar a contagem certa com SHA diferente, apontar: é o
argumento de que conferir o total não prova nada.

### Demonstração 2 — o console da AWS · João Rath · 1:00 → 8:00

Console ao vivo, três paradas e nada mais:

1. **EC2 → a instância** — tipo, zona e estado.
2. **Aba Segurança → o grupo de segurança → Regras de entrada** — demorar aqui:
   `22/tcp` com origem `<IP-da-equipe>/32`, `8000/tcp` com origem `0.0.0.0/0`.
3. Fechar dizendo por que a 22 é restrita.

### Demonstração 3 — o painel · Fábio Gabriel · 1:20 → 9:20

Navegador em `http://<IP>:8000`, com o `htop` visível ao lado.

1. **sequencial** — enquanto roda, mostrar no `htop`: **um núcleo só** ocupado.
2. **paralela n = 8** — no `htop`, **todos** os núcleos.
3. A tabela do painel põe os dois tempos, o speedup e os dois SHA-256 lado a
   lado. **Apontar que as impressões digitais são iguais.**
4. Se sobrar tempo: **threads (GIL)** — o tempo volta ao do sequencial.

> Se o corpus grande demorar demais no dia, aponte o serviço para
> `dados/amostra`. Os tempos caem, a relação entre eles se mantém, e a tabela
> do relatório continua sendo a do corpus completo.

---

## Fecho · Yuri · 0:20 → 9:40

Voltar ao deck, slide 10. **Deixar esse slide no ar durante toda a arguição:**
as três colunas são as respostas curtas para as perguntas mais prováveis.

Sobram 20 segundos de folga em 10 minutos. O limite real é 12.

---

## Se algo falhar

| O que falha | O que fazer |
|---|---|
| A instância não responde | Rodar as demonstrações 1 e 3 no laptop, dizendo que é o laptop. Ao vivo no laptop vale; gravado não vale. |
| O painel não sobe | `sudo systemctl status triagem`, e cair para o terminal: `python3 src/sequencial.py` e `python3 src/paralelo.py --trabalhadores 8`. |
| O console pede login | João assume e faz login ao vivo. Levar mais de 30 s? Passar para a demo 3 e voltar ao console no fim. |
| O tempo estourou | Cortar a demonstração 3 para só sequencial + paralela, sem threads. Nunca cortar a demonstração 1: é o critério de sincronização. |

Ensaiem cronometrados uma vez. As duas execuções da demonstração 1 são as mais
imprevisíveis — se passarem de 45 s juntas, aumentem o `--lote` da primeira.
Mudar o número de repetições obriga a mudar também a seção C da ficha, que diz
"oito execuções".

---

## Falas

Escritas para serem ditas, não lidas: a ordem das ideias importa mais que as
palavras exatas. O tempo ao lado do nome é o alvo, medido a 150 palavras por
minuto. Cada bloco termina com a direção de cena, em itálico.

São as mesmas falas que estão nas notas do apresentador do deck — se mudarem
aqui, mudem lá também.


### Slide 1 — Capa · Yuri · 0:15

> Bom dia. O nosso projeto é uma triagem automática de editais de compra pública. Eu começo pelo problema, o Pedro mostra a seção crítica, o João os recursos na nuvem e o Fábio a medição. Terminados os slides, fazemos três demonstrações ao vivo.

*Cena:* Não ficar na capa. Passar assim que terminar a frase.


### Slide 2 — O problema · Yuri · 0:40

> O PNCP publica dezenas de milhares de editais por mês. Uma empresa que vende software para prefeitura precisa achar, nesse volume, os que interessam — e precisa achar antes de a sessão pública abrir. Triagem manual não acompanha.
>
> A nossa entrada são seis mil e quinhentos editais, sessenta e seis megabytes de texto. A saída é um relatório de triagem: ranking dos mais aderentes, distribuição por linha de produto e contagem de republicações.
>
> E o custo está aqui, no terceiro cartão: cada documento gera uma assinatura MinHash de sessenta e quatro posições. É aritmética de inteiro em Python puro — é isso que torna o trabalho limitado por processador, e não por espera.

*Cena:* Não ler os cartões. Apontar o terceiro ao dizer 'o custo está aqui'.


### Slide 3 — A unidade de trabalho · Yuri · 0:50

> A unidade de trabalho é um edital. Para cada um, quatro etapas: normalizar o texto, tokenizar, pontuar contra uma taxonomia de sessenta e sete termos com peso — positivos para gestão e arrecadação, negativos para obra e merenda — e calcular a assinatura que reconhece o mesmo edital republicado por municípios diferentes.
>
> Mas o que importa para este projeto é a última linha. As funções do núcleo são puras, o módulo não tem estado global, e um edital não lê nem escreve nada de outro. A única dependência aparece na agregação dos resultados — e agregar é associativo e comutativo.
>
> É exatamente por isso que o trabalho se divide. E é essa agregação que o Pedro vai ter de proteger agora.

*Cena:* Se der tempo, abrir processar_documento no editor enquanto fala das etapas.


### Slide 4 — A seção crítica · Pedro Paulo · 0:55

> Este é o único trecho do programa que mais de um fluxo escreve. O estado compartilhado é o agregador global: contadores, dicionário de termos, ranking, mapa de assinaturas e o relógio lógico.
>
> A seção crítica é só esta função, a fundir no global. Reparem no que está fora dela: os cento e cinquenta documentos do lote são processados antes do acquire, num agregado parcial local ao processo. Dentro da trava entra só a fusão desse parcial.
>
> As duas linhas em destaque são as que não toleram entrelaçamento: o contador, que é ler, somar e gravar, e o verificar-então-agir no mapa de assinaturas.
>
> A primitiva é um Lock do multiprocessing. Um escritor por vez, sem condição de espera a sinalizar — não precisa de semáforo contado nem de monitor.

*Cena:* Abrir paralelo.py no editor e apontar a função de verdade. Se perguntarem por que o laço não está dentro da trava: estaria correto, mas serializaria tudo, e existe no modo --sincronizacao larga.


### Slide 5 — As duas corridas · Pedro Paulo · 0:40

> Sem a trava, aparecem duas corridas. A primeira é atualização perdida: ler, somar e gravar são três passos, e entre o primeiro e o terceiro cabe a gravação de outro trabalhador, que se perde.
>
> A segunda é verificar-então-agir: dois trabalhadores perguntam se a mesma assinatura já existe, os dois recebem não, e uma republicação deixa de ser contada.
>
> E olhem o quadro de baixo, que é uma execução real nossa, sem trava. Nesta linha o contador bateu — quatrocentos documentos, o número certo — e mesmo assim o SHA mudou. Conferir o total não prova nada. Por isso a nossa verificação é o SHA-256 do relatório inteiro.

*Cena:* O quadro escuro é o argumento mais forte do bloco. Não passar rápido por ele.


### Slide 6 — As decisões na nuvem · João Rath · 0:45

> Uma instância, na região de São Paulo, numa zona só. Zona única significa que passa a valer o compromisso de noventa e nove e meio por cento do SLA — duzentos e dezesseis minutos por mês. Duas zonas dariam quatro minutos, mas o experimento exige a mesma máquina para o T de um e o T de n.
>
> Família otimizada para computação, sem créditos de CPU: uma burstável esgotaria crédito no meio da medição.
>
> E a linha destacada: a porta vinte e dois aceita só o IP da nossa equipe. Nunca aberta para qualquer origem, porque a porta vinte e dois exposta à internet recebe tentativa de autenticação automática o tempo todo. A oito mil é a única pública, e serve o painel.

*Cena:* Dizer a frase da porta 22 AQUI, com calma. Quando o console abrir, no bloco ao vivo, ela já vai estar dita e é só apontar a regra.


### Slide 7 — O ganho medido · Fábio Gabriel · 0:45

> Estes são os tempos medidos: três repetições por configuração, a tabela traz a mediana, mesma máquina e mesma entrada. O T de um vem da versão sequencial, não da paralela com um trabalhador — essa já carrega o custo da fila e do Manager.
>
> A linha que importa é a de n igual a seis: o tempo caiu de oitenta e três para vinte e oito segundos. Speedup de dois vírgula nove quatro, contra um teto de Amdahl de cinco vírgula sete.
>
> E a última linha é a prova de que escolher processos não foi estilo: com threads, o speedup é um vírgula zero sete. O GIL serializa o bytecode. Daqui a pouco vocês vão ver as três rodando.

*Cena:* A última coluna diz que todas as configurações deram o mesmo SHA da sequencial. Mencionar de passagem: é o critério de correção.


### Slide 8 — O que Amdahl não modela · Fábio Gabriel · 0:45

> Por que dois vírgula nove quatro, e não cinco vírgula sete? A métrica de Karp-Flatt responde com número. Ela deduz a fração serial do próprio speedup medido e devolve zero vírgula dois zero oito. O nosso p instrumentado dá um menos p de zero vírgula zero um. Vinte vezes de diferença.
>
> Essa distância é o custo que a paralelização introduziu e que não existia na versão sequencial. Tem três origens: comunicação entre processos, porque o agregador vive num processo separado e cada acesso é ida e volta por soquete; divisão desigual, porque o custo do MinHash varia com o documento; e espera na trava — que nós medimos, e é a menor das três: zero vírgula zero quatro por cento.

*Cena:* Slide da arguição. Se perguntarem de onde veio o p: a versão sequencial cronometra separadamente a leitura e o trabalho por documento.


### Slide 9 — A passagem · Yuri · 0:15

> Até aqui foi o que nós medimos. Agora as três provas, ao vivo: o Pedro mostra a condição de corrida acontecendo, o João abre o console da AWS, e o Fábio roda as duas versões no painel.

*Cena:* SAIR DOS SLIDES ao terminar a frase. Não ler os cartões — eles são só o mapa.


### Fecho · Yuri · 0:20

> Fechando. As sete configurações paralelas e a sequencial produzem o mesmo SHA-256: paralelizar mudou o tempo, não mudou o resultado. Sem a trava, a mesma entrada devolve resultados diferentes a cada execução. E o ganho ficou abaixo do teto de Amdahl por causas que nós medimos, não supomos. Obrigado.

*Cena:* Deixar este slide no ar durante toda a arguição: as três colunas são as respostas curtas para as perguntas mais prováveis.


### Durante as demonstrações

O tempo de máquina preenche o resto; estas são as frases que enquadram
o que aparece na tela.


**Demonstração 1 — a condição de corrida** · Pedro Paulo · 1:10

> Mesma entrada, quatrocentos editais, oito trabalhadores. Primeiro com a trava.
>
> [enquanto roda] Vão sair oito execuções paralelas. O que eu quero mostrar é que as oito impressões digitais são iguais entre si, e iguais à da versão sequencial, que roda na primeira linha.
>
> [ao terminar] Aqui: ESTÁVEL e EQUIVALENTE.
>
> Agora a mesma coisa sem a trava. Só mudei o modo de sincronização.
>
> [ao terminar] INSTÁVEL. A mesma entrada, impressões digitais diferentes a cada execução. Isto é a corrida acontecendo, não uma descrição dela.


**Demonstração 2 — o console da AWS** · João Rath · 1:00

> Este é o console, ao vivo. Esta é a nossa instância: o tipo, a zona, o estado.
>
> Aba Segurança, o grupo de segurança, regras de entrada. Aqui: porta vinte e dois, origem só o IP da nossa equipe, barra trinta e dois. E porta oito mil, aberta para todos, que é o painel da aplicação.
>
> A porta administrativa não está aberta para qualquer origem, porque a porta vinte e dois exposta à internet recebe tentativa de autenticação automática de forma contínua. Restringir a origem tira a instância dessa superfície sem depender da força da chave.


**Demonstração 3 — o painel** · Fábio Gabriel · 1:20

> Este é o painel da aplicação, na porta oito mil da instância. Vou clicar em sequencial.
>
> [enquanto roda] Olhem o htop ao lado: um núcleo só ocupado. É um fluxo de execução.
>
> [ao terminar] Agora a paralela, com oito trabalhadores.
>
> [enquanto roda] Agora todos os núcleos.
>
> [ao terminar] A tabela põe os dois lado a lado: o tempo caiu, o speedup está aqui — e reparem nas duas últimas colunas, as impressões digitais. São iguais. Mesma saída, menos tempo.
>
> [se sobrar tempo] E este botão roda com threads: o tempo volta ao do sequencial. É o GIL.

---

## Arguição — o que cada um precisa saber da parte que NÃO apresentou

**Sobre o problema (para quem não é o Yuri)**
- *Qual é a unidade de trabalho?* Um edital.
- *Por que as partes são independentes?* As funções de `nucleo.py` são puras e
  não há estado global; a única dependência é a agregação, que é associativa e
  comutativa.
- *Como sabem que o resultado está certo?* O relatório é canonizado e reduzido a
  um SHA-256; paralela e sequencial têm de bater.
- *De onde veio o volume?* `calibrar.py` mede o custo por documento na própria
  instância e calcula quantos documentos dão o alvo de minutos.

**Sobre a seção crítica (para quem não é o Pedro Paulo)**
- *Qual é exatamente a seção crítica?* A função `fundir_no_global` — a fusão de
  um parcial no agregado global, não o processamento dos documentos.
- *Por que Lock e não semáforo?* Um escritor por vez, sem condição de espera a
  sinalizar nem contagem de permissões.
- *O que acontece sem a trava?* Atualização perdida nos contadores e
  verificar-então-agir no mapa de assinaturas; o SHA-256 muda a cada execução.
- *Por que o laço não está dentro da trava?* Estaria correto, mas serializaria
  tudo e o speedup cairia para perto de 1. Existe no modo `--sincronizacao larga`.
- *Tem troca de mensagem? E carimbo lógico?* Sim: a fila de lotes e o canal do
  `Manager`. Relógio de Lamport; cada evento registra quem, o quê, carimbo e
  sobre o quê. O registro está em `resultados/eventos.json`.

**Sobre a nuvem (para quem não é o João Rath)**
- *Região e zona?* sa-east-1, zona sa-east-1a, uma só.
- *Qual SLA passa a valer?* 99,5 %, 216 min/mês. Multi-AZ seria 99,99 %, 4,3 min.
- *Por que a 22 não está aberta para todo mundo?* Varredura automática contínua
  contra a 22; restringir a origem tira a instância dessa superfície.
- *Por que não usaram t3?* Burstável esgota crédito de CPU no meio da medição.
- *Por que uma zona só?* O experimento exige a mesma máquina para T(1) e T(n).

**Sobre a medição (para quem não é o Fábio Gabriel)**
- *De onde vem o T(1)?* Da versão sequencial, na mesma máquina e com a mesma
  entrada — não da paralela com um trabalhador, que já carrega o custo da fila
  e do `Manager`.
- *Por que processos e não threads?* Trabalho limitado por processador; em
  CPython o GIL serializa bytecode. Medimos as duas.
- *Por que o speedup ficou abaixo do teto de Amdahl?* Amdahl não modela
  comunicação entre processos, divisão desigual do trabalho nem espera na seção
  crítica. A espera foi medida: 0,04 % do tempo de trabalhador.
- *De onde veio o p?* Instrumentado: a versão sequencial cronometra
  separadamente a leitura e o trabalho por documento.

---

## O que derruba nota — conferir antes de entrar

- [ ] Demonstração **ao vivo**, nada gravado nem em captura de tela.
- [ ] Console da AWS **aberto**, não impresso.
- [ ] T(1) medido **na mesma máquina** e com **a mesma entrada** que T(n).
- [ ] Repositório e os dois PDFs no ambiente virtual **antes** do início do encontro.
- [ ] Não estourar 10 min em mais de 2.
- [ ] Porta 22 **não** em `0.0.0.0/0`.
- [ ] Nenhum `PREENCHER` sobrando: `python3 -c "import sys;sys.path.insert(0,'src');import configuracao as c;print(c.pendencias() or 'ok')"`.
- [ ] `python3 src/gerar_relatorio.py` sem recado de "conferir antes de entregar".
- [ ] A medição do relatório é a do corpus grande, não a da `dados/amostra`.
- [ ] Relatório com **até seis páginas**, como a lauda pede.
- [ ] Os números do slide 7 batem com a tabela da seção 5 do relatório.
