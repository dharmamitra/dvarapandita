import sys
import gzip
from tqdm import tqdm as tqdm
import pprint
import json
import gzip
import os
pp = pprint.PrettyPrinter(indent=4)
import multiprocessing
from Levenshtein import distance 

def check_files(filea,fileb):
    global quotes1,quotes2
    global total_quotes1,total_quotes2
    quotes1 = {}
    quotes2 = {}
    total_quotes1 = []
    total_quotes2 = []
    with gzip.open(filea,'rt') as f:
        segments1,quotes = json.load(f)
        for quote in quotes:
            quote_segment = quote['par_segnr'][0]
            if "4027" in quote_segment:
                total_quotes1.append(quote)
                if not quote_segment in quotes1:
                    quotes1[quote_segment] = [quote]
                else:
                    quotes1[quote_segment].append(quote)
                
    with gzip.open(fileb,'rt') as f:
        segments1,quotes = json.load(f)
        for quote in quotes:
            quote_segment = quote['par_segnr'][0]
            if "4021" in quote_segment:
                total_quotes2.append(quote)
                if not quote_segment in quotes1:
                    quotes2[quote_segment] = [quote]
                else:
                    quotes2[quote_segment].append(quote)
    #this loop is to test if we have overlapping entries                
    # for main_quote in total_quotes1:
    #     for slave_quote in total_quotes1:
    #         if not main_quote == slave_quote:
    #             if ((not set(main_quote['par_segnr']).isdisjoint(slave_quote['par_segnr'])) and
    #                 (not set(main_quote['root_segnr']).isdisjoint(slave_quote['root_segnr']))):
    #                 print("MAIN QUOTE",main_quote)
    #                 print("SLAVE QUOTE",slave_quote)
    not_found = 0
    found = 0            
    c = 0
    for main_quote in total_quotes2:
        par_string = main_quote['par_string']
        found_flag = False
        smallest_pair = []
        last_distance = 100

        for slave_quote in total_quotes1:
            if any(x in main_quote['par_segnr'] for x in slave_quote['root_segnr']):
                #print("MAIN",main_quote['par_segnr'])
                #print("SLAVE",slave_quote['root_segnr'])
                root_string = slave_quote['root_string']
                current_distance = distance(root_string,par_string)
                if current_distance < last_distance:
                    smallest_pair = [main_quote,slave_quote]
                    last_distance = current_distance
                if current_distance < 2:
                    found_flag = True
                    break            
        if not found_flag:
            print("NEW NOT FOUND PAIR:")
            print(main_quote['par_segnr'][0])
            print("MAIN  TEXT ROOT STRING",main_quote['root_string'])
            print("MAIN  TEXT PAR STRING",main_quote['par_string'])
            print(main_quote)
            if len(smallest_pair) == 2:
                print("SLAVE TEXT ROOT STRING",smallest_pair[1]['root_string'])
                print("SLAVE TEXT PAR STRING",smallest_pair[1]['par_string'])
                print(smallest_pair[1])
            not_found +=1
        else:
            found += 1
    print("FOUND",found)
    print("NOT FOUND",not_found)

    
    # for quote_key in quotes1.keys():
    #     current_quotes = quotes1[quote_key]
    #     for quote in current_quotes:
    #         parsegnr = quote['root_segnr'][0]
    #         if parsegnr in quotes2:
    #             target_quotes = quotes2[parsegnr]
    #             got_something = 0 
    #             for target_quote in target_quotes:
            
    #                 if (parsegnr == target_quote['par_segnr'][0] and
    #                     quote['par_segnr'][0] == target_quote['root_segnr'][0]):                        
    #                     if abs(quote['root_offset_beg'] - target_quote['par_offset_beg']) > 1  or abs(quote['root_offset_end'] - target_quote['par_offset_end']) > 1:
    #                         print("PARSEGNR",parsegnr)
    #                         print("CURRENT MAIN QUOTE")
    #                         pp.pprint(quote)
    #                         print("CURRENT TARGET QUOTE")
    #                         pp.pprint(target_quote)
    #                     else:
    #                         got_something = 1
    #             c += got_something
    # print("TOTAL NUMBER OF TESTED QUOTES",len(quotes1.keys()))
    # print("IDENTICAL QUOTES",c)

#filea = "/mnt/output/tib/json_unfiltered/T06TD4021E.json"
#fileb = "/mnt/output/tib/json_unfiltered/T06TD4027E.json"



filea = "/mnt/output/tib/tab/folder6/T06TD4021E-9.json.gz"
fileb = "/mnt/output/tib/tab/folder9/T06TD4027E-6.json.gz"

check_files(filea,fileb)
