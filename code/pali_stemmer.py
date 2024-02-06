from pathlib import Path
import sentencepiece as spm
import pandas as pd
from tqdm import tqdm
import shutil
from utils.constants import *

import re


def clean_pali(string):  # TODO: should be loaded from paltok sooner or later
    if type(string) != str:
        print(f"Pali cleaner: non-str input: {string}")
        return ""
    html_tags = re.compile("<.*?>")
    string = string.lower()
    string = re.sub(html_tags, "", string)
    string = re.sub(
        r'[0-9!"#$%&()*+,-./:;<=>?@[\]^_`{|}~\']', "", string
    )  # ascii digits and punctuation
    string = re.sub(r"[\t\n\r\x0b\x0c]", " ", string)  # whitespaces apart from " "
    string = re.sub(r"[ṅṁ]", "ṃ", string)  # whitespaces apart from " "
    string = re.sub(r"[”ऐạै–…‘“’\\ौऋ—औ]", "", string)
    string = string.strip()
    return string


class LanguageNotSupported(Exception):
    pass


class Stemmer:
    """
    tsv(segmentId, orig-text) --> tsv(segmentId, orig-text, tokenized-text)
    the output dir is by default is created in the parent dir of the input dir
    the output tsv files have a header and do not have empty entries
    """

    def __init__(
        self,
        lang: str,
        spm_model_abspath,
        input_dir: str,
        output_dir: str = None,
        archive=False,
        sep="\t",
        resume_mode=True,
        drop_empty=True,
    ) -> None:
        self.lang: str = lang
        self.spm_model_abspath = spm_model_abspath
        self.src_dir: Path = self.init_src_dir(input_dir)
        self.resume_mode = resume_mode
        self.file_paths: list[Path] = self.init_file_paths()
        self.tokenizer = self.set_tokenizer()
        self.output_dir: Path = self.make_dest_dir(output_dir)
        self.done_paths = list(self.output_dir.rglob("*" + DIR_NAME_STEMMED))
        self.cleaner = self.init_cleaner()
        self.sep = sep
        self.archive = archive
        self.drop_empty = drop_empty

    class TextFile:
        def __init__(self, stemmer, src_path) -> None:
            self.src_path = src_path
            self.dest_path = Path(stemmer.dest_dirs / (src_path.stem + EXTENTION_STEMMED))

    def set_tokenizer(self):
        match self.lang:
            case "pli":
                return spm.SentencePieceProcessor(
                    model_file=self.spm_model_abspath
                )  # TODO: get model
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

    def make_dest_dir(self, output_dir) -> None:
        if output_dir:
            return output_dir
        else:
            dest_dir = self.src_dir.parent / DIR_NAME_STEMMED
            dest_dir.mkdir(exist_ok=True)
            return dest_dir

    def process_src_dir(self):
        for file_path in tqdm(self.file_paths):
            self.process_file(file_path)
        if self.archive:
            print("Zipping")
            shutil.make_archive(
                base_name=str(self.output_dir),
                format="zip",
                root_dir=self.output_dir.parent,
                base_dir=self.output_dir,
            )

    def stem_segment(self, segment):
        token_list = self.tokenizer.encode(self.cleaner(segment), out_type=str)
        return " ".join(token_list)

    def process_file(self, file_path):
        dest_file_path = Path(
            self.output_dir / (file_path.stem + EXTENTION_STEMMED)
        )
        if self.resume_mode and dest_file_path in self.done_paths:
            print(
                f"Skipping {file_path.stem} as it has already been processed (resume mode active)"
            )
            return
        df = self.file2df(file_path)
        df.to_csv(dest_file_path,
                    sep="\t",
                    header=True,
                    index=False
                )
        return df  # for testing

    def file2df(self, file_path):
        df = pd.read_csv(
            file_path,
            sep=self.sep,
            header=None,
            names=[TSV_COL_SEGMENTNR, TSV_COL_ORIGINAL, TSV_COL_STEMMED],
            on_bad_lines="skip",
        ).astype(str)
        df[TSV_COL_STEMMED] = [
            self.stem_segment(seg) for seg in df[TSV_COL_ORIGINAL].tolist()
        ]
        if self.drop_empty:  # Lines: before: 2_886_152. after: 2_849_001
            df = df[df[TSV_COL_ORIGINAL] != ""]
            df = df[df[TSV_COL_STEMMED] != ""]
        return df
