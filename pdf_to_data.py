import fitz #PyMuPDF for structured text extraction
import re #for pattern detection
import os #for path
from pathlib import Path #for managing paths
from PyPDF2 import PdfReader #another reader for metadata
import csv
import unicodedata

os.chdir("C:/Users/FTS Demo/Documents/rp_kg_project/RPKG_2")

def pdf_to_txt(pdf_path):
    """
        read pdfs and transform into txt and data
        extracts:
            
    """
    with open(pdf_path, 'rb') as pdf_file:
        
        gathered = {}
        
        reader = PdfReader(pdf_file)
        metadata = reader.metadata
        
        gathered["year"] = metadata.creation_date.year
        
        #extract title, author, doi from metadata
        if metadata.title is not None:
            title = metadata.title
            f_author = metadata.author
            if metadata.subject is not None:
                doi = metadata.subject.split("doi:")[1]
                gathered["doi"] = doi
            
            gathered["title"] = title
            gathered["f_author"] = f_author
        else:
            #extraxt metadata from pdf directly
            meta_text = extract_metadata_from_pdf(pdf_path)
            
            gathered["title"] = meta_text["title"]
            if "," not in meta_text["authors"] and "and" not in meta_text["authors"]:
                gathered["f_author"] = meta_text["authors"]
            else:
                authors = meta_text["authors"].split(",")[0]
                author = authors.split(" and")[0]
                gathered["f_author"] = author
            
    return gathered
            
        
# ----------- extract title when metadata unavailable ---------------#

def extract_metadata_from_pdf(pdf_path):
    
    metadata = {"title": "", "authors": "", "year": "", "doi": ""}

    with fitz.open(pdf_path) as doc:
        if len(doc) == 0:
            return metadata
        
        full_text = ""
        for p in doc:
            full_text += p.get_text("text") + "\n"

        page = doc[0]
        text_dict = page.get_text("dict")

        spans_with_size = []
        for block in text_dict["blocks"]:
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    txt = span.get("text", "").strip()
                    if txt:
                        spans_with_size.append((txt, span["size"]))

        if not spans_with_size:
            return metadata

        # Sort by descending font size (largest text is likely title)
        sorted_spans = sorted(spans_with_size, key=lambda x: -x[1])
        top_size = sorted_spans[0][1]

        # Collect all text with the top font size (title may be multiline)
        title_parts = [txt for txt, size in spans_with_size if abs(size - top_size) < 0.1]
        metadata["title"] = " ".join(title_parts).strip()
        
        
        """ USE THIS FOR SECTION EXTRACTION
        # Find text right after the title for authors/affiliations
        # Typically, authors are the next smaller font size
        next_sizes = sorted(set(size for _, size in spans_with_size if size < top_size), reverse=True)
        if next_sizes:
            author_size = next_sizes[0]
            author_texts = [txt for txt, size in spans_with_size if abs(size - author_size) < 0.1]
            candidate_text = " ".join(author_texts)
            # Split by commas or semicolons
            possible_authors = re.split(r',|;', candidate_text)
            authors = [a.strip() for a in possible_authors if 2 < len(a.strip()) < 100]
            metadata["authors"] = ", ".join(authors)

            # Affiliations often contain keywords
            affiliations = [
                a for a in authors
                if re.search(r"University|Institute|College|Lab|Center|Department|@|School", a, re.I)
            ]
            metadata["affiliations"] = affiliations"""
            
        # authors
        authors = extract_authors(full_text[:2000], metadata["title"])
        metadata["authors"] = authors

        # Search full text for doi
        full_text = ""
        for page in doc:
            full_text += page.get_text("text") + "\n"

        doi_match = re.search(r'doi\.org/(\S+)', full_text, re.I)
        if doi_match:
            metadata["doi"] = doi_match.group(1).strip().rstrip('.')

    return metadata


def extract_authors(text, title):

    # find abstract
    match = re.search(r'(?i)\babstract\b', text)
    snippet = text[len(title):match.start()] if match else text[:1000]

    # heuristic: lines between title and abstract
    lines = [l.strip() for l in snippet.split("\n") if l.strip()]
    if len(lines) > 0:
        # authors usually appear on the second non-empty line on the first page snippet
        authors = lines[0]
        authors = re.sub(r'\s*(?:\([^)]+\)|\[[^\]]+\]|\{[^}]+\})', '', authors)  # drop (…), […], {...}
        authors = re.sub(r'[\u00B9\u00B2\u00B3\u0131\u2070-\u2079⁰¹²³⁴⁵⁶⁷⁸⁹]|[0-9]+', '', authors).strip()
        
        return normalize_text(authors)
    return "", []
#------------------------- normalize text ---------------------------#

def normalize_text(s):
    if not isinstance(s, str):
        return s
    s = unicodedata.normalize("NFKC", s)
    return s.encode("ascii", "ignore").decode("ascii")
    
# ------------------------- read pdf(s) -----------------------------#
        
#parse eswc pdf folders
p_index = 1
articles = []

for i in range(20):
    folder_year = 2015 + i

    pdf_folder = os.path.join("papers_pdf", f"eswc_{folder_year}")
    
    #loop over iswc too
    if i > 9:
        folder_year -= 10
        pdf_folder = os.path.join("papers_pdf", f"iswc_{folder_year}")
        print(pdf_folder)

    # get list of all pdf files in the folder
    pdf_files = [f for f in os.listdir(pdf_folder) if f.endswith(".pdf")]

    # read all pdf files in the folder
    for pdf_file in pdf_files:
        p_index += 1
        data = pdf_to_txt(os.path.join(pdf_folder, pdf_file))
        data["id"] = p_index
        articles.append(data)
    
    print("folder: ", i+1 )
        
count = 0
no_title = 0
no_author = 0
no_year = 0
no_doi = 0
for art in articles:
    count += 1
    
    #check titles
    if "title" not in art:
        no_title += 1
    elif art["title"] is None:
        no_title += 1
    
    #check authors
    if "f_author" not in art:
        no_author += 1
    elif art["f_author"] is None:
        no_author += 1
    
    #check year
    if "year" not in art:
        no_year += 1
    elif art["year"] is None:
        no_year += 1
    
    #check doi
    if "doi" not in art:
        no_doi += 1
    elif art["doi"] is None:
        no_doi += 1
        
print(f"{no_title} articles out of {count} have no title")
print(f"{no_author} articles out of {count} have no first author")
print(f"{no_year} articles out of {count} have no year")
print(f"{no_doi} articles out of {count} have no doi")

keys = articles[300].keys()

with open('articles.csv', 'w', newline ='', encoding="utf-8") as output_file:
    dict_writer = csv.DictWriter(output_file, keys)
    dict_writer.writeheader()
    dict_writer.writerows(articles)