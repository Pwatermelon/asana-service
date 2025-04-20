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
