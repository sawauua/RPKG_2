from rdflib import Graph, Namespace

g = Graph()
#add chunk2, chunk3, etc
g.parse("chunk1.rdf", format="xml")

g.bind("cskg", Namespace("https://w3id.org/cskg/resource/"))
g.bind("cskg-ont", Namespace("https://w3id.org/cskg/ontology#"))
g.bind("rpo", Namespace("http://www.semanticweb.org/ftsdemo/ontologies/2025/5/rpo#"))
g.bind("rdf", Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#"))
g.bind("xsd", Namespace("http://www.w3.org/2001/XMLSchema#"))


g.serialize("chunk1_fixed.ttl", format="turtle")
print("Saved as output_fixed.ttl")