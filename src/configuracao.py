"""
configuracao.py - Dados da equipe e da infraestrutura, num lugar so.

O relatorio e a ficha sao gerados a partir daqui. Editar este arquivo e gerar de
novo e mais seguro do que editar dois PDFs.

Os valores deste arquivo sao texto que vai impresso na ficha e no relatorio,
entao nomes proprios ficam acentuados como se escrevem. Comentarios e docstrings
do projeto seguem sem acento, como no resto do codigo.

ATENCAO: os campos marcados com PREENCHER precisam do dado real antes da entrega.
"""

DISCIPLINA = {
    "codigo": "070080",
    "nome": "Sistemas Distribuídos e Paralelos",
    "professor": "Fábio Rocha de Araújo",
    "oficina": "08/09",
    "entrega": "22/09",
}

EQUIPE = {
    "turma": "CC6MA",
    "repositorio": "https://github.com/yuriaguiardev/projeto-scp",
    "integrantes": [
        {"nome": "Yuri Aguiar", "matricula": "24070309"},
        {"nome": "Pedro Paulo", "matricula": "24070313"},
        {"nome": "João Rath", "matricula": "24070338"},
        {"nome": "Fábio Gabriel", "matricula": "21070209"},
    ],
}

INFRA = {
    "provedor": "AWS EC2",
    "regiao": "sa-east-1 (São Paulo)",
    "zona": "sa-east-1a",
    "tipo_instancia": "c6i.2xlarge",   # 8 vCPU / 16 GiB, sem creditos de CPU
    "vcpu": 8,
    "nucleos_fisicos": 4,
    "disco_gib": 30,
    "bucket": "sdp-etapa1-equipe (PREENCHER)",
    "origem_admin": "PREENCHER: <IP-publico-da-equipe>/32",
    "porta_servico": 8000,
    "documentos_previstos": 15000,
    "sla_uma_zona": "99,5 % (216 min/mes)",
    "sla_multi_zona": "99,99 % (4,3 min/mes)",
}


def pendencias():
    """
    Lista os campos que ainda estao com o marcador PREENCHER.

    A ficha e o relatorio chamam esta funcao para decidir se exibem o aviso de
    pendencia e quais campos citar. Assim o aviso desaparece sozinho quando o
    dado real entra, em vez de depender de alguem lembrar de apagar o texto.
    """
    faltando = []
    if "PREENCHER" in EQUIPE["repositorio"]:
        faltando.append("URL do repositorio")
    sem_matricula = [i["nome"] for i in EQUIPE["integrantes"]
                     if not i.get("matricula") or "PREENCHER" in i["matricula"]]
    if sem_matricula:
        faltando.append("matricula de " + ", ".join(sem_matricula))
    for chave, rotulo in (("bucket", "nome do bucket S3"),
                          ("origem_admin", "IP publico da equipe (origem da porta 22)")):
        if "PREENCHER" in str(INFRA[chave]):
            faltando.append(rotulo)
    return faltando
