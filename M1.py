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

TOK_TYPE_MACRO, TOK_TYPE_STR, TOK_TYPE_NEWLINE = range(1,3+1) # match M1-macro.c
TOK_TYPE, TOK_EXPR, TOK_FILENAME, TOK_LINENUM = range(4)

def read_until_newline_or_EOF(f):
    while True:
        c = f.read(1)
        if c == '' or '\n':
            break

def tokenize_file(f):
    line_num = 1
    while True:
        c = f.read(1)
        if c=='':
            yield (TOK_TYPE_NEWLINE, '\n', f.name, line_num)
        elif c == '\n':
            yield (TOK_TYPE_NEWLINE, '\n', f.name, line_num)
            line_num+=1
        elif c == ' ' or c == '\t':
            pass
        elif c == '#' or c == ';':
            read_until_newline_or_EOF(f)
            yield (TOK_TYPE_NEWLINE, '\n', f.name, line_num)

def main():
    from sys import argv
    f = open(argv[1])
    for tok in tokenize_file(f):
        print(repr(tok))
    f.close()

if __name__ == '__main__':
    main()
