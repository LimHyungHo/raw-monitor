# app/domain/models.py

class Law:
    def __init__(self, law_id, name, articles, addenda):
        self.law_id = law_id
        self.name = name
        self.articles = articles
        self.addenda = addenda


class Article:
    def __init__(self, number, title, paragraphs):
        self.number = number
        self.title = title
        self.paragraphs = paragraphs


class Paragraph:
    def __init__(self, number, content, items):
        self.number = number
        self.content = content
        self.items = items


class Item:
    def __init__(self, number, content, sub_items):
        self.number = number
        self.content = content
        self.sub_items = sub_items


class SubItem:
    def __init__(self, number, content):
        self.number = number
        self.content = content