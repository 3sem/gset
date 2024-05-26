from functiondefextractor.core_extractor import *
import os
import time


def func_defextractor(path_loc, annot=None, delta=None, functionstartwith=None, report_folder=None, exclude=None):
    """
        Modified version of core_extractor.extract function from functiondefextractor project [2019-2024]
         https://github.com/philips-software/functiondefextractor
        Function that initiates the overall process of extracting function/method definitions from the files
        @parameters
        path_loc: directory path of the repository
        annot: given annotation condition (Ex: @staticmethod, @Test)
        delta: Required lines from method
        @return
        This function returns a data frame which contains the function/method names and body
        of the processed input files
        @usage
        function_def_extractor(path to repo, "@test")
        the above function call initiates the process to run function definition extraction on
        all files with @test annotation of the repository given """
    start = time.time()
    if isinstance(initialize_values(delta, annot, path_loc, report_folder), str):  # pylint: disable=R1705
        return initialize_values(delta, annot, path_loc, report_folder)
    else:
        report_folder, annot = initialize_values(delta, annot, path_loc, report_folder)
    code_list = []
    for func_name in filter_files(filter_reg_files(get_file_names(path_loc), exclude)):
        LOG.info("Extracting %s", func_name)  # pragma: no mutate
        if delta is not None:
            get_delta_lines(func_name, annot, delta)
        else:
            functions, line_num = get_function_names(func_name)
            if os.path.splitext(func_name)[1].upper() == ".PY":
                code_list = process_py_files(code_list, line_num, func_name, annot, functionstartwith)
            else:
                code_list = process_input_files(line_num, functions, annot, func_name, code_list, functionstartwith)
    end = time.time()
    LOG.info("Extraction process took %s minutes", round((end - start) / 60, 3))  # pragma: no mutate
    LOG.info("%s vaild files has been analysed",  # pragma: no mutate
             len(filter_files(filter_reg_files(get_file_names(path_loc), exclude))))  # pragma: no mutate
    return get_final_dataframe(delta, code_list)