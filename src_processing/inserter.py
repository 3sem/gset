def insert_pragma(file_path, line_number, pragma_directive):
    with open(file_path, 'r') as file:
        lines = file.readlines()

    if line_number > len(lines):
        print("Line number out of range.")
        return

    lines.insert(line_number - 1, f"{pragma_directive}\n")

    with open(file_path, 'w') as file:
        file.writelines(lines)


def emit_pragma_from_class(func_class):
    return "#pragma "


# Example usage:
def process_file(file_path, classified_code_lines: list):
    for line_number, code_class in classified_code_lines.items():
        pragma_directive = emit_pragma_from_class(code_class)
        insert_pragma(file_path, line_number, pragma_directive)


def detect_code_snippets(fn, detector=None):
    with open(fn, 'r') as f:
        if detector is None:
            return {}
        else:
            return detector(f.readlines())


if __name__ == '__main__':
    # Example usage  
    process_file("1.c", detect_code_snippets("1.c"))
