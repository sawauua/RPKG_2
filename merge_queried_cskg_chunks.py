from rdflib import Graph, Namespace, RDF

g = Graph()

RPO  = Namespace("http://www.semanticweb.org/ftsdemo/ontologies/2025/5/rpo#")
PRO  = Namespace("http://purl.org/spar/pro/")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
CSKG = Namespace("https://w3id.org/cskg/resource/")
CSKG_ONT = Namespace("https://w3id.org/cskg/ontology#")
XSD = Namespace("http://www.w3.org/2001/XMLSchema#")

g.bind("cskg", CSKG)
g.bind("rpo", RPO)
g.bind("cskg-ont", CSKG_ONT)
g.bind("rdf", RDF)
g.bind("xsd", XSD)

filenames = ["chunk1_fixed.ttl", "chunk2_fixed.ttl", "chunk3_fixed.ttl", "chunk4_fixed.ttl", "chunk5_fixed.ttl", "chunk6_fixed.ttl"]

for file in filenames:
    print(f"loading {file}")
    g.parse(source = f"cskg_queries_results/{file}", format = "turtle")
    
print("merging")
g.serialize("cskg_output.ttl", format="turtle")
print("saved")
    