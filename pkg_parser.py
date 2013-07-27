#!/usr/bin/env python2

# This is a parser for bash-style variable assignments.
# It fully (?) supports the syntax w/o braces, the ${}-syntax
# is implemented very hackish. (There are also detailed
# TODO-comments in various places)

# This is meant for Archlinux' AUR to be used to parse
# PKGBUILD's properly.

# At the moment I have problems to find PKGBUILD's that are challenging
# for this script.

import re

reName = re.compile(r"([\w_][\w\d_]*)")
reAssignment = re.compile(r"([\w_][\w\d_]*)=")

def bashGlobToRegex(glob):
    # Reference: bash(1) "Pathname Expansion"
    # TODO:
    # * characater classes, equivalence classes, that other foo
    #   ( [:upper:], [=c=], [.symbol.]
    #   First should be easy to implement, python's regexes even have
    #   similar classes (\w, \W, \d, \D, \s, \S)
    #   Afaik, the first syntax is used rarely, the following two are
    #   used _never_. No urge to implement them. 
    # * extended globs:
    #   ( ?(pattern), *(pattern), +(pattern), etc...)
    #   Never seen someone use thiese, no urge to implement them.
    # * bash may have different handling of \:
    #   This code just ignores the following characters' special meaning
    #   and lets it match itself. Bash may evaluate e.g. "\a" as "\a"
    #   and not as "a". (But both should eval "\*" as "*".)
    #   UPDATE: This should now be solved. But it was done with magic.
    
    res = ""
    ptr = 0
    while ptr < len(glob):
        if glob[ptr] == "\\":
            ptr += 1
            res += re.escape(glob[ptr])
        elif glob[ptr] == "*":
            res += ".*?"
        elif glob[ptr] == "?":
            res += "."
        elif glob[ptr] == "[":
            ptr += 1
            res += "["
            if glob[ptr] == "^" or glob[ptr] == "!":
                res += "^"
                ptr += 1
            if glob[ptr] == "]":
                res += "]"
                ptr += 1
            if glob[ptr-1] in "[^!" and glob[ptr] == "\\":
                ptr += 1
            while glob[ptr] != "]":
                if glob[ptr] == "\\" and glob[ptr+1] in "wsdbaWSDBAZ":
                    res += "\\"
                res += glob[ptr]
                ptr += 1
            res += "]"
        else:
            res += re.escape(glob[ptr])
        ptr += 1
    return res

def expandParams(symbols, text):
    # Reference: bash(1) "Parameter Expansion"
    # Done:
    # * ${foo}
    # * ${foo/glob/substitute}
    #
    # Not done:
    # * all other syntaxes
    # * support for arrays will not be needed
    # * support for 2nd-level indirection will not be needed
    #   ( foo="bar"; bar="baz"; ${!foo} -> "baz" )
    
    res = ""
    ptr = 0
    while ptr < len(text):
        if text[ptr] == "\\":
            ptr += 1
        elif text[ptr] == "$":
            ptr += 1
            
            # are there braces?
            if text[ptr] == "{":
                ptr += 1
                name = reName.match(text, ptr)
                ptr = name.end()
                
                if text[ptr] == "/":
                    # Pattern substitution
                    # ${parameter/pattern/string}
                    
                    ptr += 1
                    
                    # check if all occurences should be substituted
                    suball = False
                    if text[ptr] == "/":
                        suball = True
                        ptr += 1
                    
                    # fetch the pattern
                    pattern = ""
                    while text[ptr] != "/" and text[ptr] != "}":
                        if text[ptr] == "\\" and text[ptr+1] in "\\}/":
                            ptr += 1
                        pattern += text[ptr]
                        ptr += 1
                    
                    # fetch the substitute
                    substitute = ""
                    if text[ptr] != "}": # there might be no substitute
                        ptr += 1
                        while text[ptr] != "}":
                            if text[ptr] == "\\":
                                ptr += 1
                            substitute += text[ptr]
                            ptr += 1
                    
                    if pattern.startswith("#"):
                        align = 1
                        pattern = pattern[1:]
                    elif pattern.startswith("\\#"):
                        pattern = pattern[1:]
                    elif pattern.endswith("%%"):
                        align = 2
                        pattern = pattern[:-1]
                    elif pattern.endswith("\\%%"):
                        pattern = pattern[:-1]
                    else:
                        align = 0
                    regex = ((align == 1 and "^" or "") +
                            bashGlobToRegex(pattern) +
                            (align == 2 and "$" or ""))
                    
                    res += re.sub(regex, substitute,
                        symbols.get(name.group(1), ""),
                        0 if suball else 1)
                else:
                    # 'normal' expansion
                    res += symbols.get(name.group(1), "")
            else:
                name = reName.match(text, ptr)
                res += symbols.get(name.group(1), "")
                ptr = name.end()
        else:
            res += text[ptr]
        ptr += 1
    return res

def parseStr(symbols, line, ptr):
    # TODO:
    # * This does not parse escapes
    res = ""
    if line[ptr] == "'":
        ptr += 1
        while line[ptr] != "'":
            res += line[ptr]
            ptr += 1
        ptr += 1
    elif line[ptr] == '"':
        ptr += 1
        while line[ptr] != '"':
            res += line[ptr]
            ptr += 1
        res = expandParams(symbols, res)
        ptr += 1
    else:
        while (len(line) > ptr) and (not line[ptr] in " \t)"):
            res += line[ptr]
            ptr += 1
        res = expandParams(symbols, res)
    return ptr, res

def parseFile(fileh):
    # TODO:
    # * Lines are not parsed like they should be.
    #   This is very unlikely to break the variable assignments
    #   at the begining of the file, but will break if a 'string'
    #   spanning multiple lines is encountered and it uses \ at the end
    #   of the line (e.g. a bash script in a bash script)
    lines = [""]

    for line in fileh:
        line = line[:-1]
        if not line: continue
        lines[-1] += line
        if line[-1] != "\\":
           lines.append("")
    
    symbols = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        
        assignment = reAssignment.match(line)
        if not assignment:
            continue
        ptr = assignment.end()
        
        # the parser relys on proper syntax. syntax errors are
        # catched here
        try:
            if line[ptr] == "(":
                symbols[assignment.group(1)] = []
                ptr += 1
                while True:
                    while (ptr < len(line)) and (line[ptr] != ")"):
                        if not line[ptr] in " \t":
                            ptr, val = parseStr(symbols, line, ptr)
                            symbols[assignment.group(1)].append(val)
                        else:
                            ptr += 1
                    if (ptr < len(line)) and (line[ptr] == ")"): break
                    if len(lines) == i: break
                    line = lines[i]
                    i += 1
                    ptr = 0
            else:
                ptr, symbols[assignment.group(1)] = parseStr(
                    symbols, line, ptr)
        except IndexError:
            print >> sys.stderr, "Syntax error, continuing"
            continue
    return symbols

if __name__ == '__main__':
    import sys
    
    class cooldict(dict):
        def __init__(self, foo):
            self.foo = foo
        def __getitem__(self, key):
            res = self.foo.get(key, "(missing)")
            if hasattr(res, 'sort'):
                res = ', '.join(res)
            return res
    
    if len(sys.argv) < 2:
        print "Usage: %s <filename or '-'>"%(sys.argv[0])
        exit(1)
    
    res = cooldict(parseFile(
        open(sys.argv[1]) if sys.argv[1] != "-" else sys.stdin))
    print """%(pkgname)s %(pkgver)s
%(pkgdesc)s

Licenses: %(license)s
Architectures: %(arch)s

Dependencies: %(depends)s
    for make: %(makedepends)s

Source: %(source)s"""%res
