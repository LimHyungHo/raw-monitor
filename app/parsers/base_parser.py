class BaseParser:

    STRUCT_KEYS = ["편", "장", "절", "조문", "항", "호", "목"]

    def normalize_list(self, value):
        if not value:
            return []
        return value if isinstance(value, list) else [value]