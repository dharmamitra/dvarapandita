LANGS = ["skt","tib","pli","chn"]

WINDOWSIZE = {"skt": 6,
              "tib": 7,
              "chn": 6,
              "pli": 5 }

THRESHOLD = {"skt": 0.03,
              "tib": 0.02,
              "chn": 0.1,#0.01, # 0.01 ist default
              "pli": 0.01 }

MIN_LENGTH = {"skt": 25,
              "tib": 11,
              "chn": 5,
              "pli": 30 }

QUERY_DEPTH = 100 # max. depth of the queries, when using 10 buckets 20 could be enough; without buckets, 100 is a good value 
MIN_DISTANCE = 500 # min. distance between the query token and the target token, in order to avoid that queries match with themselves 
TEXT_CHUNKSIZE=2000 # ? brauchen wir das? 



STOPWORDS_PATH = "ref/"
VECTOR_PATH = "ref/"

PUNC = "　 ！？｡。＂＃＄％＆＇（）＊＋，－／：；＜＝＞＠［＼］＾＿｀｛｜｝～｟｠｢｣､、〃》「」『』【】〔〕〖〗〘〙〚〛〜〝〞〟〰〾〿–—‘’‛“”„‟…‧﹏./.|*_"

LIST_OF_PP_CATEGORIES = ["K02","K03","K04","K05","K06","K07","T03"]

TIBETAN_STEMFILE="../data/verbinator_tabfile.txt"

EF_CONSTRUCTION = 40 # precision of the HNSW index, higher value = better precision, more computing time; 40 is a good tradeoff between speed and precision


