# divide pdf text into sections

import fitz
import os
import re
from PyPDF2 import PdfReader

os.chdir("C:/Users/FTS Demo/Documents/rp_kg_project/paper_eswc")

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

        # Sort by descending font size (largest text is likely title)
        sorted_spans = sorted(spans_with_size, key=lambda x: -x[1])
        top_size = sorted_spans[0][1]
        
        # USE THIS FOR SECTION EXTRACTION
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

            sections = []
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
                    metadata["sections"] = [sect for sect in sections]
            si += 1
            
        # --- split full_text into sections based on section titles ---
        sections_dict = {}
        current_title = None
        buffer = []

        for txt, size in spans_with_size:
            if abs(size - section_size) < 0.1:
                #section title
                if current_title is not None:
                    #save previous section
                    sections_dict[current_title] = " ".join(buffer).strip()
                current_title = txt.strip(" ,;.:")
                buffer = []
            else:
                if current_title is not None:
                    buffer.append(txt.strip())

        #save the last section
        if current_title is not None:
            sections_dict[current_title] = " ".join(buffer).strip()

        metadata["sections"] = sections_dict
        print(metadata)
        
    return metadata

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
        sections = extract_metadata_from_pdf(pdf_path)['sections']

            
        gathered["sections"] = sections
            
    return gathered

articles = []
p_index = 1

for i in range(1):
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
        
        