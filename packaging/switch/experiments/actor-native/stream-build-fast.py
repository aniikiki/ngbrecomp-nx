"""Use ARM load/store helpers in source, avoiding a function call before
every scalar guest access. This prototype only substitutes unambiguous
scalar stores. Validate outputs against the full compiler-observed journal."""
from pathlib import Path
h=Path(__file__).resolve().parent
# The compiler already emits write hooks for typed stores; inline them after
# the sanitizer pass so GCC can optimize calls knowing register clobbers.
# Remove only proven-empty read observer calls. All write hooks remain.
s=(h/'store-only.py').read_text().replace("d=p/'opt050/actor-store-only'","d=p/'opt050/actor-store-fast'")
i=s.index('asm.write_text(clean);')
s=s[:i]+'''# An aligned guest store is normally within the private map. The helper
# records and flushes a preceding pending store; tail-call elimination and a
# hot text section keep this part out of every unrelated guest basic block.
'''+s[i:];s=s.replace("s=s.replace(tag,new)","""s=s.replace(tag,new)
s=s.replace('static NOINST void observe_store(void*p,unsigned n)', 'static NOINST __attribute__((always_inline)) inline void observe_store(void*p,unsigned n)')
s=s.replace('static __attribute__((no_sanitize_thread)) void flush_store(void)', 'static __attribute__((always_inline,no_sanitize_thread)) inline void flush_store(void)')
""")
exec(compile(s,'fast-store-generator','exec'))
