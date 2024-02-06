from pathlib import Path
import sentencepiece as spm
import pandas as pd
from tqdm import tqdm

import re
def clean_pali(string): # TODO: should be loaded from paltok sooner or later
    if type(string) != str:
        print(f"Pali cleaner: non-str input: {string}")
        return ""
    html_tags = re.compile('<.*?>')
    string = string.lower()
    string = re.sub(html_tags, "", string)
    string = re.sub(r'[0-9!"#$%&()*+,-./:;<=>?@[\]^_`{|}~\']',"", string) # ascii digits and punctuation
    string = re.sub(r'[\t\n\r\x0b\x0c]'," ", string) # whitespaces apart from " "
    string = re.sub(r'[ṅṁ]',"ṃ", string) # whitespaces apart from " "
    string = re.sub(r'[”ऐạै–…‘“’\\ौऋ—औ]',"", string)
    string = string.strip()
    return string

class LanguageNotSupported(Exception):
    pass

class Stemmer:
        drop_empty=True,
    ) -> None:
        self.lang: str = lang
        self.src_dir: Path = self.init_src_dir(input_path)
        self.resume_mode = resume_mode
        self.file_paths: list[Path] = self.init_file_paths()
        self.tokenizer = self.set_tokenizer()
        self.dest_dir: Path = self.make_dest_dir()
        self.done_paths = list(self.dest_dir.rglob("*.stemmed.tsv"))
        self.cleaner = self.init_cleaner()
        self.sep = sep
        self.drop_empty = drop_empty

    class TextFile:
        def __init__(self, stemmer, src_path) -> None:
            self.src_path = src_path
            self.dest_path = Path(stemmer.dest_dirs / (src_path.stem + ".stemmed.tsv"))

    def set_tokenizer(self):
        match self.lang:
            case "pli":
                return spm.SentencePieceProcessor(model_file='ref/pali_spm_2024-01-15.model')  # TODO: get model
            case other:
                raise LanguageNotSupported()

    def init_cleaner(self):
        match self.lang:
            case "pli":
                return clean_pali
            case other:
                raise LanguageNotSupported()

    def init_src_dir(self, input_path: str) -> Path:
        path = Path(input_path)
        if path.is_file():
            return path.parent
        elif path.is_dir():
            return path
        else:
            raise
        
    def init_file_paths(self) -> list[Path]:
        paths = list(self.src_dir.rglob("*.tsv"))
        print(f"Stemmer: found original files {len(paths)}")
        return paths

    def make_dest_dir(self) -> None:
        dest_dir = self.src_dir.parent / "stemmed-tsv"
        dest_dir.mkdir(exist_ok=True)
        return dest_dir

    def process_src_dir(self):
        for file_path in tqdm(self.file_paths):
            self.process_file(file_path)

    def stem_segment(self, segment):
        token_list = self.tokenizer.encode(self.cleaner(segment), out_type=str)
        return " ".join(token_list)

    def process_file(self, file_path):
        dest_file_path = Path(self.dest_dir / (file_path.stem + self.stemmed_extention))
        if self.resume_mode and dest_file_path in self.done_paths:
            print(f"Skipping {file_path.stem} as it has already been processed (resume mode active)")
            return
        df = self.file2df(file_path)
        df.to_csv(dest_file_path, sep="\t", header=False, index=False)
        return df # for testing

    def file2df(self, file_path):
        column_names = ["segmentId", "original_text"]
        df = pd.read_csv(
            file_path,
            sep=self.sep,
            header=None,
            names=column_names,
            on_bad_lines="skip",
        ).astype(str)
        if self.drop_empty:  # Lines: before: 2_886_152. after: 2_849_001
            df = df[df[TSV_COL_ORIGINAL] != ""]
            df = df[df[TSV_COL_STEMMED] != ""]
        return df