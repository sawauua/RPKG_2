from rdflib import Graph, Namespace, RDF, URIRef, Literal, RDFS, OWL
from pathlib import Path
import os
import csv
import json
import re


target_dir = Path("C:/Users/FTS Demo/Documents/rp_kg_project/RPKG_2")
os.chdir(target_dir)

csv_path = Path("cskg_queries_results/cskg_research_entities.csv")

#prefixes to namespace uri
RPO  = Namespace("http://www.semanticweb.org/ftsdemo/ontologies/2025/5/rpo#")
PRO  = Namespace("http://purl.org/spar/pro/")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")

with csv_path.open(encoding="utf-8") as fh:
    reader = csv.DictReader(fh)
    
    entities = []
    ent_uris = {}
    
    types = []
    type_uris = {}
    for row in reader:
        entity = row["entity"]
        e_type = row["type"]
        ent_name = entity.split("ce/")[-1]
        type_name = e_type.split("#")[-1]
        
        entities.append(ent_name)
        ent_uris[ent_name] = entity
        
        if type_name not in types:
            types.append(type_name)
            type_uris[type_name] = e_type
            
#print(entities)

def capitalize(string):
    return string.replace("_", " ").title().replace(" ", "")

def decapitalize(string):
    s1 = re.sub(r'(?<!^)(?=[A-Z][a-z])', '_', string)
    s2 = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', '_', s1)
    return s2.lower()

for ent in entities:
    capital_ent = ent.replace("_", " ").title().replace(" ", "")
    #print(capital_ent)
    
counter = 0
    
g = Graph()
g.bind("rpo", RPO)
print("Parsing graph")
g.parse("NER_dirty.ttl", format = "ttl")

for s, p, o in g:
    if p == RDF.type and o in [RPO.Geographical, RPO.Organisation, RPO.Thing]:
        thingname = decapitalize(s.split("#")[-1])
        #print(s)
        #print(thingname)
        if thingname in entities:
            counter += 1
            g.remove((s, p, o))
            g.add((s, RDF.type, RPO[type_uris[thingname]]))
            print(f"similarity detected \n {s.split('#')[-1]} of type thingname added")

g.serialize(destination="NER_dirty_corrected.ttl", format = "turtle")