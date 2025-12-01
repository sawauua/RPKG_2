import csv
import json

input_file = "articles_sections.csv"
output_file = "articles_sections_acknowledgments.csv"

with open(input_file, newline='', encoding='utf-8') as infile, \
     open(output_file, 'w', newline='', encoding='utf-8') as outfile:

    reader = csv.reader(infile)
    writer = csv.writer(outfile)

    header = next(reader)
    writer.writerow(header)

    for row in reader:
        paper_id = row[0]
        try:
            data = json.loads(row[1])
        except:
            writer.writerow(row)
            continue

        keys = list(data.keys())
        if len(keys) < 2:
            writer.writerow([paper_id, row[1]])
            continue

        second_last_key = keys[-2]
        #print(second_last_key)
        text = data[second_last_key]
        lower_text = text.lower()

        # look for "acknowledgment" or "acknowledgments"
        pos = lower_text.find("acknowledgment")
        if pos != -1:
            ack_text = text[pos:].strip()
            section_text = text[:pos].strip()
            data[second_last_key] = section_text
            data["Acknowledgments"] = ack_text
            print(paper_id)
            print(ack_text)

        writer.writerow([paper_id, json.dumps(data, ensure_ascii=False)])
