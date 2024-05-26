from preprocessor import *
from third_party.defextract import func_defextractor # ctags required
from pprint import pprint

if __name__ == "__main__":
    out_put = func_defextractor(r"../test_code")
    print(out_put)
    pprint(out_put.to_dict())
