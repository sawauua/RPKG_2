#get OA_IDs, print them, copy paste into cskg_chunk_query

import csv
import json
import os
from pathlib import Path

os.chdir("C:/Users/FTS Demo/Documents/rp_kg_project/RPKG_2")

csv_path = Path("articles_oa_cr_metadata.csv") 

OA_IDs = []

with csv_path.open(encoding="utf-8") as fh:
    reader = csv.DictReader(fh)

    for row in reader:
        paper_id = int(row["id"])
        doi = row["doi"]
        oa_rec = json.loads(row["openalex_json"]) if row["openalex_json"].strip() else {}
        if oa_rec.get("id"):
            OA_IDs.append(oa_rec.get("id").split("org/")[-1])
        
#chunks implemented for readability. copy ids and paste into cskg_chunks_query.txt
for oad in OA_IDs[0:200]:
    print(f"     cskg:{oad}")
