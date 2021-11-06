MAIN_FOLDER="../"
#MAIN_FOLDER="/home/ftsx015/code/calculate-quotes/"

#WORK_FOLDER="/work/ftsx015/"
WORK_FOLDER="../../"


TIBETAN_WINDOWSIZE = 7
SANSKRIT_WINDOWSIZE = 6
CHINESE_WINDOWSIZE = 6
PALI_WINDOWSIZE = 5

SANSKRIT_THRESHOLD = 0.2
TIBETAN_THRESHOLD = 0.02 # war mal 0.025, das hat gut funktioniert...
CHINESE_THRESHOLD = 0.01
PALI_THRESHOLD = 0.01

SANSKRIT_MIN_LENGTH = 25
TIBETAN_MIN_LENGTH = 11
CHINESE_MIN_LENGTH = 5
PALI_MIN_LENGTH = 30

SANSKRIT_TSV_DATA_PATH = "../../data-jna/"

TIBETAN_TSV_DATA_PATH = WORK_FOLDER + "tib/tsv/"
TIBETAN_TSV_DATA_PATH = "/home/basti/data/tibetan/tsv-extract/"
CHINESE_TSV_DATA_PATH = "/home/basti/data/chinese/segmented-chinese/tsv/"
#CHINESE_TSV_DATA_PATH = WORK_FOLDER +  "chn/tsv/"


SANSKRIT_SEGMENT_DICT_PATH = MAIN_FOLDER + "data/sanskrit_segments.json"
TIBETAN_SEGMENT_DICT_PATH = MAIN_FOLDER + "data/segments/tibetan_segments.json.gz"
CHINESE_SEGMENT_DICT_PATH = MAIN_FOLDER + "data/segments/chinese_segments.json.gz"
PALI_SEGMENT_DICT_PATH = MAIN_FOLDER + "data/segments/pali_segments.json.gz"


SANSKRIT_DATA_PATH = WORK_FOLDER + "output/"

SANSKRIT_STOPWORDS = "../data/skt_stop.txt"
TIBETAN_STOPWORDS = MAIN_FOLDER + "data/tib_stop.txt"
TIBETAN_STOPWORDS_REDUCED = MAIN_FOLDER + "data/tib_stop_reduced.txt"
CHINESE_STOPWORDS = MAIN_FOLDER + "data/chn_stop.txt"
PALI_STOPWORDS = MAIN_FOLDER + "data/pali_stop.txt"


QUERY_DEPTH = 100

PUNC = "　 ！？｡。＂＃＄％＆＇（）＊＋，－／：；＜＝＞＠［＼］＾＿｀｛｜｝～｟｠｢｣､、〃》「」『』【】〔〕〖〗〘〙〚〛〜〝〞〟〰〾〿–—‘’‛“”„‟…‧﹏./.|*_"

LIST_OF_PP_CATEGORIES = ["K02","K03","K04","K05","K06","K07","T03"]
