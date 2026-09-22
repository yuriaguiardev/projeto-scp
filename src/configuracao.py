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
    "regiao": "us-east-1 (Norte da Virgínia)",
    "zona": "us-east-1c",
    "tipo_instancia": "c5.large",   # 2 vCPU / 4 GiB, sem creditos de CPU
    "vcpu": 2,
    "nucleos_fisicos": 1,
    "disco_gib": 30,
    # Nenhum bucket foi criado: a saida do projeto sao dois JSON de poucos KiB,
    # versionados no repositorio. None faz a ficha e o relatorio descreverem
    # esse arranjo em vez de prometerem um S3 que nao existe.
    "bucket": None,
    "origem_admin": "177.180.12.98/32",
    "porta_servico": 8000,
    "documentos_previstos": 8000,    # dimensionado por calibrar.py na instancia
    "alvo_minutos": 3,               # tempo alvo da execucao sequencial
    # Por que esta regiao. Na conta da equipe (AWS Academy Learner Lab) a
    # regiao nao e escolha: o laboratorio restringe a operacao a us-east-1.
    "motivo_regiao": (
        "A regi&atilde;o n&atilde;o foi uma escolha de projeto: a conta "
        "dispon&iacute;vel &eacute; um AWS Academy Learner Lab, que restringe a "
        "opera&ccedil;&atilde;o a us-east-1. O experimento n&atilde;o depende "
        "disso &mdash; T(1) e T(n) s&atilde;o medidos na mesma inst&acirc;ncia, "
        "e a lat&ecirc;ncia at&eacute; a equipe n&atilde;o entra no tempo "
        "medido, porque o corpus &eacute; lido do disco local."),
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
    # bucket = None e uma decisao registrada (nao se usa S3), nao uma pendencia
    for chave, rotulo in (("bucket", "nome do bucket S3"),
                          ("origem_admin", "IP publico da equipe (origem da porta 22)")):
        valor = INFRA[chave]
        if valor is not None and "PREENCHER" in str(valor):
            faltando.append(rotulo)
    return faltando
