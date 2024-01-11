from pathlib import Path

class FileMngr:
    def __init__(self,
                 input_path, 
                 output_dir,
                 output_extention) -> None:
        self.file_paths: list[Path] = self.find_files_by_extention()
        self.dest_dir: Path = self.make_dest_dir()
        self.done_paths = self.find_files_by_extention()
        self.src_dir: Path = FileMngr.init_src_dir(input_path)

    def init_src_dir(self, input_path: str, resume_mode=True) -> Path:
        path = Path(input_path)
        if path.is_file():
            return path.parent
        elif path.is_dir():
            return path
        else:
            raise
        
    def find_files_by_extention(self, extention) -> list[Path]:
        return list(self.src_dir.rglob(extention)) # "*.csv"

    def make_dest_dir(self, root_dir, output_dir: str) -> None:
        dest_dir = root_dir / output_dir
        dest_dir.mkdir(exist_ok=True)
        return dest_dir
