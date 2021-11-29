import json
import gzip
import sys
import xlsxwriter
json_file = sys.argv[1]
# json_file = "../output-andrey/carakasamhita-0.json.gz"
xlsx_path = json_file.replace("json.gz","xlsx")

workbook = xlsxwriter.Workbook(xlsx_path)
worksheet = workbook.add_worksheet()
worksheet.set_column(5, 6, 100)
worksheet.set_column(1, 2, 25)

row = 0

worksheet.write(row, 0, "Number")
worksheet.write(row, 1, "Inquiry file")
worksheet.write(row, 2, "Hit file")
worksheet.write(row, 3, "Score")
worksheet.write(row, 4, "Length")
worksheet.write(row, 5, "Inquiry Text")
worksheet.write(row, 6, "Hit Text")

row += 1

with gzip.open(json_file) as f:
    parallels = json.load(f)[1]
    parallels = sorted(parallels, key=lambda d: d['root_pos_beg']) 
    cfilename = parallels[0]['root_segnr'][0].split(':')[0]
    for parallel in parallels:
        pfilename = parallel['par_segnr'][0].split(':')[0]
        if cfilename != pfilename:
            par_string = parallel['par_string']
            root_string = parallel['root_string']
            score = parallel['score']
            length = parallel['root_length']
            worksheet.write(row, 0, row)
            worksheet.write(row, 1, cfilename)
            worksheet.write(row, 2, pfilename)
            worksheet.write(row, 3, score)
            worksheet.write(row, 4, length)
            worksheet.write(row, 5, root_string)
            worksheet.write(row, 6, par_string)
            row += 1     

workbook.close()
