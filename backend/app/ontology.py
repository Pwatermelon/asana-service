from rdflib import Graph, Namespace, URIRef, Literal, RDF
from app import config
from typing import Optional, Dict, Any
import uuid

g = Graph()
g.parse(config.OWL_FILE_PATH, format="xml")

ASANA = Namespace("http://www.semanticweb.org/platinum_watermelon/ontologies/Asana#")

def load_asanas():
    asanas = []
    for asana in g.subjects(RDF.type, ASANA.Asana):
        name_obj = g.value(asana, ASANA.hasName)
        photo_obj = g.value(asana, ASANA.hasPhoto)
        
        name_data = {
            "ru": str(g.value(name_obj, ASANA.nameInRussian)) if name_obj else "",
            "en": str(g.value(name_obj, ASANA.nameInEnglish)) if name_obj else "",
            "sanskrit": str(g.value(name_obj, ASANA.nameInSanskrit)) if name_obj else ""
        }
        
        source_obj = None
        if photo_obj:
            source_obj = g.value(photo_obj, ASANA.hasSource)
        
        source_data = {}
        if source_obj:
            source_data = {
                "title": str(g.value(source_obj, ASANA.sourseTitle)),
                "author": str(g.value(source_obj, ASANA.sourceAuthor)),
                "year": int(g.value(source_obj, ASANA.sourceYear))
            }
        
        photo_base64 = str(g.value(photo_obj, ASANA.base64Photo)) if photo_obj else ""
        
        asanas.append({
            "id": str(asana),
            "name": name_data,
            "source": source_data,
            "photo": photo_base64
        })
    return asanas

def add_asana(name_id: str, source_id: str, photo_base64: str):
    # Create new asana instance
    asana_uri = URIRef(f"{ASANA}asana_{uuid.uuid4()}")
    g.add((asana_uri, RDF.type, ASANA.Asana))
    
    # Link existing name
    name_uri = URIRef(name_id)
    g.add((asana_uri, ASANA.hasName, name_uri))
    
    # Create and link photo
    photo_uri = URIRef(f"{ASANA}photo_{uuid.uuid4()}")
    g.add((photo_uri, RDF.type, ASANA.AsanaPhoto))
    g.add((photo_uri, ASANA.base64Photo, Literal(photo_base64)))
    g.add((photo_uri, ASANA.hasSource, URIRef(source_id)))
    g.add((asana_uri, ASANA.hasPhoto, photo_uri))
    
    g.serialize(destination=config.OWL_FILE_PATH, format="xml")
    return str(asana_uri)

def load_sources():
    sources = []
    for source in g.subjects(RDF.type, ASANA.AsanaSource):
        sources.append({
            "id": str(source),
            "title": str(g.value(source, ASANA.sourseTitle)),
            "author": str(g.value(source, ASANA.sourceAuthor)),
            "year": int(g.value(source, ASANA.sourceYear))
        })
    return sources

def add_source(source_data: Dict[str, Any]) -> str:
    source_uri = URIRef(f"{ASANA}source_{uuid.uuid4()}")
    g.add((source_uri, RDF.type, ASANA.AsanaSource))
    g.add((source_uri, ASANA.sourseTitle, Literal(source_data["title"])))
    g.add((source_uri, ASANA.sourceAuthor, Literal(source_data["author"])))
    g.add((source_uri, ASANA.sourceYear, Literal(source_data["year"])))
    g.serialize(destination=config.OWL_FILE_PATH, format="xml")
    return str(source_uri)

def load_asana_names():
    names = []
    for name in g.subjects(RDF.type, ASANA.AsanaName):
        names.append({
            "id": str(name),
            "name_ru": str(g.value(name, ASANA.nameInRussian)),
            "name_en": str(g.value(name, ASANA.nameInEnglish)),
            "name_sanskrit": str(g.value(name, ASANA.nameInSanskrit))
        })
    return names

def add_asana_name(name_data: Dict[str, str]) -> str:
    name_uri = URIRef(f"{ASANA}name_{uuid.uuid4()}")
    g.add((name_uri, RDF.type, ASANA.AsanaName))
    g.add((name_uri, ASANA.nameInRussian, Literal(name_data["name_ru"])))
    g.add((name_uri, ASANA.nameInEnglish, Literal(name_data["name_en"])))
    g.add((name_uri, ASANA.nameInSanskrit, Literal(name_data["name_sanskrit"])))
    g.serialize(destination=config.OWL_FILE_PATH, format="xml")
    return str(name_uri)