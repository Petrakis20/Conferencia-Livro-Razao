"""
Módulo de validação de empresas por período.
Lê o arquivo params.txt e valida se a empresa pode ser processada no período selecionado.
"""

from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import re


def parse_params_file(filepath: str = "Alterdata_BI/params.txt") -> Dict:
    """
    Lê o arquivo params.txt e extrai configurações e blocos de dias.

    Returns:
        Dict com estrutura:
        {
            'start': str,  # Data inicial do arquivo
            'end': str,    # Data final do arquivo
            'municipio': str,
            'out': str,
            'day_blocks': {
                12: ['01523', '01535', ...],
                15: ['01552', ...],
                ...
            }
        }
    """
    result = {
        'start': None,
        'end': None,
        'municipio': None,
        'out': None,
        'day_blocks': {}
    }

    filepath = Path(filepath)
    if not filepath.exists():
        return result

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        current_day = None
        in_empresas_block = False

        for line in lines:
            line = line.strip()

            # Ignora comentários e linhas vazias
            if not line or line.startswith('#') or line.startswith('//'):
                continue

            # Detecta bloco [DIA X]
            day_match = re.match(r'^\[?\s*DIA\s+(\d{1,2})\s*\]?:?$', line, re.IGNORECASE)
            if day_match:
                current_day = int(day_match.group(1))
                result['day_blocks'][current_day] = []
                in_empresas_block = False
                continue

            # Detecta configurações globais
            if line.startswith('--'):
                parts = line.split(maxsplit=1)
                key = parts[0].lower()
                val = parts[1].strip() if len(parts) > 1 else ''

                if key == '--start':
                    result['start'] = val
                elif key == '--end':
                    result['end'] = val
                elif key == '--municipio':
                    result['municipio'] = val
                elif key == '--out':
                    result['out'] = val
                elif key == '--empresas':
                    in_empresas_block = True

                continue

            # Lê códigos de empresa
            if in_empresas_block and current_day is not None:
                # Remove ponto e vírgula e espaços
                code = line.replace(';', '').strip()
                if code and code.isdigit():
                    # Padroniza para 5 dígitos
                    code5 = code.zfill(5)
                    result['day_blocks'][current_day].append(code5)

        return result

    except Exception as e:
        print(f"Erro ao ler params.txt: {e}")
        return result


def get_period_from_params(params: Dict) -> Optional[Tuple[datetime, datetime]]:
    """
    Extrai o período (start, end) do params.txt.

    Returns:
        Tupla (start_date, end_date) ou None se não encontrado
    """
    try:
        if not params.get('start') or not params.get('end'):
            return None

        start = datetime.strptime(params['start'], '%Y-%m-%d')
        end = datetime.strptime(params['end'], '%Y-%m-%d')
        return start, end
    except:
        return None


def is_same_month_year(date1: datetime, date2: datetime) -> bool:
    """Verifica se duas datas estão no mesmo mês e ano."""
    return date1.year == date2.year and date1.month == date2.month


def validate_company_for_period(
    company_code: str,
    selected_start: datetime,
    selected_end: datetime,
    params: Dict
) -> Tuple[bool, str, Optional[int]]:
    """
    Valida se a empresa pode ser processada no período selecionado.

    Regras:
    1. Se o período selecionado NÃO coincide com o período do params.txt:
       - Liberado para qualquer empresa
    2. Se o período selecionado coincide com o período do params.txt:
       - Verifica se a empresa está em algum bloco [DIA X]
       - Retorna o dia do bloco encontrado

    Args:
        company_code: Código da empresa (será padronizado para 5 dígitos)
        selected_start: Data inicial selecionada
        selected_end: Data final selecionada
        params: Dicionário retornado por parse_params_file()

    Returns:
        Tupla (is_valid, message, day_block)
        - is_valid: True se pode processar
        - message: Mensagem explicativa
        - day_block: Dia do bloco se encontrado, None caso contrário
    """
    # Padroniza código
    code5 = str(company_code).zfill(5)

    # Obtém período do params.txt
    params_period = get_period_from_params(params)

    # Se não tem período no params.txt, libera
    if not params_period:
        return True, "Período não configurado no params.txt - processamento liberado", None

    params_start, params_end = params_period

    # Verifica se o período selecionado coincide com o do params.txt
    # Considera "mesmo período" se start e end são exatamente iguais
    is_same_period = (
        selected_start.date() == params_start.date() and
        selected_end.date() == params_end.date()
    )

    # Se NÃO é o mesmo período, libera
    if not is_same_period:
        return True, f"Período diferente do configurado ({params_start.strftime('%Y-%m-%d')} a {params_end.strftime('%Y-%m-%d')}) - processamento liberado", None

    # É o mesmo período - verifica blocos
    day_blocks = params.get('day_blocks', {})

    if not day_blocks:
        return True, "Nenhum bloco de dia configurado - processamento liberado", None

    # Procura a empresa em algum bloco
    found_in_day = None
    for day, companies in day_blocks.items():
        if code5 in companies:
            found_in_day = day
            break

    if found_in_day is not None:
        return True, f"Empresa autorizada para processamento no DIA {found_in_day}", found_in_day
    else:
        # Lista os dias disponíveis
        available_days = sorted(day_blocks.keys())
        return False, f"Empresa NÃO encontrada nos blocos configurados. Dias disponíveis: {available_days}. Altere o período ou verifique o código da empresa.", None


def get_companies_for_day(day: int, params: Dict) -> List[str]:
    """
    Retorna lista de empresas configuradas para um dia específico.

    Args:
        day: Dia do mês (1-31)
        params: Dicionário retornado por parse_params_file()

    Returns:
        Lista de códigos de empresa (5 dígitos)
    """
    return params.get('day_blocks', {}).get(day, [])


def get_all_configured_companies(params: Dict) -> List[str]:
    """
    Retorna lista de todas as empresas configuradas (todos os blocos).

    Args:
        params: Dicionário retornado por parse_params_file()

    Returns:
        Lista de códigos de empresa únicos (5 dígitos)
    """
    all_companies = set()
    for companies in params.get('day_blocks', {}).values():
        all_companies.update(companies)
    return sorted(list(all_companies))


def format_company_info(params: Dict) -> str:
    """
    Formata informações sobre empresas configuradas para exibição.

    Args:
        params: Dicionário retornado por parse_params_file()

    Returns:
        String formatada com informações
    """
    lines = []

    period = get_period_from_params(params)
    if period:
        start, end = period
        lines.append(f"**Período configurado:** {start.strftime('%d/%m/%Y')} a {end.strftime('%d/%m/%Y')}")
    else:
        lines.append("**Período:** Não configurado")

    lines.append("")
    lines.append("**Blocos de empresas por dia:**")

    day_blocks = params.get('day_blocks', {})
    if not day_blocks:
        lines.append("- Nenhum bloco configurado")
    else:
        for day in sorted(day_blocks.keys()):
            companies = day_blocks[day]
            lines.append(f"- **DIA {day}:** {len(companies)} empresas")

    total_companies = len(get_all_configured_companies(params))
    lines.append("")
    lines.append(f"**Total de empresas únicas:** {total_companies}")

    return "\n".join(lines)
