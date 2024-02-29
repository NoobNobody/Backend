import re

def sanitize_salary_range(salary_range):
    if salary_range is None:
        return None
    if salary_range.startswith('Mniejsze niż '):
        return '<' + salary_range.replace('Mniejsze niż ', '').replace('zł', '').strip()
    elif salary_range.startswith('Większe niż '):
        return '>' + salary_range.replace('Większe niż ', '').replace('zł', '').strip()
    else:
        return salary_range.replace('zł', '').strip()

def extract_earnings_data(earnings_str):
    if not earnings_str:
        return None, None, None

    earnings_str = re.sub(r'\s+|\u00A0', '', earnings_str)
    earnings_str = earnings_str.replace('–', '-').replace('—', '-')

    matches = re.findall(r'(\d+)-(\d+)zł(/(godz\.|mies\.))?', earnings_str)
    if not matches:
        return None, None, None

    min_earnings, max_earnings, _, earnings_type = matches[0]
    min_earnings, max_earnings = int(min_earnings), int(max_earnings)
    earnings_type = 'hourly' if 'godz.' in earnings_str else 'monthly'

    return min_earnings, max_earnings, earnings_type