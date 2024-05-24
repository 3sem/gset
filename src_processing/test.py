from preprocessor import *
from functiondefextractor import core_extractor # ctags required


if __name__ == "__main__":
    out_put = core_extractor.extractor(r"../test_code")
    print(out_put)