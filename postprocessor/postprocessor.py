import glob
import re
import os


def extract_filenames(directory, string, delimiters=' |\n|\t', pattern=r"*\.c"):
    """
    Extract filenames from benchmark
    """
    filenames = list()
    substrings = [p for p in re.split(delimiters, string) if p.endswith(".c")]
    for s in substrings:
        filenames += [r for r in glob.glob(directory + os.sep + s)]
    return filenames


