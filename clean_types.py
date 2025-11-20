from rdflib import Graph, Namespace, RDF, URIRef, Literal, RDFS, OWL
from pathlib import Path
import os
import csv
import json
import re
import requests

target_dir = Path("C:/Users/FTS Demo/Documents/rp_kg_project/RPKG_2")
os.chdir(target_dir)

#prefixes to namespace uri
RPO  = Namespace("http://www.semanticweb.org/ftsdemo/ontologies/2025/5/rpo#")
RDF = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
PRO  = Namespace("http://purl.org/spar/pro/")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")

filepath = "oa_cr_full.ttl"

target_classes = {"Orgaisation": ["Organisation"], "Place": ["City", "Country", "Continent"]}

connections = {"of", "from", "for", "at", "the", "in"}

def split_name(name):
    
    name = re.sub(r"[_-]+", " ", name)
    name = re.sub(r"(?<!^)(?=[A-Z])", " ", name)
    words = [w.strip() for w in name.split() if w.strip()]
    return " ".join(words)


def get_oa(clean_name):
    #query openalex
    
    url = f"https://openalex.org/institutions?page=1&filter=default.search:{clean_name}"
    
    try:
        r = requests.get(url, timeout = 10)
        if r.status_code != 200:
            return None
        results = r.json().get("results", [])
        if not results:
            return None
        
        return results[0]
    except Exception:
        print(f"exception, {clean_name} not found")
        
        
def infer_roles(oa_thing):
    
    if not oa_thing:
        return {"unknown"}
    
    roles = set()
    entity_type = oa_thing.get("type")
    
    if entity_type == "institution":
        institution_type = oa_thing.get("hint", "").lower
        
        for i in institution_type:
            roles.add(i)
            
    return roles

def get_subclasses(graph, class_uri):
    
    subclasses = {class_uri}
    to_check = [class_uri]
    
    while to_check:
        current = to_check.pop()
        for s in graph.subjects(RDFS.subClassOf, current):
            if s not in subclasses:
                subclasses.add(s)
                to_check.append(s)
    return subclasses

def main():
    
    g = Graph()
    g.parse(filepath, format="ttl")
    
    organisation_class_uri = RPO.Organisation
    place_class_uri = [RPO.City, RPO.Country, RPO.Continent]
    
    org_classes = [RPO.NGO, RPO.University, RPO.Organisation, RPO.PoliticalOrganisation, RPO.StateInstitution, RPO.PublishingCompany, RPO.MilitaryOrganisation, RPO.Company, RPO.InternationalOrganisation]
    
    place_classes = [RPO.City, RPO.Country, RPO.Continent]
    
    results_dict = {}
    
    print("scanning")
    for subj, rdf_type in g.subject_objects(RDF.type):
        
        if rdf_type in org_classes or rdf_type in place_classes:
            
            print(rdf_type)
            
            name = str(subj).split("rpo#")[1]
            
            clean_name = split_name(name)
            openalex_r = get_oa(clean_name)
            roles = infer_roles(openalex_r)
            
            print(f"\n Old type: {rdf_type}")
            print(f"splitted name name: {clean_name}")
            print(f"detected roles: {roles}")
            
            results_dict[name] = list(roles)
            
    print(f"{len(results_dict)} instances")
    
    return results_dict

results = main()
            
            