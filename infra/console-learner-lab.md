# Provisionar pelo console — AWS Academy Learner Lab

Guia clique a clique, para quem nunca mexeu na AWS. O `provisionar.md` ao lado
faz o mesmo pela linha de comando; **este aqui é o que serve para a
apresentação**, porque a lauda exige o console aberto ao vivo.

Tempo: 25 a 35 minutos até o painel responder de fora.

---

## O que você vai ter no fim

- uma instância EC2 ligada, com o projeto rodando;
- um grupo de segurança com a porta 22 restrita ao IP da equipe e a 8000 pública
  — **é esta tela que vale 0,5 ponto**;
- `http://<IP>:8000` abrindo no navegador de qualquer lugar.

---

## 0. Três coisas que o Learner Lab muda

Leia antes de começar. Cada uma obriga a mudar `src/configuracao.py` e a gerar
os PDFs de novo.

| O que muda | Por quê | O que fazer |
|---|---|---|
| **A região** | O Learner Lab costuma travar a região, quase sempre `us-east-1` (Norte da Virgínia). O projeto está escrito para `sa-east-1` (São Paulo). | Use a região que o lab permitir e ajuste `regiao` e `zona` em `configuracao.py`. |
| **O tipo de instância** | O lab bloqueia tipos grandes. `c6i.2xlarge` quase certamente será recusada. | Use o maior permitido e ajuste `tipo_instancia`, `vcpu` e `nucleos_fisicos`. |
| **A sessão expira** | O lab para tudo depois de algumas horas e ao acabar o crédito. | Rode a medição **hoje**, não amanhã de manhã. E dê *Start Lab* de novo antes de apresentar. |

Não tem problema a instância ser menor. O que a lauda cobra é T(1) e T(n) na
mesma máquina, com a mesma entrada, e a diferença explicada. Com 2 vCPU o
speedup fica perto de 1,8 em vez de 2,9 — e isso é um resultado legítimo, desde
que o relatório diga o número real.

---

## 1. Entrar

1. Abra o **Canvas** (ou o portal onde fica o material da disciplina).
2. Módulos → **AWS Academy Learner Lab** → **Launch AWS Academy Learner Lab**.
3. Na página do lab, clique em **Start Lab** (canto superior direito).
4. Espere a bolinha ao lado de *AWS* ficar **verde**. Leva 1 a 3 minutos.
5. Clique em **AWS** (ao lado da bolinha). Abre o console numa aba nova.

> A bolinha vermelha significa lab parado. Verde, ligado. Amarela, subindo.

**Anote o crédito** que aparece no topo (ex.: `$48 used of $100`). A instância
consome enquanto estiver ligada.

---

## 2. Conferir a região

No console, canto **superior direito**, ao lado do seu nome, há o nome de uma
região (ex.: *N. Virginia*). **Anote qual é.** Se o menu não deixar trocar, é
essa e pronto.

Clique nela para ver o código (`us-east-1`, `us-west-2`…). É esse código que
vai em `configuracao.py`.

---

## 3. Par de chaves

O Learner Lab já vem com uma chave pronta, e é mais rápido usar essa.

1. Volte à aba do lab (Canvas) e clique em **AWS Details** (ao lado de Start Lab).
2. Em *SSH key*, clique em **Download PEM**. Baixa o arquivo `labsuser.pem`.
3. No seu terminal, no Mac:

```bash
mkdir -p ~/.ssh
mv ~/Downloads/labsuser.pem ~/.ssh/
chmod 400 ~/.ssh/labsuser.pem
```

O `chmod 400` não é opcional: sem ele o SSH recusa a chave.

O nome dessa chave no console é **`vockey`**. É o que você vai escolher ao criar
a instância.

---

## 4. Grupo de segurança — o item que vale 0,5

**Faça este passo antes de criar a instância.** É esta tela que o João vai
mostrar na Demonstração 2.

1. No console, busque **EC2** na barra de busca do topo e entre.
2. Menu da esquerda → **Network & Security** → **Security Groups**.
3. **Create security group**.
4. Preencha:
   - *Security group name*: `sdp-etapa1-sg`
   - *Description*: `Etapa 1 - SSH restrito a equipe, 8000 publica`
   - *VPC*: deixe a que já vem marcada (`default`)

5. Em **Inbound rules**, clique **Add rule** duas vezes:

   **Regra 1 — a porta administrativa:**
   - *Type*: `SSH`
   - *Source*: clique no menu e escolha **My IP** ← **isto é o que importa**
   - *Description*: `SSH restrito a origem da equipe`

   > O console preenche sozinho o seu IP com `/32`. **Nunca escolha
   > *Anywhere-IPv4* aqui.** Porta 22 aberta para `0.0.0.0/0` zera o critério de
   > provisionamento — está escrito na lauda.

   **Regra 2 — a porta do serviço:**
   - *Type*: `Custom TCP`
   - *Port range*: `8000`
   - *Source*: **Anywhere-IPv4** (`0.0.0.0/0`)
   - *Description*: `Painel da aplicacao`

6. **Outbound rules**: não mexa. Sai tudo liberado, e é isso que queremos.
7. **Create security group**.

**Anote o IP que o console colocou na regra 1.** É o valor de `origem_admin` em
`configuracao.py` — algo como `189.45.12.33/32`.

> Se vocês forem apresentar de outra rede (a da faculdade, por exemplo), esse IP
> vai mudar e o SSH para de funcionar. No dia, volte aqui, **Edit inbound
> rules**, e escolha **My IP** de novo.

---

## 5. Lançar a instância

1. EC2 → menu da esquerda → **Instances** → **Launch instances**.
2. *Name*: `sdp-etapa1`
3. **Application and OS Images**: escolha **Ubuntu**. Deixe a versão que vier
   marcada (Ubuntu Server 24.04 LTS, *Free tier eligible*).
4. **Instance type**: clique no menu e procure, **nesta ordem de preferência**:

   | Tipo | vCPU | Se aparecer |
   |---|---|---|
   | `c5.2xlarge` ou `c5.xlarge` | 8 / 4 | ótimo, pegue |
   | `m5.xlarge` | 4 | bom |
   | `c5.large` / `m5.large` | 2 | serve — o speedup vai até ~1,8 |
   | `t3.medium` | 2 | último caso; burstável, veja a ressalva abaixo |

   **Anote o tipo e o número de vCPU.** Vão para `configuracao.py`.

   > Se der erro ao lançar dizendo que o tipo não é permitido, volte e desça um
   > degrau na tabela. O Learner Lab costuma liberar só até `large`.

   > `t3` é burstável: gasta crédito de CPU e o desempenho cai no meio da
   > medição. Se for a única opção, rode `medir.py --repeticoes 5` e registre a
   > limitação no relatório.

5. **Key pair (login)**: escolha **`vockey`** no menu.
6. **Network settings** → **Edit** → em *Firewall (security groups)* escolha
   **Select existing security group** e marque o **`sdp-etapa1-sg`** que você
   acabou de criar.
7. **Configure storage**: mude de 8 para **30** GiB, tipo `gp3`.
8. **Launch instance**.

Espere 1 a 2 minutos. Em **Instances**, a linha tem de mostrar *Running* e
*2/2 checks passed*.

**Clique na instância e anote o `Public IPv4 address`.** É o `<IP>` de tudo
daqui para a frente.

---

## 6. Conectar

No seu terminal, no Mac:

```bash
ssh -i ~/.ssh/labsuser.pem ubuntu@<IP>
```

Na primeira vez ele pergunta se confia no host: responda `yes`.

> **Não use o botão "Connect" do console** (EC2 Instance Connect). Ele conecta a
> partir de um IP da Amazon, e a nossa regra só aceita o IP de vocês — vai dar
> timeout. Isso é esperado, e é justamente a prova de que a regra funciona.

---

## 7. Preparar a máquina

Já conectado, cole tudo de uma vez:

```bash
sudo apt-get update -y
sudo apt-get install -y python3 git htop
git clone https://github.com/yuriaguiardev/projeto-scp.git projeto
cd projeto
python3 --version    # confirma que o Python existe
```

---

## 8. Ajustar `configuracao.py`

Ainda na instância:

```bash
nano src/configuracao.py
```

Troque, com os valores que você anotou:

- `"regiao"` — ex.: `"us-east-1 (Norte da Virginia)"`
- `"zona"` — o *Availability Zone* da instância, que aparece no console na aba
  *Details* (ex.: `"us-east-1c"`)
- `"tipo_instancia"`, `"vcpu"`, `"nucleos_fisicos"` — o tipo que você conseguiu.
  Para `c5.large`: `"c5.large"`, `2`, `1`
- `"origem_admin"` — o IP da regra 1, com `/32`
- `"bucket"` — se não for usar S3, escreva `"nao utilizado"`

Salvar no `nano`: `Ctrl+O`, `Enter`, `Ctrl+X`.

Confira:

```bash
python3 -c "import sys;sys.path.insert(0,'src');import configuracao as c;print(c.pendencias() or 'nada pendente')"
```

---

## 9. Gerar a entrada e medir

```bash
# quantos documentos dão ~3 min de execução sequencial NESTA máquina
python3 src/calibrar.py --alvo-minutos 3

# use o número que ele imprimir
python3 src/corpus.py --docs <NUMERO> --saida dados/corpus
python3 src/corpus.py --docs 400      --saida dados/amostra

# conferir que paralela == sequencial (rápido)
python3 src/verificar.py --corpus dados/amostra --trabalhadores <vCPU> --repeticoes 3
```

A medição demora. Rode dentro do `tmux`, para ela não morrer se a conexão cair:

```bash
sudo apt-get install -y tmux
tmux new -s medicao

python3 -u src/medir.py --corpus dados/corpus \
  --trabalhadores 1 2 <vCPU> --repeticoes 3 --com-thread | tee resultados/medicao.log
```

Para sair deixando rodando: `Ctrl+B`, depois `D`. Para voltar: `tmux attach -t medicao`.

Com 2 vCPU e alvo de 3 minutos, espere de 35 a 50 minutos. **Deixe rodando e vá
fazer outra coisa.**

---

## 10. Subir o serviço

```bash
sudo cp infra/triagem.service /etc/systemd/system/ 2>/dev/null || \
sudo tee /etc/systemd/system/triagem.service >/dev/null <<'UNIT'
[Unit]
Description=Triagem paralela de editais - Etapa 1
After=network-online.target
[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/projeto
ExecStart=/usr/bin/python3 src/servico.py --corpus dados/corpus --porta 8000
Restart=on-failure
[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable --now triagem
systemctl status triagem --no-pager
curl -s http://localhost:8000/api/saude
```

Tem de sair `{"estado": "vivo"}`.

**Agora o teste que importa:** no navegador **do seu computador**, abra
`http://<IP>:8000`. Se abrir, o grupo de segurança está certo.

---

## 11. Trazer os resultados e fechar os PDFs

Na **sua máquina**, não na instância:

```bash
cd ~/Downloads/projeto-sdp-etapa1
scp -i ~/.ssh/labsuser.pem ubuntu@<IP>:projeto/resultados/'*.json' resultados/
scp -i ~/.ssh/labsuser.pem ubuntu@<IP>:projeto/src/configuracao.py src/
python3 src/gerar_relatorio.py
python3 src/gerar_ficha.py
git add -A && git commit -m "Medicao na instancia EC2" && git push
```

Os PDFs passam a descrever a instância real, com os números medidos nela.

---

## 12. Antes de apresentar

- [ ] **Start Lab** de novo, e esperar a bolinha verde. A instância volta sozinha.
- [ ] Confirmar que a instância está *Running* e pegar o IP — **ele muda a cada
      parada e partida**, a não ser que vocês associem um Elastic IP.
- [ ] Se o IP mudou, `http://<IP-novo>:8000`.
- [ ] Se estiverem em outra rede, refazer a regra 22 com **My IP**.
- [ ] Deixar aberta a tela **Security Groups → sdp-etapa1-sg → Inbound rules**.
      É a tela da Demonstração 2.

---

## Se der errado

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| `Permission denied (publickey)` | `chmod 400` esquecido, ou usuário errado | `chmod 400 ~/.ssh/labsuser.pem`; o usuário é `ubuntu`, não `ec2-user` |
| SSH dá timeout | seu IP mudou, ou a regra ficou com outro valor | EC2 → Security Groups → Edit inbound rules → Source: **My IP** |
| `http://<IP>:8000` não abre | regra da 8000 ausente, ou serviço no ar | conferir a regra; `systemctl status triagem` |
| "instance type not supported" | Learner Lab bloqueou o tipo | desça um degrau na tabela do passo 5 |
| A instância sumiu | a sessão do lab expirou | **Start Lab** de novo; ela volta parada, dê *Start* nela em EC2 → Instances |
| O crédito acabou | nada a fazer na conta | Plano B: rodar as demonstrações 1 e 3 no laptop, **ao vivo**, dizendo que é o laptop |
