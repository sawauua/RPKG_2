from rdflib import Graph, Namespace, RDF, URIRef, Literal, RDFS, OWL
from rdflib.namespace import OWL
from pathlib import Path
from itertools import count
import urllib.parse
import re
import requests
import os
import pickle
import csv
import json
import time

target_dir = Path("C:/Users/FTS Demo/Documents/rp_kg_project/paper_eswc")
os.chdir(target_dir)

#prefixes to namespace uri
RPO  = Namespace("http://www.semanticweb.org/ftsdemo/ontologies/2025/5/rpo#")
RDF = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
PRO  = Namespace("http://purl.org/spar/pro/")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
    
#!geo location to everything


#search openalex by doi
def search_openalex_by_doi(doi):
    url = f"https://api.openalex.org/works/https://doi.org/{doi}"
    try:
        r = requests.get(url, timeout = 20)
        if r.status_code == 200:
            return r.json()
    except requests.RequestException:
        print("RequestException, no doi found")
        pass
    return None


#search crossref by doi
def search_crossref_by_doi(doi):
    url = f"https://api.crossref.org/works/{doi}"
    try:
        r = requests.get(url, timeout = 20)
        if r.status_code == 200:
            return r.json().get("message")
    except requests.RequestException:
        print("RequestException, no doi in crossref")
        pass
    return None


#search openalex by title + year
def search_openalex_by_title_year(title, year):
    url = "https://api.openalex.org/works"
    
    clean_title = title.replace('"', '')
    
    params = {
        "filter": f'title_and_abstract.search:"{clean_title}",publication_year:{year}',
        "per_page": 5
    }

    try:
        r = requests.get(url, params = params, timeout = 20)
        r.raise_for_status()
        results = r.json().get("results", [])
        if results:
            return results[0]
    except requests.RequestException:
        print("requestException, no title+year in openalex")
        pass
    return None


#search crossref by title + year
def search_crossref_by_title_year(title, year):
    url = "https://api.crossref.org/works"
    clean_title = normalize_title(title)
    
    params = {
        "query": clean_title,
        "filter": f"from-pub-date:{year}-01-01,until-pub-date:{year}-12-31",
        "rows": 5
    }
    try:
        r = requests.get(url, params = params, timeout = 20)
        r.raise_for_status()
        items = r.json().get("message", {}).get("items", [])
        if items:
            return items[0]
    except requests.RequestException:
        print("RequestException, title+year not in crossref")
        pass
    return None
#helper
def normalize_title(title):
    title = re.sub(r'[^A-Za-z0-9 ]+', ' ', title)
    title = re.sub(r'\s+', ' ', title)
    return title.strip()


#get metadata according to csv
def get_best_title(oa_rec, cr_rec, fallback_title):
    if oa_rec and "title" in oa_rec:
        return oa_rec["title"]
    if cr_rec and "title" in cr_rec and cr_rec["title"]:
        return cr_rec["title"][0]
    return fallback_title

def get_best_doi(oa_rec, cr_rec, fallback_doi):
    if fallback_doi:
        return fallback_doi
    if oa_rec and "doi" in oa_rec and oa_rec["doi"]:
        return oa_rec["doi"].replace("https://doi.org/", "")
    if cr_rec and cr_rec.get("DOI"):
        return cr_rec["DOI"]
    return None

def get_best_first_author(oa_rec, cr_rec, fallback_author):
    #openaex
    if oa_rec and "authorships" in oa_rec and oa_rec["authorships"]:
        name = oa_rec["authorships"][0]["author"]["display_name"]
        if name:
            return name
        
    #crossref
    if cr_rec and "author" in cr_rec and cr_rec["author"]:
        first = cr_rec["author"][0]
        given = first.get("given", "")
        family = first.get("family", "")
        name = f"{given} {family}".strip()
        if name:
            return name

    return fallback_author

#process papers from folder, create a dict with metadata

def process_all_papers(csv_path):
    """returns
    {
     id: {
        "year"
        "doi"
        "title
        "first_author"
        "openalex": {oa_rec}
        "crossref": {cr_rec}
        }
    }
    """
    paper_dict = {}
    oa_ni = 0
    cr_ni = 0
    
    with csv_path.open(encoding = "utf-8") as fh:
        reader = csv.reader(fh)
        next(reader)
        
        for row in reader:
            year, doi, title, author, paper_id = row
            year = str(year).strip()
            title = title.strip()
            author = author.strip()
            paper_id = int(paper_id)
            
            #search by doi
            if doi:
                oa_rec = search_openalex_by_doi(doi)
                cr_rec = search_crossref_by_doi(doi)
            else:
                oa_rec = search_openalex_by_title_year(title, year)
                cr_rec = search_crossref_by_title_year(title, year)
                
            corrected_title = get_best_title(oa_rec, cr_rec, title)
            corrected_doi = get_best_doi(oa_rec, cr_rec, doi)
            corrected_author = get_best_first_author(oa_rec, cr_rec, author)
            
            paper_dict[paper_id] = {
                "year": year,
                "doi": corrected_doi,
                "title": corrected_title,
                "first_author": corrected_author,
                "openalex": oa_rec,
                "crossref": cr_rec
                }
            
            #print(paper_dict[paper_id])
            print(paper_id)
            print("title:", paper_dict[paper_id]["title"])
            print("doi:", paper_dict[paper_id]["doi"])
            print("author:", paper_dict[paper_id]["first_author"])
            if paper_dict[paper_id]["openalex"] is not None:
                print("openalex included")
            else:
                oa_ni += 1
            if paper_dict[paper_id]["crossref"] is not None:
                print("crossref included")
            else:
                cr_ni += 1
            print("")
            print("")
            
        print(f"OpenAlex failed for {oa_ni} papers.")
        print(f"Crossref failed for {cr_ni} papers.")
    return paper_dict


#save this
def save_full_records_to_csv(papers, out_path):
    """
    save all metadata including full openalex and crossref json records
    json fields are serialized into single csv cells.
    """
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)

        # header
        writer.writerow([
            "id", 
            "year", 
            "doi", 
            "title", 
            "first_author",
            "openalex_json",
            "crossref_json"
        ])
        
        for pid, data in papers.items():
            oa_json = json.dumps(data.get("openalex", {}), ensure_ascii=False)
            cr_json = json.dumps(data.get("crossref", {}), ensure_ascii=False)

            writer.writerow([
                pid,
                data.get("year", ""),
                data.get("doi", ""),
                data.get("title", ""),
                data.get("first_author", ""),
                oa_json,
                cr_json,
            ])


csv_p = Path("articles.csv")

papers = process_all_papers(csv_p)

save_full_records_to_csv(papers, Path("articles_oa_cr_metadata.csv"))