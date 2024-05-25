from preprocessor import *
from functiondefextractor import core_extractor # ctags required
from pprint import pprint

if __name__ == "__main__":
    out_put = core_extractor.extractor(r"../test_code")
    pprint(out_put.to_dict())