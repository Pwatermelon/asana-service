from rdflib import Graph, Namespace, URIRef, Literal
from app import config

g = Graph()
g.parse(config.OWL_FILE_PATH, format="xml")

ASANA = Namespace("http://www.semanticweb.org/ontologies/asana#")

def load_asanas():
    asanas = []
    for asana in g.subjects(None, ASANA.AsanaName):
        name = g.value(asana, ASANA.AsanaName)
        photo = g.value(asana, ASANA.AsanaPhoto)
        source = g.value(asana, ASANA.AsanaSource)
        asanas.append({
            "name": str(name) if name else "",
            "photo": str(photo) if photo else "",
            "source": str(source) if source else ""
        })
    return asanas

def add_asana(name_ru: str, name_en: str, name_sanskrit: str, photo_base64: str, source: str):
    asana_uri = URIRef(f"http://www.semanticweb.org/ontologies/asana#{name_en}")
    g.add((asana_uri, ASANA.AsanaName, Literal(f"{name_ru}|{name_en}|{name_sanskrit}")))
    g.add((asana_uri, ASANA.AsanaPhoto, Literal(photo_base64)))
    g.add((asana_uri, ASANA.AsanaSource, Literal(source)))
    g.serialize(destination=config.OWL_FILE_PATH, format="xml")

# Новая функция: Загрузка списка источников
def load_sources():
    sources = set()
    for source in g.objects(None, ASANA.AsanaSource):
        sources.add(str(source))
    return list(sources)

# Новая функция: Добавление нового источника
def add_source(name: str):
    source_uri = URIRef(f"http://www.semanticweb.org/ontologies/asana#Source_{name}")
    if (source_uri, None, None) in g:
        return False  # Источник уже существует
    g.add((source_uri, ASANA.SourceName, Literal(name)))
    g.serialize(destination=config.OWL_FILE_PATH, format="xml")
    return True

# Новая функция: Загрузка списка названий асан
def load_asana_names():
    names = set()
    for asana in g.subjects(None, ASANA.AsanaName):
        name = g.value(asana, ASANA.AsanaName)
        if name:
            names.add(str(name))
    return list(names)

# Новая функция: Добавление нового названия асаны
def add_asana_name(name: str):
    asana_uri = URIRef(f"http://www.semanticweb.org/ontologies/asana#{name}")
    if (asana_uri, ASANA.AsanaName, None) in g:
        return False  # Название уже существует
    g.add((asana_uri, ASANA.AsanaName, Literal(name)))
    g.serialize(destination=config.OWL_FILE_PATH, format="xml")
    return True