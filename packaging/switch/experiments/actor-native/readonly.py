"""Scalar value loads only. Leave stores, address-taking, and parenthesized
lvalues on the original private path. Returned expressions are C rvalues:
a mistaken writable use must fail compilation rather than mutate shared RAM."""
import re
mem=re.compile(r'\bMEM(8|16|32|F|D)\(')
def loads(source):
    edits=[]
    for m in mem.finditer(source):
        i=m.end();depth=1
        while depth and i<len(source):
            depth+=(source[i]=='(')-(source[i]==')');i+=1
        if depth:raise ValueError("unclosed guest access")
        after=source[i:].lstrip().lstrip(')').lstrip()
        before=source[:m.start()].rstrip().rstrip('(').rstrip()
        if re.match(r'(?:[+\-*/%&|^<>]*=(?!=)|\+\+|--)',after) or before.endswith(('&','++','--')):continue
        edits.append((m.start(),m.end()-1,'ACTOR_R'+m[1]))
    for a,b,r in reversed(edits):source=source[:a]+r+source[b:]
    return source
