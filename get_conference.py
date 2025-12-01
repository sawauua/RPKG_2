import os
import re
import csv
import json
from pathlib import Path

articles = []
p_index = 1
out_path = Path("articles_conferece.csv")

for i in range(20):
    folder_year = 2015 + i

    pdf_folder = os.path.join("papers_pdf", f"eswc_{folder_year}")
    conf = "ESWC"
    
    #loop over iswc too
    if i > 9:
        folder_year -= 10
        pdf_folder = os.path.join("papers_pdf", f"iswc_{folder_year}")
        conf = "ISWC"

    # get list of all pdf files in the folder
    pdf_files = [f for f in os.listdir(pdf_folder) if f.endswith(".pdf")]

    # read all pdf files in the folder
    for pdf_file in pdf_files:
        p_index += 1
        data = {}
        data["index"] = p_index
        data["conf"] = conf
        articles.append(data)
        if p_index % 50 == 0:
            print(f" =========== Processed {p_index} papers ==========")
        
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        
        writer.writerow([
            "index", 
            "conf"
        ])
        
        for data in articles:
            writer.writerow([
                data.get("index"),
                data.get("conf"),
            ])
        
        