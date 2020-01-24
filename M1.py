#!/usr/bin/env python
#
# A derivitive port of:
# https://github.com/oriansj/mescc-tools/M1-macro.c
#
# Copyright (C) 2016 Jeremiah Orians
# Copyright (C) 2017 Jan Nieuwenhuizen <janneke@gnu.org>
# Copyright (C) 2020 Mark Jenkins <mark@markjenkins.ca>
# This file is part of knightpies
#
# knightpies is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# knightpies is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with knightpies.  If not, see <http://www.gnu.org/licenses/>.

from pythoncompat import open_ascii, print_func, COMPAT_TRUE, COMPAT_FALSE

TOK_TYPE_ATOM, TOK_TYPE_STR, TOK_TYPE_NEWLINE = range(1,3+1) # match M1-macro.c
TOK_TYPE, TOK_EXPR, TOK_FILENAME, TOK_LINENUM = range(4)

class MultipleDefinitionsException(Exception):
    pass

def read_atom(first_char, f):
    buf = first_char
    while True:
        c = f.read(1)
        if c in ('', "\n", "\t", " "):
            break
        else:
            buf += c
    return buf, c

def read_until_newline_or_EOF(f):
    while True:
        c = f.read(1)
        if c == '' or c=='\n':
            return c

def tokenize_file(f):
    line_num = 1
    string_char, string_buf = None, None
    while True:
        c = f.read(1)
        if c=='':
            if string_char != None:
                raise Exception("unmatched %s quote in %s line %s",
                                string_char, f.name, line_num)
            break
        # look for being in string stage first, as these are not
        # interupted by newline or comments
        elif (string_char != None):
            if string_char == c:
                yield (TOK_TYPE_STR, string_buf, f.name, line_num)
                string_char, string_buf = None, None
            else:
                string_buf += c
        elif c == '#' or c == ';':
            c = read_until_newline_or_EOF(f)
            if c!= '':
                yield (TOK_TYPE_NEWLINE, '\n', f.name, line_num)
                line_num+=1
            else:
                break
        elif (string_char == None) and (c == '"' or c == "'"):
            string_char = c
            string_buf  = ''
        elif c == '\n':
            yield (TOK_TYPE_NEWLINE, '\n', f.name, line_num)
            line_num+=1
        elif c == ' ' or c == '\t':
            pass
        else:
            atom, trailing_char = read_atom(c, f)
            yield (TOK_TYPE_ATOM, atom, f.name, line_num)
            if trailing_char == '':
                break
            elif trailing_char == '\n':
                yield (TOK_TYPE_NEWLINE, '\n', f.name, line_num)
                line_num+=1
                
    yield (TOK_TYPE_NEWLINE, '\n', f.name, line_num)

def get_symbols_used(file_objs, symbols):
    symbols_used = {}
    for f in file_objs:
        f.seek(0) # return to start of file
        next_atom_symbol = False
        for tok_type, tok_expr, tok_filename, tok_linenum in tokenize_file(f):
            if tok_type == TOK_TYPE_ATOM and tok_expr == 'DEFINE':
                next_atom_symbol = True
            elif tok_type == TOK_TYPE_ATOM and next_atom_symbol:
                next_atom_symbol = False
            elif tok_type == TOK_TYPE_ATOM and tok_expr in symbols:
                symbols_used[tok_expr] = None
    return list(symbols_used.keys())

def get_macros_defined_and_add_to_sym_table(f, symbols=None):
    # start a new dictionary if one wasn't, putting this in the function
    # definition would cause there to be one dictionary at build time
    #
    # we're using a dictionary as a backwards compatible set implementation
    if symbols == None:
        symbols = {}

    next_atom_symbol = COMPAT_FALSE
    for tok_type, tok_expr, tok_filename, tok_linenum in tokenize_file(f):
        if tok_type == TOK_TYPE_ATOM:
            if next_atom_symbol:
                if tok_expr in symbols:
                    raise MultipleDefinitionsException(
                        "DEFINE %s on line %s of %s is a duplicate definition"
                        % (tok_expr, tok_linenum, tok_filename) )
                symbols[tok_expr] = None
                next_atom_symbol = COMPAT_FALSE
            elif tok_expr == 'DEFINE':
                next_atom_symbol = COMPAT_TRUE
    return symbols

def main():
    from sys import argv
    dump_defs_used = False
    arguments = []
    for arg in argv[1:]:
        if arg == '--dump-defs-used':
            dump_defs_used = True
        else:
            arguments.append(arg)

    symbols = {}
    file_objs = []
    # first pass get the symbols
    for filename in arguments:
        f = open_ascii(filename)
        file_objs.append(f)
        get_macros_defined_and_add_to_sym_table(f, symbols)

    if dump_defs_used:
        # second pass figure out which symbols are used
        symbols_used = get_symbols_used(file_objs, symbols)
        symbols_used.sort()
        for symbol in symbols_used:
            print_func(symbol)
    # this will be the default case, outputting a processed version of the file
    else:
        pass

    for f in file_objs:
        f.close()

if __name__ == '__main__':
    main()
