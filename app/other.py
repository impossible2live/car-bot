from decimal import Decimal

def _format_price(value):
    if value is None:
        return None

    try:
        if isinstance(value, (Decimal, float)):
            int_value = int(float(value))
            return f"{int_value:,}".replace(",", " ")

        if isinstance(value, str) and ('E' in value or 'e' in value):
            float_value = float(value)
            int_value = int(float_value)
            return f"{int_value:,}".replace(",", " ")

        try:
            int_value = int(float(value))
            return f"{int_value:,}".replace(",", " ")
        except:
            return str(value)

    except (ValueError, TypeError):
        return str(value)