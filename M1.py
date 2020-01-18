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

TOK_TYPE_MACRO, TOK_TYPE_STR, TOK_TYPE_MACRO = range(1,3+1) # match M1-macro.c
TOK_TYPE, TOK_EXPR, TOK_FILENAME, TOK_LINENUM = range(4)
