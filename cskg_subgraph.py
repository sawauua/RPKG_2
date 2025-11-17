from rdflib import Graph, Namespace, URIRef, Literal
from SPARQLWrapper import SPARQLWrapper, TURTLE
from urllib.parse import quote
from tqdm import tqdm
from pathlib import Path
import csv

# --- rpo namespace (adjust if different) ---------------------------
RPO = Namespace("http://www.semanticweb.org/ftsdemo/ontologies/2025/5/rpo#")

def collect_dois(csv_path):
    
    dois = []

    with csv_path.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)

        for row in reader:
            dois.append(["doi"])

    return dois

        
"""
harvest subgraphs for many dois from the cs-kg sparql endpoint
and save as a single turtle file.
"""


# ---------- CONFIG -------------------------------------------------
ENDPOINT = "https://cskg.kmi.open.ac.uk/sparql"      # adjust if different
OUT_FILE = "cskg_subset.ttl"
# -------------------------------------------------------------------

PREFIXES = """
PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX cskg-ont: <https://w3id.org/cskg/ontology#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
"""

CONSTRUCT_TEMPLATE = PREFIXES + """
CONSTRUCT {
    ?s ?p ?o .
}
WHERE {
    # (1) locate the paper
    ?paper cskg-ont:doi "%ENCODED_DOI%"^^xsd:anyURI .

    # (2) triples where paper is subject
    { ?paper ?p ?o  BIND(?paper AS ?s) }
    UNION
    # (3) triples where paper is object
    { ?s ?p ?paper  BIND(?paper AS ?o) }

    UNION
    # (4) full statements derived from the paper
    { ?stmt prov:wasDerivedFrom ?paper .
      ?stmt ?p ?o .
      BIND(?stmt AS ?s)
    }
}
"""

def fetch_subgraph(endpoint: str, doi: str) -> str:
    """
    Run one CONSTRUCT query and return Turtle string for a single DOI.
    """
    enc_doi = quote(f"https%3A//doi.org/{doi}")
    query = CONSTRUCT_TEMPLATE.replace("%ENCODED_DOI%", enc_doi)

    sparql = SPARQLWrapper(endpoint)
    sparql.setQuery(query)
    sparql.setReturnFormat(TURTLE)
    return sparql.query().convert().decode("utf-8")


def main():
    g = Graph()

    for doi in tqdm(DOIS, desc="Querying CS-KG"):
        try:
            turtle_data = fetch_subgraph(ENDPOINT, doi)
            g.parse(data=turtle_data, format="turtle")
        except Exception as e:
            tqdm.write(f"  DOI {doi} failed: {e}")

    g.serialize(destination=OUT_FILE, format="turtle")
    print(f"\n saved combined graph to {OUT_FILE} ({len(g)} triples)")

#if __name__ == "__main__":
#    main()

if __name__ == "__main__":
    doi_list = collect_dois(Path("articles_oa_cr_metadata.csv"))
    DOIS = doi_list
    main()
