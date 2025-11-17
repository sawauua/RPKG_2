from rdflib import Graph, Namespace, RDF, URIRef, Literal, RDFS, OWL
from pathlib import Path
import os

RPO  = Namespace("http://www.semanticweb.org/ftsdemo/ontologies/2025/5/rpo#")
RDF = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
PRO  = Namespace("http://purl.org/spar/pro/")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")

target_dir = Path("C:/Users/FTS Demo/Documents/rp_kg_project/paper_eswc")
os.chdir(target_dir)

def merge_ttl_subgraphs(input_folder: Path, output_file: Path):

    merged = Graph()
    
    merged.bind("rpo", RPO)
    merged.bind("foaf", FOAF)
    merged.bind("pro", PRO)

    ttl_files = sorted(input_folder.glob("*.ttl"))

    print(f"found {len(ttl_files)} ttl files to merge.")

    for ttl_file in ttl_files:
        temp_g = Graph()
        temp_g.bind("rpo", RPO)
        temp_g.bind("foaf", FOAF)
        temp_g.bind("pro", PRO)
        
        
        temp_g.parse(ttl_file, format="turtle")

        merged += temp_g  # merges without duplication

    merged.serialize(destination=output_file, format="turtle")
    print(f"merged graph saved to: {output_file}\n")

input_dir = Path("subgraphs_oa_cr")
output_ttl = Path("oa_cr_full.ttl")

merge_ttl_subgraphs(input_dir, output_ttl)