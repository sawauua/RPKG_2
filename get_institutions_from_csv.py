from rdflib import Graph, Namespace, RDF, URIRef, Literal, RDFS, OWL
import json
from pathlib import Path
import os
import re
import csv
import requests

target_dir = Path("C:/Users/FTS Demo/Documents/rp_kg_project/RPKG_2")
os.chdir(target_dir)

csv_path = Path("articles_oa_cr_metadata.csv")

OA_TO_RPO = {
    "education": "University",
    "company": "Company",
    "government": "StateInstitution",
    "nonprofit": "NGO",
    "political": "PoliticalOrganisation",
    "military": "MilitaryOrganisation",
    "international": "InternationalOrganisation",
}

RPO  = Namespace("http://www.semanticweb.org/ftsdemo/ontologies/2025/5/rpo#")
PRO  = Namespace("http://purl.org/spar/pro/")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")

def fetch_oa_inst(inst_id):
    
    try:
        url = f"https://api.openalex.org/institutions/{inst_id}"
        r = requests.get(url, timeout = 15)
        if r.status_code != 200:
            return None
        return r.json()
    except:
        print(f"exception institution not found")
        return None
    
def makename(name):
    goodname = re.sub(r'[^a-zA-Z0-9]', '', name)
    return goodname.replace(" ", "")

def class_inst(oa_data):
    
    if not oa_data:
        return "Organisation"
    
    OA_TO_RPO = {
        "education": "University",
        "company": "Company",
        "government": "StateInstitution",
        "nonprofit": "NGO",
        "political": "PoliticalOrganisation",
        "military": "MilitaryOrganisation",
        "international": "InternationalOrganisation",
    }
    
    inst_type = oa_data.get("type", "").lower()
    return OA_TO_RPO.get(inst_type, "Organisation")


def extract_affiliation_types(author):
    """Extract (id, type) pairs from an author's affiliations list."""
    out = []
    affs = author.get("institutions", [])
    for aff in affs:
        aff_id = aff.get("id")
        aff_type = aff.get("type")
        if aff_id:
            out.append((aff_id, aff_type))
            
    #print(type(affs), len(affs))
    #if len(affs) > 0:
    #    aff_id = affs.get("id")
    #    aff_type = affs.get("type")
    #    if aff_id:
    #        out.append((aff_id, aff_type))
    return out


def extract_funder_types(oa_data):
    """extract (id, type) pairs from the top-level funders list"""
    out = []
    funders = oa_data.get("funders", [])  # or "grants", depending on structure
    for f in funders:
        funder_id = f.get("funder", {}).get("id")
        funder_type = f.get("funder", {}).get("type")
        if funder_id:
            out.append((funder_id, funder_type))
            print("FUND FUND FUND FUND FUND FUND FUND FUND FUND FUND")
    
    return out

def add_top_company(g, institution):
    
    parents = institution.get("associated_institutions", [])
    for p in parents:
        if p.get("relationship") == "parent":
            return None
        
    display_country_name = institution.get("geo").get("country")
    institution_name = institution.get("display_name")
    
    if display_country_name in institution_name:
            institution_name = re.sub(r'[^a-zA-Z0-9]', '', institution_name)
            institution_top = institution_name.split(display_country_name)[0]
            g.add((RPO[makename(institution_top)], RPO.located_in, RPO[makename(display_country_name)]))
            g.add((RPO[makename(institution_top)], RDF.type, RPO[class_inst(institution)]))
    return None

# MAIN

def extract_affiliations(csv_path):

    institution_cache = {}

    fundi = 0

    with csv_path.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        
        results = {}

        for row in reader:
            paper_id = int(row["id"])

            if paper_id % 10 == 0:
                print(f" \n paper number {paper_id} \n")

            # parse oa and cr json columns
            oa_rec = json.loads(row["openalex_json"]) if row["openalex_json"].strip() else {}
                

            if not oa_rec:
                continue


            for author in oa_rec.get("authorships", []):
                author_f = author.get("author", {}).get("display_name")
                if not author_f:
                    continue
                author_uri = RPO[makename(author_f)]
                print(author_f)
                
                for inst_id, _ in extract_affiliation_types(author):
                    
                    org_info(institution_cache, inst_id, author_uri = author_uri)
                    
            for fund_id, _ in extract_funder_types(oa_rec):
                    
                org_info(institution_cache, fund_id, author_uri = author_uri, fund = True)

    OUTPUT_TTL = "institutions_affiliations.ttl"
    g.serialize(destination=OUTPUT_TTL, format="turtle")
    print(f"Saved RDF graph to {OUTPUT_TTL}")

    print(f"funders found for {fundi} papers")
    print("\nDone.")
    return g

def org_info(cache, org_id, author_uri = False, fund = False):
    
    if org_id not in cache:
        meta = fetch_oa_inst(org_id)
        cache[org_id] = meta
    else:
        meta = cache[org_id]
    
    if meta:
        name = meta.get("display_name", "UnknownInstitution")
        inst_uri = RPO[makename(name)]
        if author_uri:
            g.add((author_uri, RPO.affiliated_with, inst_uri))
        if author_uri and fund:
            g.add((author_uri, RPO.funded_by, inst_uri))
            
        g.add((inst_uri, FOAF["name"], Literal(name)))
        g.add((inst_uri, RPO.oa_id, Literal(org_id)))
        city = meta.get("geo").get("city")
        country = meta.get("geo").get("country")
        geonames = meta.get("geo").get("geonames_city_id")
        g.add((inst_uri, RPO.located_in, RPO[makename(city)]))
        g.add((inst_uri, RPO.located_in, RPO[makename(country)]))
        g.add((RPO[makename(city)], RPO.located_in, RPO[makename(country)]))
        g.add((RPO[makename(city)], RDF.type , RPO.City))
        g.add((RPO[makename(country)], RDF.type , RPO.Country))
        g.add((RPO[makename(city)], RPO.geonames_id, RPO[geonames]))
        print(city)
    
        parent = meta.get("associated_institutions", [])
        for parent_inst in parent:
            if parent_inst.get("relationship") == "parent":
                parent_id = parent_inst.get("id")
                if parent_id:
                    parent_uri = RPO[makename(parent_inst.get("display_name", "UnknownInstitution"))]
                    g.add((inst_uri, RPO.part_of, parent_uri))
                    g.add((parent_uri, RPO.oa_id, Literal(parent_id)))
                    g.add((parent_uri, FOAF.name, Literal(parent_inst.get("display_name", "UnknownInstitution"))))
        add_top_company(g, meta)

        for child_inst in parent:
            if child_inst.get("relationship") == "child":
                child_id = child_inst.get("id")
                if child_id:
                    child_uri = RPO[makename(child_inst.get("display_name", "UnknownInstitution"))]
                    #print(child_uri)
                    g.add((child_uri, RPO.part_of, inst_uri))
                    g.add((child_uri, RPO.oa_id, Literal(child_id)))
                    g.add((child_uri, FOAF.name, Literal(child_inst.get("display_name", "UnknownInstitution"))))
            
        inst_type = class_inst(meta)
        g.add((inst_uri, RDF.type, RPO[inst_type]))
    

g = Graph()
g.bind("rpo", RPO)
g.bind("rdf", RDF)
g.bind("pro", PRO)
g.bind("foaf", FOAF)

extract_affiliations(csv_path)