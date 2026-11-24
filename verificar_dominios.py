import csv
import socket
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
from rich.console import Console
from rich.table import Table

console = Console()


def extrair_host_e_url(linha: str) -> tuple[str, str]:
    bruto = linha.strip()
    if not bruto.startswith(("http://", "https://")):
        url = f"https://{bruto}"
    else:
        url = bruto

    parsed = urlparse(url)
    host = parsed.hostname or bruto
    return host, url


def resolver_ip(host: str) -> tuple[str | None, str | None]:
    try:
        ip = socket.gethostbyname(host)
        return ip, None
    except socket.gaierror as exc:
        return None, f"DNS/IP: {exc}"


def obter_status_http(url: str, timeout: float = 6.0) -> tuple[str | None, str | None]:
    headers = {"User-Agent": "Mozilla/5.0 (DomainChecker/1.0)"}
    try:
        resposta = requests.get(url, timeout=timeout, headers=headers, allow_redirects=True)
        return str(resposta.status_code), None
    except requests.exceptions.SSLError:
        if url.startswith("https://"):
            url_http = "http://" + url[len("https://"):]
            try:
                resposta = requests.get(url_http, timeout=timeout, headers=headers, allow_redirects=True)
                return str(resposta.status_code), None
            except requests.RequestException as exc_http:
                return None, f"HTTP: {exc_http.__class__.__name__}"
        return None, "Erro SSL"
    except requests.exceptions.Timeout:
        return None, "Timeout (tempo esgotado)"
    except requests.RequestException as exc:
        return None, f"HTTP: {exc.__class__.__name__}"


def salvar_csv(linhas: list[dict[str, str]], caminho_csv: Path) -> None:
    campos = ["dominio", "ip", "status_http", "erro", "consultado_em"]
    with caminho_csv.open("w", newline="", encoding="utf-8-sig") as arquivo_csv:
        escritor = csv.DictWriter(arquivo_csv, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows(linhas)


def main() -> None:
    arquivo_dominios = Path("dominios.txt")
    arquivo_csv = Path("resultados.csv")

    if not arquivo_dominios.exists():
        console.print("[bold red]Erro:[/bold red] Arquivo [cyan]dominios.txt[/cyan] não encontrado.")
        return

    dominios = [
        linha.strip()
        for linha in arquivo_dominios.read_text(encoding="utf-8").splitlines()
        if linha.strip() and not linha.strip().startswith("#")
    ]

    if not dominios:
        console.print("[yellow]Nenhum domínio encontrado em dominios.txt.[/yellow]")
        return

    tabela = Table(title="Verificação de Domínios", show_lines=True)
    tabela.add_column("Domínio", style="cyan", no_wrap=True)
    tabela.add_column("IP", style="green")
    tabela.add_column("Status HTTP", justify="center")
    tabela.add_column("Observações / Erro", style="red")

    resultados_csv: list[dict[str, str]] = []
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")

    with console.status("[bold blue]Consultando domínios...[/bold blue]"):
        for entrada in dominios:
            host, url = extrair_host_e_url(entrada)
            ip, erro_ip = resolver_ip(host)

            if erro_ip:
                tabela.add_row(entrada, "-", "[red]ERRO[/red]", erro_ip)
                resultados_csv.append({
                    "dominio": entrada,
                    "ip": "",
                    "status_http": "ERRO",
                    "erro": erro_ip,
                    "consultado_em": timestamp,
                })
                continue

            status, erro_http = obter_status_http(url)
            if erro_http:
                tabela.add_row(entrada, ip or "-", "[red]ERRO[/red]", erro_http)
                resultados_csv.append({
                    "dominio": entrada,
                    "ip": ip or "",
                    "status_http": "ERRO",
                    "erro": erro_http,
                    "consultado_em": timestamp,
                })
            else:
                cor_status = "green" if status and status.startswith("2") else "yellow"
                tabela.add_row(
                    entrada,
                    ip or "-",
                    f"[bold {cor_status}]{status}[/bold {cor_status}]",
                    "-",
                )
                resultados_csv.append({
                    "dominio": entrada,
                    "ip": ip or "",
                    "status_http": status or "",
                    "erro": "",
                    "consultado_em": timestamp,
                })

    console.print(tabela)
    salvar_csv(resultados_csv, arquivo_csv)
    console.print(f"[bold green]CSV salvo em:[/bold green] [cyan]{arquivo_csv}[/cyan]")


if __name__ == "__main__":
    main()