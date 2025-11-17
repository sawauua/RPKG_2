from rdflib import Graph, Namespace, RDF, URIRef, Literal, RDFS, OWL
import csv
import json
from pathlib import Path
import os

target_dir = Path("C:/Users/FTS Demo/Documents/rp_kg_project/RPKG_2")
os.chdir(target_dir)

RPO  = Namespace("http://www.semanticweb.org/ftsdemo/ontologies/2025/5/rpo#")
RDF = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
PRO  = Namespace("http://purl.org/spar/pro/")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")

def get_apc(csv_path, output_path):
    
    g = Graph()

    g.bind("rpo", RPO)
    g.bind("foaf", FOAF)
    g.bind("pro", PRO)

    with csv_path.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)

        for row in reader:
            paper_id = int(row["id"])
            
            paper_uri = URIRef(f"{RPO}paper/{paper_id}")

            # parse oa and cr json columns
            oa_rec = json.loads(row["openalex_json"]) if row["openalex_json"].strip() else {}
            cr_rec = json.loads(row["crossref_json"]) if row["crossref_json"].strip() else {}

            if oa_rec:
                apc = oa_rec.get("apc_paid")
                if apc:
                    
                    g.add((paper_uri, RPO.apc_paid, Literal(apc.get('value'))))
                    g.add((paper_uri, RPO.apc_currency, Literal(apc.get('currency'))))
                    print(f"id {paper_id}, paid {apc.get('value')} in {apc.get('currency')}")
    
    g.serialize(destination=output_path, format="turtle")
    print(f"KG saved to {output_path}")
# RUN
csv_input = Path("articles_oa_cr_metadata.csv")

output_path = Path("apc_paid.ttl")

get_apc(csv_input, output_path)