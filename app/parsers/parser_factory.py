from .law_parser import LawParser
from .admrul_parser import AdmRulParser


class ParserFactory:

    @staticmethod
    # def get_parser(data: dict):
    def get_parser(target):
        print("get_parser called with data keys:", target)
        
        # target = data.get("target") or data.get("type")

        if target == "law":
            return LawParser()

        elif target == "admRul":
            return AdmRulParser()

        else:
            raise ValueError(f"지원하지 않는 parser 타입: {target}")