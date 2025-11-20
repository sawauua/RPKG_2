from rdflib import Graph, Namespace, RDF, URIRef, Literal, RDFS, OWL
from pathlib import Path
import os
import csv
import json

import re
import time
import requests
from itertools import count

target_dir = Path("C:/Users/FTS Demo/Documents/rp_kg_project/RPKG_2")
os.chdir(target_dir)

#prefixes to namespace uri
RPO  = Namespace("http://www.semanticweb.org/ftsdemo/ontologies/2025/5/rpo#")
RDF = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
PRO  = Namespace("http://purl.org/spar/pro/")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
    
#!geo location to everything


#add paper
def add_paper(graph: Graph, paper_id: int, meta: dict):
    #add general peper triples
    #create uri for the paper
    paper_uri = URIRef(f"{RPO}paper/{paper_id}")

    #base type
    graph.add((paper_uri, RDF.type, RPO["AcademicWork"]))
    print(f"added {paper_id} as AcademicWork")

    #get specific type
    oa_type_map = {
        "journal-article": "JournalArticle",
        "proceedings-article": "ProceedingsArticle",
        "article": "Article",
        "book": "Book",
        "book-chapter": "Chapter",
    }
    
    oa_type_raw = (meta["openalex"] or {}).get("type_crossref")
    if oa_type_raw:
        class_local = oa_type_map.get(oa_type_raw, "AcademicWork")
        graph.add((paper_uri, RDF.type, RPO[class_local]))

    #basic metadata
    doi = (
        (meta["openalex"] or {}).get("doi")
        or (meta["crossref"] or {}).get("DOI")
    )
    if doi:
        graph.add((paper_uri, RPO.doi, Literal(doi)))
        graph.add((RPO.doi, RDF.type, OWL.DatatypeProperty))
        print(f"     doi: {doi}")

    if meta["openalex"]:
        oa_id = meta["openalex"].get("id")
        if oa_id:
            graph.add((paper_uri, RPO.openalex_id, Literal(oa_id)))
            graph.add((RPO.openalex_id, RDF.type, OWL.DatatypeProperty))
            print(f"     oa id {oa_id}")
        
        year = (meta["openalex"].get("publication_year"))
        if year:
            graph.add((paper_uri, RPO.published_in_year, Literal(year)))
            graph.add((RPO.published_in_year, RDF.type, OWL.DatatypeProperty))
            print(f"     year {year}")

        cites = meta["openalex"].get("cited_by_count")
        if cites is not None:
            graph.add((paper_uri, RPO.nr_of_citations, Literal(cites)))
            graph.add((RPO.nr_of_citations, RDF.type, OWL.DatatypeProperty))
            print(f"     cit count {cites}")

        lang = meta["openalex"].get("language")
        if lang:
            graph.add((paper_uri, RPO.language, Literal(lang)))
            graph.add((RPO.language, RDF.type, OWL.DatatypeProperty))
            print(f"     lang {lang}")
        #print(f"    added {paper_id} basic metadata")
        
    elif meta["crossref"]:
        pass
        
    graph.add((paper_uri, RPO.has_title, Literal(meta["title"])))

# ---------------------------------------------
    
#get authors
def get_authors(graph: Graph, paper_id: int, meta: dict):
    paper_uri = URIRef(f"{RPO}paper/{paper_id}")
    oa = meta["openalex"]
    if not oa:
        return
    
    author_uris: list[URIRef] = []

    for auth in oa.get("authorships", []):
        auth_id = auth["author"]["id"]
        full_name = auth["author"]["display_name"]
        auth_uri = URIRef(f"{RPO}{makeName(full_name)}")
        if auth_id:
            graph.add((auth_uri, RPO.has_id, RPO[auth_id]))
            graph.add((RPO.has_id, RDF.type, OWL.DatatypeProperty))
        graph.add((auth_uri, RDF.type, RPO.Author))
        graph.add((auth_uri, FOAF.name, Literal(full_name)))
        #print(f"    added {full_name} as Author")
        
        inst = (auth.get("institutions") or [{}])[0]
        aff_name = inst.get("display_name")
        if aff_name:
            affi_name = makeName(aff_name)
            graph.add((auth_uri, RPO.affiliated_with, RPO[affi_name]))
            graph.add((RPO.affiliated_with, RDF.type, OWL.ObjectProperty))
            
            info = extract_affiliations_from_metadata(auth)
            
            more = detailed_org(graph, info.get("institution"))
            if more.get("key_person") is not None:
                graph.add((RPO[affi_name], RPO.key_person, RPO[makeName(more.get("key_person"))]))
                graph.add((RPO.key_person, RDF.type, OWL.ObjectProperty))
            
        graph.add((auth_uri, RPO.wrote, paper_uri))
        graph.add((RPO.wrote, RDF.type, OWL.ObjectProperty))
        graph.add((paper_uri, RPO.written_by, auth_uri))
        graph.add((RPO.written_by, RDF.type, OWL.ObjectProperty))
        
        author_uris.append(auth_uri)
        
    for i, a in enumerate(author_uris):
        for b in author_uris[i + 1 :]:
            graph.add((a, RPO.works_with, b))
            graph.add((RPO.works_with, RDF.type, OWL.ObjectProperty))
            graph.add((b, RPO.works_with, a))
    
    license_url = (
        (oa.get("open_access") or {}).get("license")
        or (
            (meta.get("crossref") or {}).get("license") and
            meta["crossref"]["license"][0].get("URL")
        )
    )
    if license_url:
        graph.add((paper_uri, RPO.has_license, Literal(license_url)))
        graph.add((RPO.has_licene, RDF.type, OWL.DatatypeProperty))
    if oa.get("open_access").get("is_oa"):
        graph.add((paper_uri, RPO.is_open_access, Literal("True")))
        graph.add((RPO.is_open_access, RDF.type, OWL.DatatypeProperty))
        
    return author_uris

def extract_affiliations_from_metadata(meta_auth):
    
    affiliations = {}
    keywords = [
    "institute", "Institute", "society", "Society", "research", "Research",
    "Organization", "Organisation", "University", "university", "College", "college"
]
    
    raw_affils = meta_auth.get("raw_affiliation_strings", [])
    for raw in raw_affils:
        parts = [part.strip() for part in raw.split(",")]
        if len(parts) >= 3 and (len(xp) >2 for xp in parts):
            country = None
            city = None
            # Assume last is country, second last is city, rest is institution
            if not any(keyword in parts[-1] for keyword in keywords):
                country = parts[-1]
            if not any(keyword in parts[-2] for keyword in keywords):
                city = parts[-2]
            institution = ", ".join(parts[:-2])
        elif len(parts) == 2 and (len(xp) >2 for xp in parts):
            if not any(keyword in parts[-1] for keyword in keywords):
                institution, city = parts
            else:
                institution = ", ".join(parts)
                city = None
            country = None
        elif len(parts) == 1:
            institution = parts[0]
            city = None
            country = None
        else:
            institution = city = country = None
            
        affiliations = {
            "institution": institution,
            "city": city,
            "country": country,
            "id": meta_auth.get("institutions_id")
        }
    
        return affiliations

# ----------------- helper functions --------------------------

def _slugify(text: str) -> str:
    return _slug_rx.sub("-", text.strip().lower()).strip("-") or "unk"

_slug_rx = re.compile(r"[^A-Za-z0-9]+")

_CLASS_KEYWORDS = {
    "university":           "University",
    "college":              "University",
    "ngo":                  "NGO",
    "non‑profit":           "NGO",
    "foundation":           "NGO",
    "political party":      "PoliticalOrganisation",
    "political organisation":"PoliticalOrganisation",
    "government":           "StateInstitution",
    "ministry":             "StateInstitution",
    "publisher":            "PublishingCompany",
    "publishing":           "PublishingCompany",
    "journal":              "PublishingCompany",
    "military":             "MilitaryOrganisation",
    "army":                 "MilitaryOrganisation",
    "navy":                 "MilitaryOrganisation",
    "air force":            "MilitaryOrganisation",
    "company":              "Company",
    "corporation":          "Company",
    "inc":                  "Company",
    "ltd":                  "Company",
    "international organisation": "InternationalOrganisation",
    "international organization": "InternationalOrganisation",
}

def _classify_from_text(text):
    t = text.lower()
    for kw, cls in _CLASS_KEYWORDS.items():
        if kw in t:
            return cls
    return "Organisation"

def makeName(string):
    if string is not None:
        string = string.replace('&', 'and')
        words = re.findall(r'\b[A-Za-z0-9]+\b', string)
        result = []
        for word in words:
            if word.isupper():
                result.append(word)
            else:
                result.append(word.capitalize())

        return ''.join(result)
    return ''

def handle_corp_division(graph: Graph, name: str):
    if "(" in name and name.endswith(")"):
        # general and specific names
        general_name = name[:name.index("(")].strip()  # e.g., "Google"
        specific_name = name.replace("(", "").replace(")", "").strip()  # e.g., "Google United States"
        print("general name", general_name, ", specific name:", specific_name)
        # uri
        specific_uri = URIRef(f"{RPO}{specific_name.replace(' ', '')}")
        general_uri = URIRef(f"{RPO}{general_name.replace(' ', '')}")
        print(general_uri)
        if len(general_name) > 1:
            graph.add((specific_uri, RPO.part_of, general_uri))
            graph.add((RPO.part_of, RDF.type, OWL.ObjectProperty))
            #graph.add((specific_uri, OWL.sameAs, general_uri))

            graph.add((specific_uri, RDF.type, RPO.Organisation))
            graph.add((general_uri, RDF.type, RPO.Organisation))
    

# ------------------- end of helper functions -----------------

# ------------------- scrap DBpedia for org info --------------

DBPEDIA_SPARQL = "https://dbpedia.org/sparql"
HEADERS = {"User-Agent": "ontology-lookup/0.1"}

def get_dbpedia_class(entity_name):
    uri = f"http://dbpedia.org/resource/{entity_name.replace(' ', '_').replace('-', '_').replace('.', '').replace(',', '')}"
    #print(f"trying uri {uri}")
    query = f"""
    PREFIX dbr: <http://dbpedia.org/resource/>
    PREFIX dbo: <http://dbpedia.org/ontology/>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT DISTINCT ?superclass WHERE {{
      <{uri}> rdf:type ?class .
      ?class rdfs:subClassOf* ?superclass .
      FILTER(STRSTARTS(STR(?superclass), "http://dbpedia.org/ontology/"))
    }}
    """
    time.sleep(0.1)
    response = requests.get(DBPEDIA_SPARQL, params={"query": query, "format": "json"}, headers=HEADERS, timeout=10)
    response.raise_for_status()
    data = response.json()

    superclasses = [binding["superclass"]["value"] for binding in data["results"]["bindings"]]
    scls = []
    for cl in superclasses:
        cl = cl[cl.index("y")+2:]
        scls.append(cl)
    return _classify_from_text("".join(scls))
    
def get_dbpedia_location(entity_name):

    uri = (
        "http://dbpedia.org/resource/"
        + entity_name.replace(" ", "_")
                      .replace("-", "_")
                      .replace(".", "")
                      .replace(",", "")
    )

    query = f"""
    PREFIX dbo:  <http://dbpedia.org/ontology/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT DISTINCT ?cityLabel ?countryLabel WHERE {{
      OPTIONAL {{
        <{uri}> dbo:location|dbo:headquarter|dbo:locationCity ?city .
        ?city rdfs:label ?cityLabel FILTER (lang(?cityLabel)="en")
      }}
      OPTIONAL {{
        <{uri}> dbo:country ?country .
        ?country rdfs:label ?countryLabel FILTER (lang(?countryLabel)="en")
      }}
    }}
    LIMIT 1
    """
    #time.sleep(0.8)
    try:
        res = requests.get(
            DBPEDIA_SPARQL,
            params={"query": query, "format": "json"},
            headers=HEADERS,
            timeout=15,
        )
        res.raise_for_status()
        bindings = res.json()["results"]["bindings"]
        if not bindings:
            return {"city": None, "country": None}

        row = bindings[0]
        #print(row)
        city    = row["cityLabel"]["value"]    if "cityLabel"    in row else None
        country = row["countryLabel"]["value"] if "countryLabel" in row else None
        return {"city": city, "country": country}

    except requests.exceptions.RequestException as e:
        #print(f"DBpedia location lookup failed for '{entity_name}': {e}")
        return {"city": None, "country": None}
    
def get_dbpedia_leadership(entity_name):
    uri = (
        "http://dbpedia.org/resource/"
        + entity_name.replace(" ", "_")
                      .replace("-", "_")
                      .replace(".", "")
                      .replace(",", "")
    )

    query = f"""
    PREFIX dbo: <http://dbpedia.org/ontology/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT DISTINCT ?ownerLabel ?keyPersonLabel ?ceoLabel ?presidentLabel WHERE {{
      OPTIONAL {{ <{uri}> dbo:owner      ?owner .       ?owner rdfs:label ?ownerLabel FILTER(lang(?ownerLabel)="en") }}
      OPTIONAL {{ <{uri}> dbp:keyPeople  ?keyPeople .   ?keyPeople rdfs:label ?keyPersonLabel FILTER(lang(?keyPersonLabel)="en") }}
      OPTIONAL {{ <{uri}> dbo:ceo        ?ceo .         ?ceo rdfs:label ?ceoLabel FILTER(lang(?ceoLabel)="en") }}
      OPTIONAL {{ <{uri}> dbo:president  ?president .   ?president rdfs:label ?presidentLabel FILTER(lang(?presidentLabel)="en") }}
    }}
    LIMIT 1
    """
    time.sleep(0.05)
    try:
        response = requests.get(
            DBPEDIA_SPARQL,
            params={"query": query, "format": "json"},
            headers=HEADERS,
            timeout=15,
        )
        response.raise_for_status()
        bindings = response.json()["results"]["bindings"]
        if not bindings:
            return {
                "owner": None,
                "key_person": None,
                "ceo": None,
                "president": None,
            }

        row = bindings[0]
        return {
            "owner": row.get("ownerLabel", {}).get("value"),
            "key_person": row.get("keyPersonLabel", {}).get("value"),
            "ceo": row.get("ceoLabel", {}).get("value"),
            "president": row.get("presidentLabel", {}).get("value"),
        }

    except requests.exceptions.RequestException as e:
        #print(f"DBpedia leadership lookup failed for '{entity_name}': {e}")
        return {
            "owner": None,
            "key_person": None,
            "ceo": None,
            "president": None,
        }

def detailed_org(graph, name):
    
    if "(" in name and name.endswith(")"):
        general_name = name[:name.index("(")].strip()
        handle_corp_division(graph, name)
    else:
        general_name = name
    """ DELETED BC NOT USEFUL
    try:
        #print(general_name)
        org = get_dbpedia_class(general_name)
    except Exception as e:
        print("exception class not found")
        org = "Organisation"
        
    try:
        result = get_dbpedia_location(general_name)
        city = result.get("city")
        #p("exception location not found")
        city = "--"
        country = "--"rint(city)
        country = result.get("country")
        #print(country)
    except Exception as e:
        #print """
    feature = ["keyPerson", None]    
    leadership = get_dbpedia_leadership(general_name)
    for key, value in leadership.items():
        if value is not None:
            feature = [key, value]
    #if db lookup failed
    return {
        f"key_person":    feature[1],
        "source":   "None",
    }


# ------------------- end of scrapping DBpedia --------------------


def get_funder_info(graph, paper_id, meta, authors):

    paper_uri = URIRef(f"{RPO}paper/{paper_id}")
    cross = meta.get("crossref") or {}
    for f in cross.get("funder", []):
        name = f.get("name")
        if not name:
            continue

        funder_uri = URIRef(f"{RPO}{makeName(name)}")
        graph.add((funder_uri, RDF.type, RPO.Organisation))
        graph.add((funder_uri, RPO.has_name, Literal(name)))
        print(f"    added funder {name}")
        
        more_fi = detailed_org(graph, name)
        """ DELETED DUE TO DETAILED_ORG FUNCTION CHANGE
        if more_fi.get("class"):
            graph.add((funder_uri, RDF.type, RPO[more_fi.get("class")]))
        if more_fi.get("city"):
            graph.add((funder_uri, RPO.located_in, RPO[makeName(more_fi.get("city"))]))
            graph.add((RPO[makeName(more_fi.get("city"))], RDF.type, RPO.City))
            print("added funder city for", name)
        if more_fi.get("country"):
            graph.add((funder_uri, RPO.located_in, RPO[makeName(more_fi.get("country"))]))
            graph.add((RPO[makeName(more_fi.get("country"))], RDF.type, RPO.Country))
        """ 
        if more_fi.get("key_person"):
            graph.add((funder_uri, RDF.key_person, RPO[makeName(more_fi.get("key_person"))]))


        # Paper - funder link
        graph.add((paper_uri, RPO.funded_by, funder_uri))

        # Author - funder link
        for a in authors:
            graph.add((a, RPO.funded_by, funder_uri))

        # Grants
        for award in f.get("award", []):
            grant_uri = URIRef(f"{RPO}grant/{_slugify(award)}")
            graph.add((grant_uri, RDF.type, RPO.Grant))
            graph.add((grant_uri, RPO.grant_id, Literal(award)))
            graph.add((RPO.grant_id, RDF.type, OWL.DatatypeProperty))
            graph.add((paper_uri, RPO.received_grant, grant_uri))
            graph.add((RPO.received_grant, RDF.type, OWL.ObjectProperty))
            graph.add((grant_uri, RPO.funding_amount, Literal("")))  # amount unknown
            graph.add((RPO.funding_amount, RDF.type, OWL.DatatypeProperty))
            graph.add((funder_uri, RPO.funds, grant_uri))
            graph.add((RPO.funds, RDF.type, OWL.ObjectProperty))
            #print(f"    added grant info of {award}")
            
        for award in f.get("grants", []):
            grant_uri = URIRef(f"{RPO}grant/{_slugify(award)}")
            graph.add((grant_uri, RDF.type, RPO.Grant))
            graph.add((grant_uri, RPO.grant_id, Literal(award)))
            graph.add((RPO.grant_id, RDF.type, OWL.DatatypeProperty))
            graph.add((paper_uri, RPO.received_grant, grant_uri))
            graph.add((RPO.received_grant, RDF.type, OWL.ObjectProperty))
            graph.add((grant_uri, RPO.funding_amount, Literal("")))  # amount unknown
            graph.add((RPO.funding_amount, RDF.type, OWL.DatatypeProperty))
            graph.add((funder_uri, RPO.funds, grant_uri))
            graph.add((RPO.funds, RDF.type, OWL.ObjectProperty))
            #print(f"    added grant info of {award}")

    
    
_citation_id_counter = count(start=10_000)   # unique Ids for unseen papers

def get_citation_info(graph, paper_id, meta):

    paper_uri = URIRef(f"{RPO}paper/{paper_id}")
    oa = meta.get("openalex")
    if not oa:
        return

    referenced = oa.get("referenced_works", [])
    if not referenced:
        return

    for cited_oa in referenced:
        # create synthetic ID → URI
        cited_pid = next(_citation_id_counter)
        cited_uri = URIRef(f"{RPO}paper/{cited_pid}")

        # minimal typing; metadata can be fetched later if desired
        graph.add((cited_uri, RDF.type, RPO.AcademicWork))

        # Paper‑level citation
        graph.add((paper_uri, RPO.cites, cited_uri))
        graph.add((RPO.cites, RDF.type, OWL.ObjectProperty))
        graph.add((cited_uri, RPO.cited_by, paper_uri))
        graph.add((RPO.cited_by, RDF.type, OWL.ObjectProperty))
    print(f"     added some citation info, for example {paper_id} cited {cited_pid}")

#publisher information
def get_publishing_info(graph, paper_id, meta):
    paper_uri = URIRef(f"{RPO}paper/{paper_id}")

    oa = meta.get("openalex") or {}
    cr = meta.get("crossref") or {}

    primary_location = oa.get("primary_location") or {}
    source = primary_location.get("source") or oa.get("source") or {}

    publisher_name = cr.get("publisher")
    if not publisher_name:
        publisher_name = oa.get("host_organization_name")
        if not publisher_name:
            return  # No publisher info available

    print(f"     publisher: {publisher_name}")

    # Create URI-safe ID
    publisher_id = publisher_name.replace(" ", "_").replace(",", "").replace(".", "")
    publisher_uri = URIRef(f"{RPO}org/{publisher_id}")

    graph.add((paper_uri, RPO.published_by, publisher_uri))
    graph.add((RPO.published_by, RDF.type, OWL.ObjectProperty))
    graph.add((publisher_uri, RDF.type, RPO.Organisation))

    # Detect publishing platform type
    oa_type = source.get("type", "").lower()
    cr_type = cr.get("type_crossref", "").lower()

    if oa_type == "journal" or cr_type == "journal-article":
        graph.add((publisher_uri, RDF.type, RPO.Journal))
    elif oa_type == "conference" or cr_type == "proceedings-article":
        graph.add((publisher_uri, RDF.type, RPO.Conference))
    elif oa_type == "repository":
        graph.add((publisher_uri, RDF.type, RPO.Repository))
    else:
        graph.add((publisher_uri, RDF.type, RPO.Organisation))  # fallback
        
    more = detailed_org(graph, publisher_name)
    if more.get("key_person"):
        graph.add((publisher_uri, RPO.key_person, RPO[makeName(more.get("key_person"))]))
        

    # Add readable name
    graph.add((publisher_uri, RPO.has_name, Literal(publisher_name)))

# geospatial enrichment

_WD_ENDPOINT = "https://query.wikidata.org/sparql"
_WD_SEARCH   = "https://www.wikidata.org/w/api.php"
_GEO_PROPS   = {
    "state":       "P131",   # located in the admin. territorial entity
    "country":     "P17",    # country
    "continent":   "P30",    # continent
}

#@lru_cache(maxsize=1024)
def _wikidata_qid(label):
    params = {
        "action": "wbsearchentities",
        "search": label,
        "language": "en",
        "format": "json",
        "type": "item",
        "limit": 5
    }
    r = requests.get(_WD_SEARCH, params=params, timeout=15,
                     headers={"User-Agent": "ontology-enricher/0.1"})
    if not r.ok:
        return None
    for item in r.json().get("search", []):
        if item["label"].lower() == label.lower():
            return item["id"]
    return None

#@lru_cache(maxsize=1024)
def _geo_hierarchy(qid):

    select_parts = " ".join(f"OPTIONAL {{ wd:{qid} wdt:{prop} ?{lvl}. ?{lvl} rdfs:label ?{lvl}Label FILTER(lang(?{lvl}Label)='en') }}" 
                            for lvl, prop in _GEO_PROPS.items())
    q = f"SELECT * WHERE {{ {select_parts} }} LIMIT 1"
    r = requests.get(_WD_ENDPOINT, params={"query": q, "format": "json"}, timeout=30,
                     headers={"User-Agent": "ontology-enricher/0.1"})
    res = {}
    if r.ok:
        for lvl in _GEO_PROPS:
            lab = f"{lvl}Label"
            ent = f"?{lvl}"
            binding = r.json()["results"]["bindings"]
            if binding and lab in binding[0]:
                res[lvl] = (binding[0][lab]["value"], binding[0][ent[1:]]["value"].split("/")[-1])
    return res

def get_geo_info(graph: Graph):
    """
    For every *literal* object of rpo:located_in, look up Wikidata and add
    broader places:  city -> state -> country -> continent.
    """
    for s, p, o in list(graph.triples((None, RPO.located_in, None))):
        if not isinstance(o, Literal):
            continue  # already a URIRef, skip

        place_name = str(o)
        qid = _wikidata_qid(place_name)
        if not qid:
            continue

        # Create URI for the original place
        place_uri = URIRef(f"{RPO}place/{_slugify(place_name)}")
        graph.remove((s, RPO.located_in, o))
        graph.add((s, RPO.located_in, place_uri))
        graph.add((place_uri, RDF.type, RPO.Place))
        graph.add((place_uri, RDFS.label, Literal(place_name)))

        # Add broader hierarchy
        hierarchy = _geo_hierarchy(qid)
        parent_uri = place_uri
        for lvl in ("state", "country", "continent"):
            if lvl in hierarchy:
                label, qid_lvl = hierarchy[lvl]
                lvl_uri = URIRef(f"{RPO}place/{qid_lvl}")
                graph.add((lvl_uri, RDF.type, RPO.Place))
                graph.add((lvl_uri, RDFS.label, Literal(label)))
                graph.add((parent_uri, RPO.located_in, lvl_uri))
                parent_uri = lvl_uri   # walk upwards


"""def get_concepts_info():
    types in my ontology: Topic, ResearchField, ResearchArea, Goal, Ideology, Keyword, SocietalProblem
    add all the below mentioned features as instances of their types and add triples like paperuri has_topic topic etc.
    #openalex topics
    #cso topics
    #ResearchField, ResearchArea
    #keywords
    #Goal
    #SocietalProblem
    pass"""
    
def _concept_class(level):

    if level == 0:
        return RPO.ResearchField
    if level == 1:
        return RPO.ResearchArea
    return RPO.Topic

def get_concepts_info(graph, paper_id, meta):
    paper_uri = URIRef(f"{RPO}paper/{paper_id}")
    
    if not meta.get("openalex"):
        return

    # OpenAlex concepts (fields of study)
    if "concepts" in meta.get("openalex"):
        for c in meta.get("openalex", {}).get("concepts", []):
            name = c.get("display_name")
            if not name:
                continue
            level = c.get("level")
            concept_uri = URIRef(f"{RPO}{makeName(name)}")
            graph.add((concept_uri, RDF.type, _concept_class(level)))
            graph.add((concept_uri, RDFS.label, Literal(name)))
            graph.add((paper_uri, RPO.has_topic, concept_uri))
            graph.add((RPO.has_topic, RDF.type, OWL.ObjectProperty))

    # Crossref/OpenAlex keywords (if any)
    keywords = meta.get("openalex", {}).get("keywords", [])
    for kw in keywords:
        if isinstance(kw, dict):  # if keyword is a dict with display_name
            kw_name = kw.get("display_name")
        else:
            kw_name = kw  # assume it's a plain string
        if not kw_name:
            continue
        kw_uri = URIRef(f"{RPO}{makeName(kw_name)}")
        graph.add((kw_uri, RDF.type, RPO.Keyword))
        graph.add((kw_uri, RDFS.label, Literal(kw_name)))
        graph.add((paper_uri, RPO.has_keyword, kw_uri))
        graph.add((RPO.has_keyword, RDF.type, OWL.ObjectProperty))
        
    if "sustainable_development_goals" in meta.get("openalex"):
        goals = meta.get("openalex").get("sustainable_development_goals")
        for goal in goals:
            name = goal.get("display_name")
            graph.add((RPO[makeName(name)], RDF.type, RPO.Goal))
            graph.add((paper_uri, RPO.addresses, RPO[makeName(name)]))
            graph.add((RPO.addresses, RDF.type, OWL.ObjectProperty))

"""def main():
    folder = Path("test_papers_txt")
    
    #uncomment to load papers from folder
    #papers = process_all_papers(folder)
    
    #or use pickle
    with open("papers.pkl", "rb") as f:
        papers = pickle.load(f)

    g = Graph()
    g.bind("rpo", RPO)
    g.bind("rdf", RDF)
    g.bind("pro", PRO)
    g.bind("foaf", FOAF)

    for pid, meta in papers.items():
        add_paper(g, pid, meta)
        authors = get_authors(g, pid, meta)
        get_funder_info(g, pid, meta, authors)
        get_citation_info(g, pid, meta)
        get_publishing_info(g, pid, meta)
        get_concepts_info(g, pid, meta)
        
    get_geo_info(g)

    #PRINT STATEMENT: progress report
    #print(f"Processed {len(papers)} paper(s):")
    # ""for pid, meta in papers.items():
    #    doi = (
    #        (meta['openalex'] or {}).get('doi')
    #        or (meta['crossref'] or {}).get('DOI')
    #        or 'no‑doi'
    #    )
    #    print(f"  #{pid:<3} «{meta['title'][:60]}…» → DOI: {doi}")""

    #serialize the graph for inspection
    g.serialize("papers.ttl", format="turtle")
    with open("papers.pkl", "wb") as f:
        pickle.dump(papers, f)

if __name__ == "__main__":
    print(f"Current working directory: {Path.cwd()}")
    main()
    """
    
def build_kg_from_csv(csv_path, output_prefix = "kg_chunk"):
    
    chunk_size = 100
    chunk_index = 1
    paper_counter = 0
    
    g = Graph()

    g.bind("rpo", RPO)
    g.bind("foaf", FOAF)
    g.bind("pro", PRO)

    with csv_path.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)

        for row in reader:
            paper_id = int(row["id"])
            year = row["year"]
            doi = row["doi"]
            title = row["title"]
            first_author = row["first_author"]

            # parse oa and cr json columns
            oa_rec = json.loads(row["openalex_json"]) if row["openalex_json"].strip() else {}
            cr_rec = json.loads(row["crossref_json"]) if row["crossref_json"].strip() else {}

            meta = {
                "year": year,
                "doi": doi,
                "title": title,
                "first_author": first_author,
                "openalex": oa_rec,
                "crossref": cr_rec
            }
            
            paper_counter += 1
            if paper_counter > 0: #this was a helper statement before

                add_paper(g, paper_id, meta)
                authors = get_authors(g, paper_id, meta)
                get_funder_info(g, paper_id, meta, authors)
                get_citation_info(g, paper_id, meta)
                get_publishing_info(g, paper_id, meta)
                get_concepts_info(g, paper_id, meta)
            
                if paper_counter == chunk_size :
                    get_geo_info(g)

                    out_file = f"{output_prefix}_{chunk_index}.ttl"
                    g.serialize(destination=out_file, format="turtle")

                    print(f"s aved chunk {chunk_index} to {out_file}")

                    # reset counters and graph
                    chunk_index += 1
                    paper_counter = 0

                    g = Graph()
                    g.bind("rpo", RPO)
                    g.bind("foaf", FOAF)
                    g.bind("pro", PRO)
            
        if paper_counter > 0:
            get_geo_info(g)

            out_file = f"{output_prefix}_{chunk_index}.ttl"
            g.serialize(destination=out_file, format="turtle")

            print(f"saved final chunk {chunk_index} to {out_file}")
            
    
# RUN
csv_input = Path("articles_oa_cr_metadata.csv")
kg_output = Path("subgraphs_oa_cr/kg1")

build_kg_from_csv(csv_input, kg_output)