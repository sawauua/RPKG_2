from rdflib import Graph, Namespace, RDF, URIRef, Literal, RDFS, OWL
from pathlib import Path
import os
import csv
import json
import re
from itertools import count

target_dir = Path("C:/Users/FTS Demo/Documents/rp_kg_project/RPKG_2")
os.chdir(target_dir)

#prefixes to namespace uri
RPO  = Namespace("http://www.semanticweb.org/ftsdemo/ontologies/2025/5/rpo#")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
    

#add paper
def add_paper(graph, paper_id, meta):
    #add general paper triples
    
    #create uri for the paper
    paper_uri = RPO[f"paper{paper_id}"]

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
            #print(f"     oa id {oa_id}")
        
        year = (meta["openalex"].get("publication_year"))
        if year:
            graph.add((paper_uri, RPO.published_in_year, Literal(year)))
            graph.add((RPO.published_in_year, RDF.type, OWL.DatatypeProperty))
            #print(f"     year {year}")

        cites = meta["openalex"].get("cited_by_count")
        if cites is not None:
            graph.add((paper_uri, RPO.nr_of_citations, Literal(cites)))
            graph.add((RPO.nr_of_citations, RDF.type, OWL.DatatypeProperty))
            #print(f"     cit count {cites}")

        lang = meta["openalex"].get("language")
        if lang:
            graph.add((paper_uri, RPO.language, Literal(lang)))
            graph.add((RPO.language, RDF.type, OWL.DatatypeProperty))
            #print(f"     lang {lang}")
        #print(f"    added {paper_id} basic metadata")
        
    elif meta["crossref"]:
        print("OPENALEX NOT FOUND FOR", paper_id)
        pass
        
    graph.add((paper_uri, RPO.has_title, Literal(meta["title"])))

# ---------------------------------------------
    
#get authors
def get_authors(graph, paper_id, meta):
    """
    Gathers author information from openalex, including their names and affiliated institutions.
    Links paper to authors using rpo:written_by and rpo:wrote properties.
    Links authors to each other using rpo:works_with property.
    Adds institutional data from extract_affiliation_from_mtadata().

    """
    paper_uri = RPO[f"paper{paper_id}"]
    oa = meta["openalex"]
    if not oa:
        return
    
    author_uris: list[URIRef] = []

    for auth in oa.get("authorships", []):
        auth_id = auth["author"]["id"]
        full_name = auth["author"]["display_name"]
        auth_uri = URIRef(f"{RPO}{makeName(full_name)}")
        if auth_id:
            graph.add((auth_uri, RPO.has_id, Literal(auth_id)))
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
    """
    processes affiliations of one author as listed in openalex.
    Classifies institutions by heuristic keywords.
    Splits nmes of affiliations to detect links to geographica entities via a heuristic.

    """
    
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

def _slugify(text):
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
    """
    Uses a manualy created mapping to classify organisations.

    """
    t = text.lower()
    for kw, cls in _CLASS_KEYWORDS.items():
        if kw in t:
            return cls
    return "Organisation"

def makeName(string):
    """
    Creates names for individuals according to the chosen convention (camel case for things)

    """
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

def handle_corp_division(graph, name):
    """
    Detects whether a geographical location is mentioned in the Organisation Name,
        if yes, creates a specific ad general name for the Organisation (e.g. BMW (Germany) becomes BMW and BMW Germany)

    """
    if "(" in name and name.endswith(")"):
        # general and specific names
        general_name = name[:name.index("(")].strip()  
        specific_name = name.replace("(", "").replace(")", "").strip()  
        print("general name", general_name, ", specific name:", specific_name)
        # uri
        specific_uri = URIRef(f"{RPO}{specific_name.replace(' ', '')}")
        general_uri = URIRef(f"{RPO}{general_name.replace(' ', '')}")
        print(general_uri)
        if len(general_name) > 1:
            graph.add((specific_uri, RPO.part_of, general_uri))
            graph.add((RPO.part_of, RDF.type, OWL.ObjectProperty))

            graph.add((specific_uri, RDF.type, RPO.Organisation))
            graph.add((general_uri, RDF.type, RPO.Organisation))
            
            
def get_funder_info(graph, paper_id, meta, authors):
    """
    Gathers information about funders and grants from openalex and crossref (often incomplete)

    """

    paper_uri = RPO[f"paper{paper_id}"]
    cross = meta.get("crossref") or {}
    for f in cross.get("funder", []):
        name = f.get("name")
        if not name:
            continue

        funder_uri = URIRef(f"{RPO}{makeName(name)}")
        graph.add((funder_uri, RDF.type, RPO.Organisation))
        graph.add((funder_uri, RPO.has_name, Literal(name)))
        print(f"    added funder {name}")
        
        # Paper - funder link
        graph.add((paper_uri, RPO.funded_by, funder_uri))
        # Author - funder link
        for a in authors:
            graph.add((a, RPO.funded_by, funder_uri))
        # Grants
        for award in f.get("award", []):
            grant_uri = RPO[_slugify(award)]
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
            grant_uri = RPO[_slugify(award)]
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
    """
    created links between dataset articles and articles cited by them

    """

    paper_uri = RPO[f"paper{paper_id}"]
    oa = meta.get("openalex")
    if not oa:
        return

    referenced = oa.get("referenced_works", [])
    if not referenced:
        return

    for cited_oa in referenced:
        # create synthetic ID → URI
        cited_pid = next(_citation_id_counter)
        cited_uri = RPO[f"paper{cited_pid}"]

        # minimal typing; metadata can be fetched later if desired
        graph.add((cited_uri, RDF.type, RPO.AcademicWork))

        # Paper‑level citation
        graph.add((paper_uri, RPO.cites, cited_uri))
        graph.add((RPO.cites, RDF.type, OWL.ObjectProperty))
        graph.add((cited_uri, RPO.cited_by, paper_uri))
        graph.add((RPO.cited_by, RDF.type, OWL.ObjectProperty))
    #print(f"     added some citation info, for example {paper_id} cited {cited_pid}")

#publisher information
def get_publishing_info(graph, paper_id, meta):
    """
    Gathers information about publishing entity

    """
    paper_uri = RPO[f"paper{paper_id}"]

    oa = meta.get("openalex") or {}
    cr = meta.get("crossref") or {}

    primary_location = oa.get("primary_location") or {}
    source = primary_location.get("source") or oa.get("source") or {}

    publisher_name = cr.get("publisher")
    if not publisher_name:
        publisher_name = oa.get("host_organization_name")
        if not publisher_name:
            return  # No publisher info available

    #print(f"     publisher: {publisher_name}")

    # create URI-safe id
    publisher_id = publisher_name.replace(" ", "_").replace(",", "").replace(".", "")
    publisher_uri = RPO[publisher_id]

    graph.add((paper_uri, RPO.published_by, publisher_uri))
    graph.add((RPO.published_by, RDF.type, OWL.ObjectProperty))
    graph.add((publisher_uri, RDF.type, RPO.Organisation))

    #detect publishing platform type
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
        
    # Add readable name
    graph.add((publisher_uri, RPO.has_name, Literal(publisher_name)))

def _concept_class(level):

    if level == 0:
        return RPO.ResearchField
    if level == 1:
        return RPO.ResearchArea
    return RPO.Topic

def get_concepts_info(graph, paper_id, meta):
    """
    gathers research areas an fields, keywords, topics, sustainable development goals (SDG) form openalex

    """
    paper_uri = RPO[f"paper{paper_id}"]
    
    if not meta.get("openalex"):
        return
    #openalex concepts (fields of study)
    if "concepts" in meta.get("openalex"):
        for c in meta.get("openalex", {}).get("concepts", []):
            name = c.get("display_name")
            if not name:
                continue
            level = c.get("level")
            concept_uri = RPO[makeName(name)]
            graph.add((concept_uri, RDF.type, _concept_class(level)))
            graph.add((concept_uri, RDFS.label, Literal(name)))
            graph.add((paper_uri, RPO.has_topic, concept_uri))
            graph.add((RPO.has_topic, RDF.type, OWL.ObjectProperty))

    # keywords
    keywords = meta.get("openalex", {}).get("keywords", [])
    for kw in keywords:
        if isinstance(kw, dict):  # if keyword is a dict with display_name
            kw_name = kw.get("display_name")
        else:
            kw_name = kw
        if not kw_name:
            continue
        kw_uri = RPO[makeName(kw_name)]
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


def build_kg_from_csv(csv_path, output_prefix = "kg_chunk"):
    """
    construct subgraphs based on articlea_oa_cr_metadata.csv
    creates chunks due to possible errors from dbpedia /wikidata (exhausting the API)
    if an error occurs, change index and continue making subsequent subgraphs

    """
    
    chunk_size = 100
    chunk_index = 1
    paper_counter = 0
    
    g = Graph()

    g.bind("rpo", RPO)
    g.bind("foaf", FOAF)

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
            if paper_counter > 0:

                add_paper(g, paper_id, meta)
                authors = get_authors(g, paper_id, meta)
                get_funder_info(g, paper_id, meta, authors)
                get_citation_info(g, paper_id, meta)
                get_publishing_info(g, paper_id, meta)
                get_concepts_info(g, paper_id, meta)
            
                #if paper_counter == chunk_size :
#
                    #out_file = f"{output_prefix}_{chunk_index}.ttl"
                    #g.serialize(destination=out_file, format="turtle")

                    #print(f"saved chunk {chunk_index} to {out_file}")

                    # reset counters and graph
                    #chunk_index += 1
                    #paper_counter = 0

                    #g = Graph()
                    #g.bind("rpo", RPO)
                    #g.bind("foaf", FOAF)
            
        #if paper_counter > 0:

    out_file = f"{output_prefix}_full.ttl"
    g.serialize(destination=out_file, format="turtle")
    print('saved to kg1_full.ttl')
    #print(f"saved final chunk {chunk_index} to {out_file}")
            
    
# ---------------------------- RUN -------------------------------
csv_input = Path("articles_oa_cr_metadata.csv")
kg_output = Path("subgraphs_oa_cr/kg1")

build_kg_from_csv(csv_input, kg_output)