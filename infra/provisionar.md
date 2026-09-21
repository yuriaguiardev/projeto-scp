# Provisionamento na AWS

Tudo aqui pode ser feito pelo console, e **na apresentação tem de ser pelo
console, ao vivo**. Os comandos da CLI estão junto para que o provisionamento
fique registrado e possa ser repetido.

Substitua os valores entre `<>` antes de rodar.

---

## 0. Antes de começar

Descubra o IP público da equipe — é a origem da regra da porta 22:

```bash
curl -s https://checkip.amazonaws.com
```

Use o IP de onde vocês vão se conectar no dia. Se for a rede da faculdade,
confirme o IP no dia da apresentação: ele pode mudar.

Variáveis usadas abaixo:

```bash
REGIAO=sa-east-1
ZONA=sa-east-1a
TIPO=c6i.2xlarge          # 8 vCPU / 16 GiB, sem créditos de CPU
NOME=sdp-etapa1
MEU_IP=$(curl -s https://checkip.amazonaws.com)/32
```

---

## 1. Par de chaves

```bash
aws ec2 create-key-pair --region $REGIAO --key-name $NOME-chave \
  --query 'KeyMaterial' --output text > ~/$NOME-chave.pem
chmod 400 ~/$NOME-chave.pem
```

---

## 2. Grupo de segurança

Este é o item que vale 0,5 ponto. **Porta administrativa aberta para 0.0.0.0/0
zera o critério.**

```bash
VPC=$(aws ec2 describe-vpcs --region $REGIAO --filters Name=isDefault,Values=true \
      --query 'Vpcs[0].VpcId' --output text)

SG=$(aws ec2 create-security-group --region $REGIAO \
     --group-name $NOME-sg \
     --description "Etapa 1 - SSH restrito a equipe, 8000 publica" \
     --vpc-id $VPC --query 'GroupId' --output text)

# porta administrativa: SOMENTE o IP da equipe
aws ec2 authorize-security-group-ingress --region $REGIAO --group-id $SG \
  --ip-permissions "IpProtocol=tcp,FromPort=22,ToPort=22,\
IpRanges=[{CidrIp=$MEU_IP,Description='SSH restrito a origem da equipe'}]"

# porta do serviço: pública
aws ec2 authorize-security-group-ingress --region $REGIAO --group-id $SG \
  --ip-permissions "IpProtocol=tcp,FromPort=8000,ToPort=8000,\
IpRanges=[{CidrIp=0.0.0.0/0,Description='Painel da aplicacao'}]"
```

Confira antes da apresentação — é exatamente esta saída que o professor vai
querer ver na tela:

```bash
aws ec2 describe-security-groups --region $REGIAO --group-ids $SG \
  --query 'SecurityGroups[0].IpPermissions[].{porta:FromPort,origem:IpRanges[].CidrIp}'
```

| Porta | Origem | Por quê |
|---|---|---|
| 22/tcp | `<IP-da-equipe>/32` | A porta 22 exposta à internet recebe tentativas automáticas de autenticação de forma contínua. Restringir a origem tira a instância dessa superfície sem depender da força da chave. |
| 8000/tcp | `0.0.0.0/0` | Painel da aplicação. É a única porta que precisa ser pública. |
| saída | liberada | Instalar pacotes e enviar resultados ao S3. |

> Alternativa mais forte, se quiserem: não abrir a porta 22 de jeito nenhum e
> acessar por **AWS Systems Manager Session Manager**, que usa a saída HTTPS.
> Nesse caso a instância precisa de um perfil IAM com `AmazonSSMManagedInstanceCore`.

---

## 3. Instância

```bash
AMI=$(aws ssm get-parameters --region $REGIAO \
  --names /aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id \
  --query 'Parameters[0].Value' --output text)

aws ec2 run-instances --region $REGIAO \
  --image-id $AMI --instance-type $TIPO \
  --key-name $NOME-chave --security-group-ids $SG \
  --placement AvailabilityZone=$ZONA \
  --block-device-mappings '[{"DeviceName":"/dev/sda1",
     "Ebs":{"VolumeSize":30,"VolumeType":"gp3","DeleteOnTermination":true}}]' \
  --user-data file://infra/user-data.sh \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$NOME}]" \
  --query 'Instances[0].InstanceId' --output text
```

Pegue o IP público:

```bash
aws ec2 describe-instances --region $REGIAO \
  --filters Name=tag:Name,Values=$NOME Name=instance-state-name,Values=running \
  --query 'Reservations[].Instances[].{id:InstanceId,ip:PublicIpAddress,az:Placement.AvailabilityZone,tipo:InstanceType}'
```

---

## 4. Bucket S3 para a saída

```bash
BUCKET=$NOME-<sufixo-unico>
aws s3api create-bucket --bucket $BUCKET --region $REGIAO \
  --create-bucket-configuration LocationConstraint=$REGIAO
aws s3api put-public-access-block --bucket $BUCKET \
  --public-access-block-configuration \
  "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
aws s3api put-bucket-encryption --bucket $BUCKET \
  --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
```

---

## 5. Na instância

```bash
ssh -i ~/$NOME-chave.pem ubuntu@<IP-PUBLICO>

git clone <URL-do-repositorio> projeto && cd projeto

# 5.1 dimensionar a entrada para esta máquina
python3 src/calibrar.py --alvo-minutos 4

# 5.2 gerar os dois corpora: o da medição, com o número que a calibração
#     indicou, e o da demonstração ao vivo, que precisa caber em segundos
python3 src/corpus.py --docs 15000 --saida dados/corpus
python3 src/corpus.py --docs 400   --saida dados/amostra

# 5.3 conferir que paralela == sequencial
python3 src/verificar.py --corpus dados/amostra --trabalhadores 8 --repeticoes 3

# 5.4 medir (demora: são várias execuções de minutos cada). O -u mantém o
#     progresso visível numa execução longa, e o tee guarda o registro.
mkdir -p resultados
python3 -u src/medir.py --corpus dados/corpus \
  --trabalhadores 1 2 4 8 --repeticoes 3 --com-thread | tee resultados/medicao.log

# Grava resultados/medicao.json e resultados/eventos.json — este último é o
# registro de fusões com carimbo lógico de Lamport, citado na seção C da ficha.

# 5.5 gerar o relatório com os números medidos
python3 src/gerar_relatorio.py

# 5.6 arquivar
aws s3 cp resultados/ s3://$BUCKET/resultados/ --recursive
aws s3 cp relatorio/relatorio.pdf s3://$BUCKET/
```

### Se o PDF não sair na instância

`gerar_relatorio.py` grava sempre o HTML e só depois tenta converter, pelo
primeiro conversor que encontrar: `wkhtmltopdf`, um navegador sem tela
(Chrome/Chromium/Edge) ou `weasyprint`. O Ubuntu 24.04 **não empacota mais o
wkhtmltopdf** e a imagem base não traz navegador, então na instância a conversão
pode simplesmente não acontecer. Nesse caso traga só os JSON para a máquina da
equipe e gere o PDF lá: o relatório depende da medição, não da máquina onde o
PDF é montado.

```bash
# na sua máquina, não na instância
mkdir -p resultados
scp -i ~/$NOME-chave.pem ubuntu@<IP-PÚBLICO>:projeto/resultados/'*.json' resultados/
python3 src/gerar_relatorio.py
```

Se preferir fechar tudo na instância:

```bash
sudo snap install chromium     # ~200 MiB; só compensa se for gerar lá mesmo
```

Deixe o serviço no ar para a apresentação:

```bash
sudo systemctl enable --now triagem
curl -s http://localhost:8000/api/saude
```

Do seu navegador: `http://<IP-PUBLICO>:8000`

---

## 6. Depois da apresentação

```bash
aws ec2 terminate-instances --region $REGIAO --instance-ids <ID>
```

---

## Se a conta for AWS Academy / Learner Lab

Contas de laboratório costumam limitar os tipos de instância. Se
`c6i.2xlarge` for recusado, use o maior tipo permitido e **ajuste
`src/configuracao.py`** (`tipo_instancia`, `vcpu`, `nucleos_fisicos`) antes de
gerar a ficha e o relatório. Ordem de preferência:

| Tipo | vCPU | Núcleos físicos | Observação |
|---|---|---|---|
| `c6i.2xlarge` | 8 | 4 | Melhor curva de speedup. |
| `c6i.xlarge` | 4 | 2 | Serve; o teto prático fica perto de 2. |
| `m5.large` / `t3.large` | 2 | 1 | Só dá para mostrar n = 2, e t3 é burstável — veja abaixo. |

Instância burstável (t2, t3) esgota créditos de CPU no meio de uma medição de
minutos e o desempenho cai. Se for a única opção, rode `--repeticoes 5`,
intercale as configurações e registre no relatório que o T(n) pode ter sido
afetado — é melhor declarar a limitação do que apresentar um número que não se
sustenta.
