import os
from pycparser import c_ast, parse_file


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
        })


def show_func_defs(filename):
    ast = parse_file(filename, use_cpp=False,
                     cpp_args=r'-Iutils/fake_libc_include')

    v = FuncSignCollectVisitor()
    v.visit(ast)


if __name__ == "__main__":
    filename = '..' + os.sep + "test_code" + os.sep +"dir1" + os.sep +"2.c"
    functions = []
    show_func_defs(filename)
    print(functions)