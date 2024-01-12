from pathlib import Path
from random import randint

class TextFile:
    def __init__(self, lang, path: Path):
        self.lang = lang
        self.path: Path = path
        self.name: str = path.stem
        self.segments_df = None # Pandas DataFrame
        self.words_df = None # Pandas DataFrame
        self.tags = [] # could be decoded from the file name

class FileMngr:
    def __init__(self,
                 n_buckets,
                 input_dir, 
                 input_extention,
                 output_dir,
                 output_extention,
                 ) -> None:
        self.n_buckets = n_buckets
        self.input_dir: Path = self.init_input_dir(input_dir)
        self.input_extention = input_extention
        self.output_dir = output_dir
        self.output_extention = output_extention
        self.file_paths: list[Path] = self.find_files_by_extention(self.input_extention)
        print(f"Vectorizer: {len(self.file_paths)} input files found")
        self.dest_dir: Path = self.make_dest_dir()
        self.done_paths = self.find_files_by_extention(self.output_dir)
        print(f"Vectorizer: {len(self.file_paths)} processed files found")

    def init_input_dir(self, input_dir: str) -> Path:
        path = Path(input_dir)
        if path.is_file():
            return path.parent
        elif path.is_dir():
            return path
        else:
            raise FileNotFoundError
        
    def find_files_by_extention(self, extention) -> list[Path]:
        result = list(self.input_dir.rglob("*" + extention)) # "*.csv"
        return result

    def make_dest_dir(self) -> None:
        dest_dir = self.input_dir.parent / self.output_dir
        dest_dir.mkdir(exist_ok=True)
        return dest_dir

    def pickle_text(self, TextFile_obj):
        save_dir = self.file_mngr.dest_dir
        if self.n_buckets > 0:
            save_dir /= "bucket_" + str(randint(1, self.n_buckets))
        TextFile_obj.df.to_pickle(save_dir / TextFile_obj.name + self.file_mngr.out)
