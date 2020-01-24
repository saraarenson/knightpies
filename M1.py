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

from __future__ import generators # for yield keyword in python 2.2

from pythoncompat import \
    open_ascii, print_func, COMPAT_TRUE, COMPAT_FALSE

TOK_TYPE_ATOM, TOK_TYPE_STR, TOK_TYPE_NEWLINE = range(1,3+1) # match M1-macro.c
TOK_TYPE, TOK_EXPR, TOK_FILENAME, TOK_LINENUM = range(4)

class MultipleDefinitionsException(Exception):
    pass

def read_atom(first_char, f):
    buf = first_char
    while COMPAT_TRUE:
        c = f.read(1)
        if c in ('', "\n", "\t", " "):
            break
        else:
            buf += c
    return buf, c

def read_until_newline_or_EOF(f):
    while COMPAT_TRUE:
        c = f.read(1)
        if c == '' or c=='\n':
            return c

def tokenize_file(f):
    line_num = 1
    string_char, string_buf = None, None
    while COMPAT_TRUE:
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
        next_atom_symbol = COMPAT_FALSE
        for tok_type, tok_expr, tok_filename, tok_linenum in tokenize_file(f):
            if tok_type == TOK_TYPE_ATOM and tok_expr == 'DEFINE':
                next_atom_symbol = COMPAT_TRUE
            elif tok_type == TOK_TYPE_ATOM and next_atom_symbol:
                next_atom_symbol = COMPAT_FALSE
            elif tok_type == TOK_TYPE_ATOM and tok_expr in symbols:
                symbols_used[tok_expr] = None
    return list(symbols_used.keys())

def process_string_token_as_macro_value(string_expr):
    return ''.join(
        '%.2x' % ord(c)
        for c in
        string_expr[1:-1] # remove leading and trailing quote chars
    ) # join

def get_macros_defined_and_add_to_sym_table(f, symbols=None):
    # start a new dictionary if one wasn't provided, putting this in the
    # function definition would cause there to be one dictionary at build time
    if symbols == None:
        symbols = {}

    next_atom_symbol = COMPAT_FALSE
    next_atom_macro_value = COMPAT_FALSE
    for tok_type, tok_expr, tok_filename, tok_linenum in tokenize_file(f):
        if tok_type == TOK_TYPE_ATOM:
            if next_atom_symbol:
                assert not next_atom_macro_value
                if tok_expr in symbols:
                    raise MultipleDefinitionsException(
                        "DEFINE %s on line %s of %s is a duplicate definition"
                        % (tok_expr, tok_linenum, tok_filename) )
                symbols[tok_expr] = None
                last_symbol = tok_expr
                next_atom_symbol = COMPAT_FALSE
                next_atom_macro_value = COMPAT_TRUE
                # assert not next_atom_symbol # redundant assertion/
            elif next_atom_macro_value:
                symbols[last_symbol] = tok_expr
                next_atom_macro_value = COMPAT_FALSE
                assert not next_atom_symbol
            elif tok_expr == 'DEFINE':
                next_atom_symbol = COMPAT_TRUE
                assert not next_atom_macro_value
        elif tok_type == TOK_TYPE_STR:
            if next_atom_symbol:
                raise Exception(
                    "Using a string for macro name %s not supported "
                    "line %s from %s" % (tok_expr, tok_linenum, tok_filename)
                )
            elif next_atom_macro_value:
                symbols[last_symbol] = process_string_token_as_macro_value(
                    tok_expr)
                next_atom_macro_value = COMPAT_FALSE
                # redundant assertion. See if next_atom_symbol statement above
                # assert not next_atom_symbol

    # if the file ends with just DEFINE, that's a problem
    if next_atom_symbol:
        assert not next_atom_macro_value
        raise Exception(
            "%s ended with uncompleted DEFINE" % tok_filename
        )
    # if the file ends with DEFINE, a macro name, but no value
    elif next_atom_macro_value:
        raise Exception(
            "%s ended with uncompleted DEFINE" % tok_filename
        )
    return symbols

def filter_define_out_from_token_stream(input_tokens):
    # yuck, there's a better way to do this with next() for look ahead
    # and catching StopIteration
    # should rewrite the stream to have TOK_TYPE_DEFINE as a replacement
    # for three original ATOM tokens
    next_atom_symbol = COMPAT_FALSE
    next_atom_macro_value = COMPAT_FALSE    
    for tok in input_tokens:
        tok_type, tok_expr, tok_filename, tok_linenum = tok
        if tok_type == TOK_TYPE_ATOM:
            if next_atom_symbol:
                assert not next_atom_macro_value
                next_atom_symbol = COMPAT_FALSE
                next_atom_macro_value = COMPAT_TRUE
            elif next_atom_macro_value:
                assert not next_atom_symbol
                next_atom_macro_value = COMPAT_FALSE
            elif tok_expr == 'DEFINE':
                next_atom_symbol = COMPAT_TRUE
                assert not next_atom_macro_value
            else:
                yield tok
        else:
            assert not next_atom_symbol
            assert not next_atom_macro_value
            yield tok

def process_and_output_string_expr(output_file, string_expr):
    # remove leading and trailing quote chars
    for c in string_expr[1:-1]:
        output_file.write("%.2x" % ord(c))

def output_regular_atom(output_file, atomstr):
    if atomstr[0:2] == '0x': # atom's prefixed with 0x are hex
        hexatom = atomstr[2:]
        hexatom_list = list(reversed(hexatom))
        a = int(''.join(hexatom_list), 16) # endianness of this needs a look
        output_file.write('%.4x' % a) # endianness of this needs a look
    elif atomstr[0] in (':', '@'):
        output_file.write(atomstr)
    else:
        # other regular atoms are treated as decimal values
        output_file.write( '%.2x' % int(atomstr) )
        
def output_file_from_tokens_with_macros_sub_and_string_sub(
    input_tokens, output_file, symbols):

    for tok_type, tok_expr, tok_filename, tok_linenum in \
        filter_define_out_from_token_stream(input_tokens):
        if tok_type == TOK_TYPE_ATOM:
            assert tok_expr != "DEFINE" # these have been filtered
            # fixme, whitespace not needed if last thing out was newline
            output_file.write(' ')
            if tok_expr in symbols: # exact match only
                output_file.write(' ')
                output_file.write(symbols[tok_expr])
            else:
                output_regular_atom(output_file, tok_expr)
        elif tok_type == TOK_TYPE_NEWLINE:
            output_file.write('\n')
        else: # token_type == TOK_TYPE_STR
            process_and_output_string_expr(
                binary_output_file, tok_expr
                )

def main():
    from sys import argv, stdout
    dump_defs_used = COMPAT_FALSE
    arguments = []
    for arg in argv[1:]:
        if arg == '--dump-defs-used':
            dump_defs_used = COMPAT_TRUE
        else:
            arguments.append(arg)

    symbols = {}
    file_objs = []
    # first pass get the symbols
    for filename in arguments:
        f = open_ascii(filename)
        file_objs.append(f)
        get_macros_defined_and_add_to_sym_table(f, symbols)
        f.seek(0) # return to start of file for next pass

    if dump_defs_used:
        # second pass figure out which symbols are used
        symbols_used = get_symbols_used(file_objs, symbols)
        symbols_used.sort()
        for symbol in symbols_used:
            print_func(symbol)
    # this will be the default case, outputting a processed version of the file
    else:
        for f in file_objs:
            output_file_from_tokens_with_macros_sub_and_string_sub(
                tokenize_file(f), stdout, symbols)
                
    for f in file_objs:
        f.close()

if __name__ == '__main__':
    main()
