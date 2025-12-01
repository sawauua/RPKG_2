#### Instructions on how to run the pipeline

1. Articles gathered from Springer Nature Link ESWC proceedings 2015-2024 and ISWC proceedings 2015-2014 (in pdfs). dir: /papers_pdf
2. Run pdf_to_data.py to gather title (not clean), first author (not clean), year of creation, doi (where possible) and create unique ids. Resulting file: articles.csv
3. Run metadata_oa_cr.py to correct primary metadata and gather all metadata from openalex and crossref. Resulting file: articles_oa_cr_metadata.csv
4. Run metadata_to_rdf.py to create a KG based on collected metadata, supported by dbpedia lookups to correct some names and classes. Resulting files: 12 subgraphs kg_1.ttl to kg_12.ttl (they had to be divided due to exceeding requests for dbpedia).
5. Run merge_oa_cr_subs.py to merge subgraphs from he folder into one kg: oa_cr_full.ttl .
6. Run get_insitutions_to_csv.py to get parent institutions of those mentioned in the openalex metadata. Creates institutions_affiliations.ttl subgraph.
8. Run apc_trial.py to gather apc (article processing cost) Resulting file: apc_paid.ttl
9. Run general_merger.py to merge metadata subgraphs oa_cr_full.ttl, institutions_affiliations.ttl, apc_paid.ttl. Resulting file: merged.ttl
10. Run get_conference.py to gather conference type (omitted in metadata_to_rdf.py). Creates articles_conference.csv
11. Run divide_into_sections.py to prepare section txt for NER. resulting file: articles_sections.csv
12. Run acknowledgments.py to separate Acknowledgments section (omitted in divide_into_sections.py). Resulting file: articles_sections_acknowledgments.csv
13. Run oa_ids_for_cskg.py in chunks (change index in line 25) and paste the ids into cskg_chunks_query.txt.
14. Gather CS-KG information via the CS-KG Sparql endpoint using and cskg_chunks_query.txt save into /cskg_queries_results . oiginal queries were ran 6 time, each chunk for 200 ids.
15. Run rdf_to_ttl.py (several times depending on chunk number) in /cskg_queries_results to tranform rdf cskg chunks into turtle
16. Run merge_queried_cskg_chunks.py to merge cskg chunks into one cskg subgraph. Resulting file: cskg_output.ttl
