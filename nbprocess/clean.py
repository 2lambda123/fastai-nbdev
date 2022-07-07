# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/11_clean.ipynb.

# %% auto 0
__all__ = ['nbprocess_trust', 'clean_nb', 'wrapio', 'process_write', 'nbprocess_clean', 'nbprocess_install_hooks']

# %% ../nbs/11_clean.ipynb 2
import json,warnings,stat

from execnb.nbio import *
from fastcore.script import *
from fastcore.basics import *
from fastcore.imports import *
from fastcore.test import *

from .imports import *
from .read import *
from .sync import *
from .process import first_code_ln

# %% ../nbs/11_clean.ipynb 4
@call_parse
def nbprocess_trust(
    fname:str=None,  # A notebook name or glob to trust
    force_all:bool=False  # Trust even notebooks that havent changed
):
    "Trust notebooks matching `fname`"
    try: from nbformat.sign import NotebookNotary
    except:
        import warnings
        warnings.warn("Please install jupyter and try again")
        return

    fname = Path(fname if fname else config_key("nbs_path", '.'))
    path = fname if fname.is_dir() else fname.parent
    check_fname = path/".last_checked"
    last_checked = os.path.getmtime(check_fname) if check_fname.exists() else None
    nbs = globtastic(fname, file_glob='*.ipynb', skip_folder_re='^[_.]') if fname.is_dir() else [fname]
    for fn in nbs:
        if last_checked and not force_all:
            last_changed = os.path.getmtime(fn)
            if last_changed < last_checked: continue
        nb = read_nb(fn)
        if not NotebookNotary().check_signature(nb): NotebookNotary().sign(nb)
    check_fname.touch(exist_ok=True)

# %% ../nbs/11_clean.ipynb 6
def _clean_cell_output(cell):
    "Remove execution count in `cell`"
    if 'outputs' in cell:
        for o in cell['outputs']:
            if 'execution_count' in o: o['execution_count'] = None
            o.get('data',{}).pop("application/vnd.google.colaboratory.intrinsic+json", None)
            o.get('metadata', {}).pop('tags', None)

# %% ../nbs/11_clean.ipynb 7
def _clean_cell(cell, clear_all=False):
    "Clean `cell` by removing superfluous metadata or everything except the input if `clear_all`"
    if 'execution_count' in cell: cell['execution_count'] = None
    if 'outputs' in cell:
        if clear_all: cell['outputs'] = []
        else:         _clean_cell_output(cell)
    if cell['source'] == ['']: cell['source'] = []
    cell['metadata'] = {} if clear_all else {
        k:v for k,v in cell['metadata'].items() if k=="hide_input"}

# %% ../nbs/11_clean.ipynb 8
def clean_nb(nb, clear_all=False):
    "Clean `nb` from superfluous metadata"
    for c in nb['cells']: _clean_cell(c, clear_all=clear_all)
    nb['metadata'] = {k:v for k,v in nb['metadata'].items() if k in
                     ("kernelspec", "jekyll", "jupytext", "doc")}

# %% ../nbs/11_clean.ipynb 11
def wrapio(strm): return io.TextIOWrapper(strm.buffer, encoding='utf-8', line_buffering=True)

# %% ../nbs/11_clean.ipynb 12
def process_write(warn_msg, proc_nb, f_in, f_out=None, disp=False):
    if not f_out: f_out = wrapio(sys.stdout) if disp else f_in
    if isinstance(f_in, (str,Path)): f_in = Path(f_in).open()
    try:
        nb = json.load(f_in)
        proc_nb(nb)
        write_nb(nb, f_out)
    except Exception as e:
        warn(f'{warn_msg}')
        warn(e)

# %% ../nbs/11_clean.ipynb 13
@call_parse
def nbprocess_clean(
    fname:str=None, # A notebook name or glob to convert
    clear_all:bool=False, # Clean all metadata and outputs
    disp:bool=False,  # Print the cleaned outputs
    stdin:bool=False # Read input stream and not nb folder
):
    "Clean all notebooks in `fname` to avoid merge conflicts"
    # Git hooks will pass the notebooks in stdin
    _clean = partial(clean_nb, clear_all=clear_all)
    _write = partial(process_write, warn_msg='Failed to clean notebook', proc_nb=_clean)
    if stdin: _write(f_in=wrapio(sys.stdin), f_out=wrapio(sys.stdout))
    
    if fname is None: fname = config_key("nbs_path", '.', missing_ok=True)
    for f in globtastic(fname, file_glob='*.ipynb', skip_folder_re='^[_.]'): _write(f_in=f, disp=disp)

# %% ../nbs/11_clean.ipynb 15
@call_parse
def nbprocess_install_hooks():
    "Install git hooks to clean/trust notebooks automatically"
    nb_path = config_key("nbs_path", '.')
    path = get_config().config_path
    hook_path = path/'.git'/'hooks'
    fn = hook_path/'post-merge'
    hook_path.mkdir(parents=True, exist_ok=True)
    fn.write_text("#!/bin/bash\nnbprocess_trust")
    os.chmod(fn, os.stat(fn).st_mode | stat.S_IEXEC)
    #Clean notebooks on commit/diff
    (path/'.gitconfig').write_text("""# Generated by nbprocess_install_git_hooks
#
# If you need to disable this instrumentation do:
#   git config --local --unset include.path
#
# To restore the filter
#   git config --local include.path .gitconfig
#
# If you see notebooks not stripped, checked the filters are applied in .gitattributes
#
[filter "clean-nbs"]
        clean = nbprocess_clean --stdin
        smudge = cat
        required = true
[diff "ipynb"]
        textconv = nbprocess_clean --disp --fname
""")
    cmd = "git config --local include.path ../.gitconfig"
    run(cmd)
    print("Hooks are installed and repo's .gitconfig is now trusted")
    (nb_path/'.gitattributes').write_text("**/*.ipynb filter=clean-nbs\n**/*.ipynb diff=ipynb\n")
