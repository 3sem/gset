import shutil
import re
import os
from pprint import pprint

from glob import glob
from src_processing.third_party.defextract import func_defextractor

functions = list()


def get_func_body(filename, line_num):
    """ Function to get method/function body from files
        @parameters
        filename, line_num: Path to the file, function/method line number
        @return
        This function returns function/method definitions of all the given files"""
    line_num = int(line_num)
    code = ""  # pragma: no mutate
    cnt_braket = 0
    found_start = False
    return_val = None
    with open(filename, "r", encoding='utf-8', errors='ignore') as files:  # pragma: no mutate
        for i, line in enumerate(files):
            if i >= (line_num - 1):
                code += line

                if line.count("{") > 0:
                    found_start = True
                    cnt_braket += line.count("{")

                if line.count("}") > 0:
                    cnt_braket -= line.count("}")

                if cnt_braket == 0 and found_start is True:
                    return_val = code
                    break
    return return_val


def substring_after(s, delim):
    return s.partition(delim)[2]


def substring_before(s, delim):
    return s.partition(delim)[0]


def canonize_string(s):
    return re.sub(r"[\n\t\s]*", "", s)


def collect_fun_info(filename):
    functions.clear()
    func_splitting = func_defextractor(os.path.split(filename)[0]).to_dict()
    fc = {substring_after(v, ".c_"): func_splitting['Code'][k]
          for k, v in func_splitting['Uniq ID'].items() if
          os.path.split(filename)[1].startswith(substring_before(os.path.split(v)[1])) }
    for i in range(len(functions)):
        functions[i]['code'] = fc[functions[i]['name']]

    return functions


def check_from_file(filepath=
                    '..' + os.sep + "test_code" + os.sep + "dir1" + os.sep + "2.c"):
    print(
        collect_fun_info(filename=filepath)
    )
    return functions


def check_from_text(func_splitting):
    fc = {substring_after(v, ".c_"):
              (func_splitting['Code'][k], {
               'name': substring_after(v, ".c_"),
               'ret_type':
                   substring_before(func_splitting['Code'][k].split('{')[0],
                                    substring_after(v, ".c_")),
               'args':
                   substring_after(func_splitting['Code'][k].split('{')[0],
                                   substring_after(v, ".c_")).split('(')[-1].split(')')[0],
               'code': None,  # code will be filled on the next steps
               'text_repr': func_splitting['Code'][k].split('{')[0] + ";"
               })
          for k, v in func_splitting['Uniq ID'].items()}
    return fc


def comment_remover(text):
    def replacer(match):
        s = match.group(0)
        if s.startswith('/'):
            return " " # note: a space and not an empty string
        else:
            return s
    pattern = re.compile(
        r'//.*?$|/\*.*?\*/|\'(?:\\.|[^\\\'])*\'|"(?:\\.|[^\\"])*"',
        re.DOTALL | re.MULTILINE
    )
    return re.sub(pattern, replacer, text)


def extract_filenames(base_dir, string=None, delimiters=' |\n|\t'):
    """
    Extract filenames from benchmark
    Arguments:
        base_dir -- benchmark base directory
        string -- if str, filenames enumerated in str, separated by any delimiter from 'delimiters';
            else None if each of *.c file should be processed
    return:
        tuple with list of src, list of includes
    """
    arguments = list()
    filenames = list() # src to compile
    includes = list() # include files
    if string is not None:
        substrings = [p for p in re.split(delimiters, string) if p.endswith(".c")]
        for s in substrings:
            filenames += [r for r in glob(base_dir + os.sep + s)]
        arguments = [p for p in re.split(delimiters, string) if (p.startswith("-") and not p.startswith("-I"))]
        includes = [p for p in re.split(delimiters, string) if p.startswith("-I")]
    else:
        filenames += glob(pathname=os.path.join(os.path.normpath(base_dir) + os.sep, "**/*.c"), recursive=True)
        includes += glob(pathname=os.path.join(os.path.normpath(base_dir) + os.sep, "**/*.h"), recursive=True)
    return filenames, includes, arguments


def chdir_build_string(string, base_dir, delimiters=' |\n|\t'):
    substrings = [p for p in re.split(delimiters, string)]
    for i in range(len(substrings)):
        if substrings[i].endswith(".c"):
            substrings[i] = os.path.join(base_dir, substrings[i])
        elif substrings[i].startswith("-I"):
            substrings[i] = "-I" + os.path.join(base_dir, substrings[i].lstrip("-I"))
    return " ".join(substrings)


def create_benchmark_working_dir(benchmark, working_dir):
    if os.path.exists(working_dir):
        return
    os.makedirs(working_dir, exist_ok=True)
    shutil.copytree(benchmark.path, working_dir, dirs_exist_ok=True)


def evaluate_compiler_preprocessing(compiler_path, working_dir, whitelist=None, verbose=True):
    if verbose is True:
        print("Preprocessing starts on:", working_dir, "; Compiler path:", compiler_path)
    checklist = whitelist[0] if whitelist is not None\
            else glob(pathname=os.path.join(working_dir, "**/*.c"), recursive=True)
    includes = whitelist[1] if whitelist is not None\
            else glob(pathname=os.path.join(working_dir, "**/*.h"), recursive=True) # may be improved
    arguments = whitelist[2] if whitelist is not None\
            else list()
    arguments = [a for a in arguments if not a.startswith("-o")]

    processed_data = dict()
    prev_head, _ = os.path.split(checklist[0])
    func_splitting = func_defextractor(prev_head).to_dict()

    for i, name in enumerate(checklist): # preprocess each file by gcc, remove #, comments, & save
        head, tail = os.path.split(name)
        if not prev_head == head: # update the information about functions in the dir
            prev_head = head

        full_path = os.path.join(head, name)
        print("FULLPATH", full_path)
        with open(full_path, "r") as f:
            def preprocess_text(f):
                if verbose is True:
                    print(f"\n[{i+1}/{len(checklist)}]", "Processing file:", full_path)
                prepr_text = f.read()
                orig_text = prepr_text
                with open(name,'r') as orig_src:
                    orig_text = orig_src.read()

                prepr_text = comment_remover(prepr_text)
                prepr_src = prepr_text.split("\n")

                return \
                    (orig_text, \
                    " ".join([x for x in prepr_src if not x.startswith("#")])) # remove directives, join and return

            original_text, preprocessed_text = preprocess_text(f)
            func_splitting = func_defextractor(prev_head).to_dict()
            functions_def_info = [v[1] for _, v in check_from_text(func_splitting).items()]
            processed_data[full_path] = {'src': original_text, 'sign': functions_def_info}

            fc = {substring_after(v, ".c_"): func_splitting['Code'][k]
                  for k, v in func_splitting['Uniq ID'].items()}

            for i, item in enumerate(processed_data[full_path]['sign']):
                print(f"We will process item:{item}")
                processed_data[full_path]['sign'][i]['code'] = fc[item['name']]

            if verbose is True:
                print(f"Iteration {i} ends.\nGet info of {len(processed_data[full_path]['sign'])} functions")

    if verbose is True:
        print("==RESULTS OF DATA PREPROCESSING:==")
        pprint(processed_data)
    return processed_data


def collect_functions_info(working_dir):
    pass