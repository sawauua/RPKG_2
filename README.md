1. Articles gathered from Springer Nature Link ESWC proceedings 2015-2024 and ISWC proceedings 2015-2014 (in pdfs). dir: /papers_pdf
2. Run pdf_to_data.py to gather title (not clean), first author (not clean), year of creation, doi (where possible) and create unique ids. Resulting file: articles.csv
3. Run metadata_oa_cr.py to correct primary metadata and gather all metadata from openalex and crossref. Resulting file: articles_oa_cr_metadata.csv
4. Run metadata_to_rdf.py to create a KG based on collected metadata, supported by dbpedia lookups to correct some names and classes. Resulting files: 12 subgraphs kg_1.ttl to kg_12.ttl (they had to be divided due to exceeding requests for dbpedia).
5. Run merge_oa_cr_subs.py to merge subgraphs from he folder into one kg: oa_cr_full.ttl .
6. Add-on: gather apc (article processing cost) by running apc_trial.py. Resulting file: apc_paid.ttl
7. Try to gather CS-KG information via cskg_subgraph.py. Unfortunately CS-KG SPARQL endpoint is not working.

Add-on: divide pdfs into text sections (unfinished, probably useful later) in divide_into_sections.py
