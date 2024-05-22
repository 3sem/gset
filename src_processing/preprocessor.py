import shutil
import re
import os
from pprint import pprint
from glob import glob

import subprocess
from pycparser import c_ast, parse_file, c_parser

functions = list()


class FuncSignCollectVisitor(c_ast.NodeVisitor):
    def visit_FuncDef(self, node):
        print('%s at %s' % (node.decl.name, node.decl.coord))
        func_ret_type = node.decl.type.type.type.names[0]
        func_name = node.decl.name
        try:
            func_arguments = [(x.name, x.type.type.names[0]) for x in node.decl.type.args.params]
        except AttributeError:
            func_arguments = []
        functions.append({
            'name': func_name,
            'ret_type': func_ret_type,
            'args': func_arguments,
            'text_repr': func_ret_type + " " + func_name + '(' + ", ".join(a[0] + a[1] for a in func_arguments) + ');'
        }
        )


def traversal_func_defs_from_file(filename):
    ast = parse_file(filename, use_cpp=False,
                     cpp_args=r'-Iutils/fake_libc_include')

    v = FuncSignCollectVisitor()
    v.visit(ast)


def traversal_func_defs_from_text(text):
    parser = c_parser.CParser()
    ast = parser.parse(text, filename='<none>')
    v = FuncSignCollectVisitor()
    v.visit(ast)


def collect_fun_info(filename):
    functions.clear()
    traversal_func_defs_from_file(filename)
    return functions


def check_from_file(filepath=
                    '..' + os.sep + "test_code" + os.sep + "dir1" + os.sep + "2.c"):
    print(
        collect_fun_info(filename=filepath)
    )
    return functions


def check_from_text(text="int m() {int i; return i++;} int main() {return m();}"):
    functions.clear()
    traversal_func_defs_from_text(text)
    print(functions)
    return functions


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


def extract_filenames(directory, string, delimiters=' |\n|\t', pattern=r"*\.c"):
    """
    Extract filenames from benchmark
    """
    filenames = list()
    substrings = [p for p in re.split(delimiters, string) if p.endswith(".c")]
    for s in substrings:
        filenames += [r for r in glob(directory + os.sep + s)]
    return filenames


def create_benchmark_working_dir(benchmark, working_dir):
    if os.path.exists(working_dir):
        return
    os.makedirs(working_dir, exist_ok=True)
    shutil.copytree(benchmark.path, working_dir, dirs_exist_ok=True)


def evaluate_compiler_preprocessing(compiler_path, working_dir, whitelist=None, verbose=True):
    if verbose is True:
        print("Preprocessing starts on:", working_dir, "; Compiler path:", compiler_path)
    checklist = whitelist if whitelist is not None\
        else glob(pathname=os.path.join(working_dir, "**/*.c"), recursive=True)
    processed_names = list()
    processed_data = dict()

    for i, name in enumerate(checklist): # preprocess each file by gcc, remove #, comments, & save
        head, tail = os.path.split(name)
        imm_name = "preprocess_" + tail
        subprocess.run([compiler_path, "-E", name, "-o", os.path.join(head, imm_name)])
        processed_names.append(imm_name)
        full_path = os.path.join(head, imm_name)
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
                #prepr_src = [x.strip() for x in prepr_src]  # remove leading whitespaces / tabs
                return \
                    (orig_text, \
                    " ".join([x for x in prepr_src if not x.startswith("#")])) # remove directives, join and return

            original_text, preprocessed_text = preprocess_text(f)
            functions_def_info = check_from_text(preprocessed_text)
            processed_data[full_path] = {'src': original_text,'sign': functions_def_info}
            if verbose is True:
                print(f"Iteration {i} ends.\nGet info of {len(processed_data[full_path]['sign'])} functions")
            if os.path.exists(full_path):
                os.remove(full_path)
        if verbose is True:
            print("==RESULTS OF DATA PREPROCESSING:==")
            pprint(processed_data)
    return processed_data


def collect_functions_info(working_dir):
    pass