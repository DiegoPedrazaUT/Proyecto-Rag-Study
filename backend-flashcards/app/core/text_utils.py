def normalize_answer(text: str) -> str:
    """Normaliza una respuesta para comparación tolerante.

    Aplica: quitar espacios sobrantes al inicio/fin y pasar a minúsculas.
    NO quita acentos: los acentos se consideran significativos.

    Se usa tanto para validar que la respuesta sea una opción válida como
    para compararla con la respuesta correcta, de forma consistente.
    """
    return text.strip().lower()