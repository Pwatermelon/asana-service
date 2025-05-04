from rdflib import Graph, Namespace, URIRef, Literal, RDF
from app import config
from typing import Optional, Dict, Any
import uuid
import logging
import os
import base64

logger = logging.getLogger("asana_service.ontology")

ASANA = Namespace("http://www.semanticweb.org/platinum_watermelon/ontologies/Asana#")

def ensure_ontology_file_exists():
    """Создает файл онтологии, если он не существует"""
    try:
        if not os.path.exists(config.OWL_FILE_PATH):
            logger.info(f"Creating new ontology file at {config.OWL_FILE_PATH}")
            # Создаем базовый граф с основными классами
            g = Graph()
            g.bind("asana", ASANA)
            
            # Добавляем основные классы
            g.add((ASANA.Asana, RDF.type, RDF.Class))
            g.add((ASANA.AsanaName, RDF.type, RDF.Class))
            g.add((ASANA.AsanaSource, RDF.type, RDF.Class))
            g.add((ASANA.AsanaPhoto, RDF.type, RDF.Class))
            
            # Создаем директорию, если её нет
            os.makedirs(os.path.dirname(config.OWL_FILE_PATH), exist_ok=True)
            
            # Сохраняем граф
            g.serialize(destination=config.OWL_FILE_PATH, format="xml")
            logger.info("Successfully created new ontology file")
        return True
    except Exception as e:
        logger.error(f"Error ensuring ontology file exists: {str(e)}")
        raise

def get_graph():
    try:
        ensure_ontology_file_exists()
        logger.info(f"Loading RDF graph from {config.OWL_FILE_PATH}")
        g = Graph()
        g.parse(config.OWL_FILE_PATH, format="xml")
        logger.debug(f"Successfully loaded graph with {len(g)} triples")
        return g
    except Exception as e:
        logger.error(f"Failed to load RDF graph: {str(e)}")
        raise

def load_asanas():
    logger.info("Starting to load asanas from graph")
    g = get_graph()
    asanas = []
    all_asanas = list(g.subjects(RDF.type, ASANA.Asana))
    logger.info(f"Found {len(all_asanas)} asanas in graph")
    for asana in all_asanas:
        logger.debug(f"Processing asana: {asana}")
        name_obj = g.value(asana, ASANA.hasName)
        photo_objs = list(g.objects(asana, ASANA.hasPhoto))
        logger.debug(f"Name object: {name_obj}")
        logger.debug(f"Photo objects: {photo_objs}")
        name_data = {
            "ru": str(g.value(name_obj, ASANA.nameInRussian)) if name_obj else "",
            "en": str(g.value(name_obj, ASANA.nameInEnglish)) if name_obj else "",
            "sanskrit": str(g.value(name_obj, ASANA.nameInSanskrit)) if name_obj else ""
        }
        source_obj = None
        if photo_objs:
            source_obj = g.value(photo_objs[0], ASANA.hasSource)
            logger.debug(f"Source object: {source_obj}")
        source_data = {}
        if source_obj:
            source_data = {
                "title": str(g.value(source_obj, ASANA.sourseTitle)),
                "author": str(g.value(source_obj, ASANA.sourceAuthor)),
                "year": int(g.value(source_obj, ASANA.sourceYear))
            }
        photos_base64 = [str(g.value(photo, ASANA.base64Photo)) for photo in photo_objs if g.value(photo, ASANA.base64Photo)]
        logger.debug(f"Photos count: {len(photos_base64)}")
        asana_data = {
            "id": str(asana),
            "name": name_data,
            "source": source_data,
            "photos": photos_base64,
            "photo": photos_base64[0] if photos_base64 else ""
        }
        logger.debug(f"Adding asana with ID: {asana_data['id']}")
        asanas.append(asana_data)
    logger.info(f"Successfully loaded {len(asanas)} asanas")
    return asanas

def add_asana(name_id: str, source_id: str, photo_base64: str):
    try:
        logger.info("Starting to add new asana")
        logger.debug(f"Parameters: name_id={name_id}, source_id={source_id}, photo_base64=<truncated>")
        
        g = get_graph()
        
        # Create new asana instance
        asana_uri = URIRef(f"{ASANA}asana_{uuid.uuid4()}")
        logger.debug(f"Created asana URI: {asana_uri}")
        
        g.add((asana_uri, RDF.type, ASANA.Asana))
        logger.debug("Added asana type triple")
        
        # Link existing name
        name_uri = URIRef(name_id)
        g.add((asana_uri, ASANA.hasName, name_uri))
        logger.debug(f"Linked name: {name_uri}")
        
        # Create and link photo
        photo_uri = URIRef(f"{ASANA}photo_{uuid.uuid4()}")
        logger.debug(f"Created photo URI: {photo_uri}")
        
        g.add((photo_uri, RDF.type, ASANA.AsanaPhoto))
        g.add((photo_uri, ASANA.base64Photo, Literal(photo_base64)))
        g.add((photo_uri, ASANA.hasSource, URIRef(source_id)))
        g.add((asana_uri, ASANA.hasPhoto, photo_uri))
        logger.debug("Added photo and source triples")
        
        logger.info(f"Saving graph to {config.OWL_FILE_PATH}")
        g.serialize(destination=config.OWL_FILE_PATH, format="xml")
        logger.info("Successfully saved graph")
        
        return str(asana_uri)
    except Exception as e:
        logger.error(f"Error adding asana: {str(e)}", exc_info=True)
        raise

def load_sources():
    logger.info("Starting to load sources from graph")
    g = get_graph()
    sources = []
    for source in g.subjects(RDF.type, ASANA.AsanaSource):
        source_data = {
            "id": str(source),
            "title": str(g.value(source, ASANA.sourseTitle)),
            "author": str(g.value(source, ASANA.sourceAuthor)),
            "year": int(g.value(source, ASANA.sourceYear))
        }
        logger.debug(f"Loaded source: {source_data}")
        sources.append(source_data)
    logger.info(f"Successfully loaded {len(sources)} sources")
    return sources

def add_source(source_data: Dict[str, Any]) -> str:
    try:
        logger.info("Starting to add new source")
        logger.debug(f"Source data: {source_data}")
        
        g = get_graph()
        source_uri = URIRef(f"{ASANA}source_{uuid.uuid4()}")
        logger.debug(f"Created source URI: {source_uri}")
        
        g.add((source_uri, RDF.type, ASANA.AsanaSource))
        g.add((source_uri, ASANA.sourseTitle, Literal(source_data["title"])))
        g.add((source_uri, ASANA.sourceAuthor, Literal(source_data["author"])))
        g.add((source_uri, ASANA.sourceYear, Literal(source_data["year"])))
        logger.debug("Added source triples")
        
        logger.info(f"Saving graph to {config.OWL_FILE_PATH}")
        g.serialize(destination=config.OWL_FILE_PATH, format="xml")
        logger.info("Successfully saved graph")
        
        return str(source_uri)
    except Exception as e:
        logger.error(f"Error adding source: {str(e)}", exc_info=True)
        raise

def load_asana_names():
    logger.info("Starting to load asana names from graph")
    g = get_graph()
    names = []
    for name in g.subjects(RDF.type, ASANA.AsanaName):
        name_data = {
            "id": str(name),
            "name_ru": str(g.value(name, ASANA.nameInRussian)),
            "name_en": str(g.value(name, ASANA.nameInEnglish)),
            "name_sanskrit": str(g.value(name, ASANA.nameInSanskrit))
        }
        logger.debug(f"Loaded asana name: {name_data}")
        names.append(name_data)
    logger.info(f"Successfully loaded {len(names)} asana names")
    return names

def add_asana_name(name_data: Dict[str, str]) -> str:
    try:
        logger.info("Starting to add new asana name")
        logger.debug(f"Name data: {name_data}")
        
        g = get_graph()
        name_uri = URIRef(f"{ASANA}name_{uuid.uuid4()}")
        logger.debug(f"Created name URI: {name_uri}")
        
        g.add((name_uri, RDF.type, ASANA.AsanaName))
        g.add((name_uri, ASANA.nameInRussian, Literal(name_data["name_ru"])))
        g.add((name_uri, ASANA.nameInEnglish, Literal(name_data["name_en"])))
        g.add((name_uri, ASANA.nameInSanskrit, Literal(name_data["name_sanskrit"])))
        logger.debug("Added name triples")
        
        logger.info(f"Saving graph to {config.OWL_FILE_PATH}")
        g.serialize(destination=config.OWL_FILE_PATH, format="xml")
        logger.info("Successfully saved graph")
        
        return str(name_uri)
    except Exception as e:
        logger.error(f"Error adding asana name: {str(e)}", exc_info=True)
        raise

def delete_any_by_uri(uri: str) -> bool:
    try:
        g = get_graph()
        obj_uri = URIRef(uri)
        found = False
        # Пробуем точное совпадение
        if (obj_uri, None, None) in g or (None, None, obj_uri) in g:
            found = True
            g.remove((obj_uri, None, None))
            g.remove((None, None, obj_uri))
        else:
            # Если не найдено — ищем по окончанию (UUID)
            suffix = uri.split("_")[-1]
            candidates = [s for s in g.subjects() if str(s).endswith(suffix)]
            for cand in candidates:
                g.remove((cand, None, None))
                g.remove((None, None, cand))
                found = True
            # Если всё равно не найдено — ищем по подстроке UUID
            if not found:
                uuid_part = suffix
                candidates = [s for s in g.subjects() if uuid_part in str(s)]
                for cand in candidates:
                    g.remove((cand, None, None))
                    g.remove((None, None, cand))
                    found = True
        if not found:
            print(f'НЕ НАЙДЕН В ГРАФЕ: {uri}')
            return False
        g.serialize(destination=config.OWL_FILE_PATH, format="xml")
        print(f'УДАЛЁН(Ы): {uri}')
        return True
    except Exception as e:
        print(f'ОШИБКА ПРИ УДАЛЕНИИ: {e}')
        raise

def delete_source_from_ontology(source_id: str) -> bool:
    return delete_any_by_uri(source_id)

def delete_asana_name_from_ontology(name_id: str) -> bool:
    return delete_any_by_uri(name_id)

def delete_asana_from_ontology(asana_id: str) -> bool:
    try:
        g = get_graph()
        ASANA = Namespace("http://www.semanticweb.org/platinum_watermelon/ontologies/Asana#")
        asana_uri = URIRef(asana_id)
        # Если не найдено точное совпадение — ищем по UUID
        if (asana_uri, None, None) not in g:
            suffix = asana_id.split("_")[-1]
            candidates = [s for s in g.subjects(RDF.type, ASANA.Asana) if str(s).endswith(suffix)]
            if not candidates:
                print(f'Асана не найдена: {asana_id}')
                return False
            asana_uri = candidates[0]
        # Найти все связанные фото
        photo_uris = list(g.objects(asana_uri, ASANA.hasPhoto))
        for photo_uri in photo_uris:
            # Удалить все триплеты, где фигурирует фото
            g.remove((photo_uri, None, None))
            g.remove((None, None, photo_uri))
        # Удалить все триплеты, где фигурирует асана
        g.remove((asana_uri, None, None))
        g.remove((None, None, asana_uri))
        g.serialize(destination=config.OWL_FILE_PATH, format="xml")
        print(f'Удалена асана и связанные фото: {asana_id}')
        return True
    except Exception as e:
        print(f'ОШИБКА ПРИ УДАЛЕНИИ АСАНЫ: {e}')
        raise

def add_photo_to_asana(asana_id: str, photo_bytes: bytes):
    try:
        g = get_graph()
        asana_uri = URIRef(asana_id)
        # Если не найдено точное совпадение — ищем по UUID
        if (asana_uri, None, None) not in g:
            suffix = asana_id.split("_")[-1]
            candidates = [s for s in g.subjects(RDF.type, ASANA.Asana) if str(s).endswith(suffix)]
            if not candidates:
                raise Exception("Асана не найдена")
            asana_uri = candidates[0]
        photo_base64 = base64.b64encode(photo_bytes).decode()
        photo_uri = URIRef(f"{ASANA}photo_{uuid.uuid4()}")
        g.add((photo_uri, RDF.type, ASANA.AsanaPhoto))
        g.add((photo_uri, ASANA.base64Photo, Literal(photo_base64)))
        g.add((asana_uri, ASANA.hasPhoto, photo_uri))
        g.serialize(destination=config.OWL_FILE_PATH, format="xml")
    except Exception as e:
        raise