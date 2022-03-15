
stem-tibetan:
	invoke stem  --path "/home/basti/data/tibetan/txt-cropped/" --lang tib --threads 16

stem-sanskrit:
	invoke stem  --path "../data-kurt/" --lang skt --threads 16



create-vectors-tibetan:
	invoke create_vectorfiles --tsv_path "/home/basti/data/tibetan/txt-cropped/" --out_path "../tibetan-work/" --bucket_num 10 --lang "tib" --threads 16
