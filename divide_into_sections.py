# divide pdf text into sections

import fitz
import os
import re
import csv
import json
from PyPDF2 import PdfReader
from pathlib import Path

os.chdir("C:/Users/FTS Demo/Documents/rp_kg_project/RPKG_2")

def extract_metadata_from_pdf(pdf_path):
    
    metadata = {"sections": ""}

    with fitz.open(pdf_path) as doc:
        if len(doc) == 0:
            return metadata
        
        full_text = ""
        spans_with_size = []
        

        for p in doc:
            full_text += p.get_text("text") + "\n"

            #collect font size info from every page
            text_dict = p.get_text("dict")
            for block in text_dict.get("blocks", []):
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        txt = span.get("text", "").strip()
                        if txt:
                            spans_with_size.append((txt, span.get("size")))

        if not spans_with_size:
            return metadata

        # sort by descending font size (largest text is likely title)
        sorted_spans = sorted(spans_with_size, key=lambda x: -x[1])
        top_size = sorted_spans[0][1]
        
        # sections are smaller font size
        next_sizes = sorted(set(size for _, size in spans_with_size if size < top_size), reverse=True)
        
        candidate_text = ""
        si = 0
        
        while len(candidate_text) < 5 and si < len(next_sizes):
            section_size = next_sizes[si]
            section_texts = [txt for txt, size in spans_with_size if abs(size - section_size) < 0.1]
            candidate_text = " ".join(section_texts)

            pattern = (
                r'(?i)'  # case-insensitive flag at start
                r'\b\d+(?:\.\d+)*\s+[A-Z][^\d,;]{2,}'
                r'|'
                r'\b(?:References|Bibliography|Acknowledgments?|Appendix)\b'  # last sections
                )

            possible_sections = re.findall(pattern, candidate_text)

            sections = ["Abstract"]
            for s in possible_sections:
                s = s.strip(" ,;.")
                if 2 < len(s) < 200 and s not in sections:
                    if 'References' in s:
                        sections.append(s.split(" R")[0])
                        sections.append("References")
                    elif "Bibliography" in s:
                        sections.append(s.split(" B")[0])
                        sections.append("Bibliography")
                    else:
                        sections.append(s)
            si += 1
            
        # --- split full_text into sections based on section titles ---
        sections_dict = {}
        current_title = None
        buffer = []
        
        sections_dict = split_sections(full_text, sections)
        
        for title, content in sections_dict.items():
            if title == "Abstract":
                print(title, content[:200], "...\n")
                    
        
    return sections_dict

def remove_math(text):

    # remove latex math environments
    text = re.sub(r'\$\$.*?\$\$', ' ', text, flags=re.DOTALL)
    text = re.sub(r'\\\[.*?\\\]', ' ', text, flags=re.DOTALL)

    text = re.sub(r'\$[^$]+\$', ' ', text)
    text = re.sub(r'\\\(.*?\\\)', ' ', text)

    text = re.sub(r'\\begin\{equation\*?\}.*?\\end\{equation\*?\}', ' ', text, flags=re.DOTALL)
    text = re.sub(r'\\begin\{align\*?\}.*?\\end\{align\*?\}', ' ', text, flags=re.DOTALL)
    text = re.sub(r'\\begin\{math\}.*?\\end\{math\}', ' ', text, flags=re.DOTALL)

    text = re.sub(r'\( ?\d+ ?\)', ' ', text)
    text = re.sub(r'\b[Ee]q\.?\s*\(?\d+\)?', ' ', text)
    text = re.sub(r'\b[Ee]quation\s*\(?\d+\)?', ' ', text)

    text = re.sub(r'([=<>±×÷∑∫√∂∆∇≈≠≤≥→←↔∞∈∉∪∩∅∀∃∈∑]+)', ' ', text)

    greek_letters = r'αβγδεζηθικλμνξοπρστυφχψωΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ'
    text = re.sub(f'[{greek_letters}]', ' ', text)

    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()

def split_sections(full_text, titles):
    """
    full_text : string containing all PDF text
    titles    : list of section titles as detected, e.g. ['1 Introduction', '2 Related Work']
    
    Returns dict: { "1 Introduction": "...text...", "2 Related Work": "...text..." }
    """

    # normalize whitespace
    normalized = re.sub(r"\s+", " ", full_text).strip()

    # normalize and sort titles by length descending
    titles = sorted([re.sub(r"\s+", " ", t.strip()) for t in titles],
                    key=len, reverse=True)
    pattern = "|".join(re.escape(t) for t in titles)
    matches = list(re.finditer(pattern, normalized))
    
    sections = {}

    for i, m in enumerate(matches):
        title = m.group()

        start = m.end()   # content begins after the title

        if i + 1 < len(matches):
            end = matches[i+1].start()
            content = normalized[start:end].strip()
        else:
            content = normalized[start:].strip()

        sections[title] = content

    return sections

def pdf_to_txt(pdf_path):
    """
        read pdfs and transform into txt and data
            
    """
    with open(pdf_path, 'rb') as pdf_file:
        
        gathered = {}
        
        reader = PdfReader(pdf_file)
        metadata = reader.metadata
        
        gathered["year"] = metadata.creation_date.year
        
        #extract title, author, doi from metadata
        sections = extract_metadata_from_pdf(pdf_path)

            
        gathered["sections"] = sections
            
    return gathered

articles = []
p_index = 1
out_path = Path("articles_sections.csv")

for i in range(20):
    folder_year = 2015 + i

    pdf_folder = os.path.join("papers_pdf", f"eswc_{folder_year}")
    
    #loop over iswc too
    if i > 9:
        folder_year -= 10
        pdf_folder = os.path.join("papers_pdf", f"iswc_{folder_year}")

    # get list of all pdf files in the folder
    pdf_files = [f for f in os.listdir(pdf_folder) if f.endswith(".pdf")]

    # read all pdf files in the folder
    for pdf_file in pdf_files:
        p_index += 1
        data = pdf_to_txt(pdf_file)
        data["id"] = p_index
        articles.append(data)
        if p_index % 50 == 0:
            print(f" =========== Processed {p_index} papers ==========")
        
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        
        writer.writerow([
            "id", 
            "sections"
        ])
        
        for data in articles:
            writer.writerow([
                data.get("id"),
                json.dumps(data.get("sections")),
            ])
        
        