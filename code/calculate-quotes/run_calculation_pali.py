from calculate_quotes_pali import populate_index
from calculate_quotes import calculate_all
from quotes_constants import *

#populate_index(PALI_TSV_DATA_PATH)



output_path = PALI_OUTPUT_FOLDER + "raw/"
calculation = calculate_all(PALI_WORDS_PATH,PALI_INDEX_PATH,output_path)
calculation.process_all()

# todo: process_lists muss hier noch mit rein... warscheinlich muessen wir da viel neu schreiben. 


