class BaseParser:
    def __init__(self):
        pass
            
    def parse(self, data: dict) -> str:
        raise NotImplementedError("Parser must implement parse()")