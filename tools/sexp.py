"""Minimal KiCad s-expression parse/serialise + symbol library resolver."""
import re, os

def _find_symbol_dir():
    """Locate KiCad's stock symbol libraries.

    Override with KICAD_SYMBOL_DIR if yours live somewhere unusual."""
    env = os.environ.get('KICAD_SYMBOL_DIR')
    if env:
        return env.rstrip('/') + '/'
    candidates = [
        '/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols/',   # macOS
        '/usr/share/kicad/symbols/',                                        # Linux
        '/usr/local/share/kicad/symbols/',
        'C:/Program Files/KiCad/9.0/share/kicad/symbols/',                  # Windows
    ]
    for c in candidates:
        if os.path.isdir(c):
            return c
    raise RuntimeError(
        'Could not find KiCad symbol libraries. Set KICAD_SYMBOL_DIR to the folder '
        'containing Device.kicad_sym (looked in: %s)' % ', '.join(candidates))

SYMDIR = _find_symbol_dir()

class Q(str):
    """A quoted string atom."""
    pass

def tokenize(s):
    out=[]; i=0; n=len(s)
    while i<n:
        c=s[i]
        if c=='"':
            j=i+1; buf=[]
            while True:
                if s[j]=='\\':
                    buf.append(s[j+1]); j+=2; continue
                if s[j]=='"': break
                buf.append(s[j]); j+=1
            out.append(Q(''.join(buf))); i=j+1
        elif c in '()':
            out.append(c); i+=1
        elif c.isspace():
            i+=1
        else:
            j=i
            while j<n and not s[j].isspace() and s[j] not in '()"': j+=1
            out.append(s[i:j]); i=j
    return out

def parse_one(t,i=0):
    if t[i]=='(':
        i+=1; node=[]
        while t[i]!=')':
            sub,i = parse_one(t,i); node.append(sub)
        return node, i+1
    return t[i], i+1

def dumps(node, indent=0):
    if not isinstance(node,list):
        if isinstance(node,Q):
            return '"'+str(node).replace('\\','\\\\').replace('"','\\"')+'"'
        return str(node)
    parts=[dumps(c) for c in node]
    return '('+' '.join(parts)+')'

def _extract_block(txt, header):
    k = txt.index(header); depth=0; j=k
    while True:
        if txt[j]=='(': depth+=1
        elif txt[j]==')':
            depth-=1
            if depth==0: break
        j+=1
    return txt[k:j+1]

_libcache={}
def load_lib(lib):
    if lib not in _libcache:
        _libcache[lib]=open(SYMDIR+lib+'.kicad_sym').read()
    return _libcache[lib]

def get(node,key):
    for c in node:
        if isinstance(c,list) and c and c[0]==key: return c
    return None

def getall(node,key):
    return [c for c in node if isinstance(c,list) and c and c[0]==key]

def resolve_symbol(lib, name):
    """Return a flattened (symbol "lib:name" ...) node ready for lib_symbols."""
    txt = load_lib(lib)
    blk = _extract_block(txt, '(symbol "%s"'%name)
    node,_ = parse_one(tokenize(blk))
    ext = get(node,'extends')
    if ext:
        parent = resolve_symbol(lib, str(ext[1]))
        # child keeps its own properties; inherit parent's graphics/pin sub-symbols
        child_props = {str(p[1]): p for p in getall(node,'property')}
        merged = [node[0], Q('%s:%s'%(lib,name))]
        for c in parent[2:]:
            if isinstance(c,list) and c[0]=='property':
                key=str(c[1])
                merged.append(child_props.pop(key, c))
            elif isinstance(c,list) and c[0]=='symbol':
                sub=list(c)
                sub[1]=Q(str(c[1]).replace(str(ext[1]), name, 1))
                merged.append(sub)
            else:
                merged.append(c)
        for p in child_props.values(): merged.append(p)
        return merged
    node=list(node)
    node[1]=Q('%s:%s'%(lib,name))
    return node

def symbol_pins(sym):
    """{unit: {pinnum: (x,y,angle,name,etype)}} from a resolved symbol."""
    res={}
    for sub in getall(sym,'symbol'):
        m=re.search(r'_(\d+)_(\d+)$', str(sub[1]))
        if not m: continue
        unit=int(m.group(1))
        for pin in getall(sub,'pin'):
            at=get(pin,'at'); num=get(pin,'number'); nm=get(pin,'name')
            etype=pin[1] if len(pin)>1 and not isinstance(pin[1],list) else 'passive'
            res.setdefault(unit,{})[str(num[1])]=(float(at[1]),float(at[2]),float(at[3]),str(nm[1]),str(etype))
    return res
