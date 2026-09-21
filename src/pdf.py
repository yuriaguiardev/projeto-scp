"""
pdf.py - Converte HTML em PDF usando o primeiro conversor disponivel.

Existe porque o wkhtmltopdf foi descontinuado pelo projeto de origem e deixou
de ser empacotado nas distribuicoes recentes - entre elas o Ubuntu 24.04, que e
a imagem usada na instancia. Sem alternativa, gerar_relatorio.py e
gerar_ficha.py parariam no HTML e a entrega ficaria sem os dois PDFs.

Ordem de tentativa:
    1. wkhtmltopdf            se ainda estiver instalado
    2. navegador sem tela     Chrome / Chromium / Edge, em --headless
    3. weasyprint             se o pacote Python estiver presente

Nenhum deles e obrigatorio: o HTML sempre e gravado, e o navegador do usuario
imprime para PDF. Mas com qualquer um dos tres a geracao fica automatica.
"""

import os
import shutil
import subprocess

# Navegadores, por nome no PATH e por caminho fixo (macOS nao poe no PATH).
NAVEGADORES = (
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
    "microsoft-edge", "brave-browser",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
)


def _achar_navegador():
    for candidato in NAVEGADORES:
        if os.path.sep in candidato:
            if os.path.exists(candidato):
                return candidato
        else:
            caminho = shutil.which(candidato)
            if caminho:
                return caminho
    return None


def _por_wkhtmltopdf(html, pdf):
    if not shutil.which("wkhtmltopdf"):
        return None
    subprocess.run(["wkhtmltopdf", "-q", "--encoding", "utf-8",
                    "--enable-local-file-access", html, pdf], check=True)
    return "wkhtmltopdf"


def _por_navegador(html, pdf):
    navegador = _achar_navegador()
    if not navegador:
        return None
    # --no-pdf-header-footer tira o cabecalho com URL e data que o Chrome
    # imprime por padrao; o @page do CSS define as margens.
    subprocess.run(
        [navegador, "--headless", "--disable-gpu", "--no-sandbox",
         "--no-pdf-header-footer", f"--print-to-pdf={os.path.abspath(pdf)}",
         "file://" + os.path.abspath(html)],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not os.path.exists(pdf):
        raise RuntimeError(f"{os.path.basename(navegador)} nao gravou {pdf}")
    return os.path.basename(navegador)


def _por_weasyprint(html, pdf):
    try:
        from weasyprint import HTML
    except Exception:
        return None
    HTML(filename=html).write_pdf(pdf)
    return "weasyprint"


def converter(html, pdf):
    """Gera `pdf` a partir de `html`. Devolve o nome do conversor usado, ou
    None se nenhum estiver disponivel."""
    for tentativa in (_por_wkhtmltopdf, _por_navegador, _por_weasyprint):
        try:
            usado = tentativa(html, pdf)
        except Exception as erro:
            print(f"aviso: {tentativa.__name__} falhou ({erro}); tentando o proximo")
            continue
        if usado:
            return usado
    return None
