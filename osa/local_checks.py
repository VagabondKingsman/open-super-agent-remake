"""Opt-in, allowlisted fixture checks in bubblewrap; never a general host shell."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import signal
import subprocess
import sys
import tempfile
import uuid
from . import memory

HINT = ("\nFor registered code fixtures, inspect_repo first (including existing tests), then check_patch with the returned snapshot and exact unified diff. "
        "Only deliver a patch after git apply --check AND sandbox pytest PASS; otherwise fix/iterate or report BLOCKED. "
        "Never infer apply/test PASS from hunk counting. Preserve actual comments and existing tests; tests are append-only. ")


def registry_file():
    return memory.db_path.parent / "local-checks.json"


def _relative(name):
    p = PurePosixPath(name)
    if not name or p.is_absolute() or ".." in p.parts or any(c in name for c in "\n\r\t ") or name.startswith("-"):
        raise ValueError("Invalid allowlisted file")
    return p


def _load(repo):
    cfg = json.loads(registry_file().read_text()) if registry_file().exists() else {}
    selected = [(k,v) for k,v in cfg.items() if repo in (k,v["path"])]
    if len(selected) != 1:
        raise ValueError("Repository is not registered by the operator; no host access granted")
    key, spec = selected[0]
    root = Path(spec["path"])
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Repository root missing or symlinked")
    files = {}
    for name in spec["files"]:
        rel = _relative(name); target = root / rel
        if any((root / Path(*rel.parts[:i])).is_symlink() for i in range(1,len(rel.parts)+1)):
            raise ValueError("Symlinks are forbidden")
        if not target.is_file() or target.stat().st_size > 64000:
            raise ValueError("Allowlisted source missing or too large")
        files[name] = target.read_text(encoding="utf-8")
    if not spec["tests"] or not set(spec["tests"]) <= files.keys():
        raise ValueError("Trusted test targets must be existing allowlisted files")
    acceptance = Path(spec["acceptance_file"]).read_text() if spec.get("acceptance_file") else ""
    snapshot = hashlib.sha256(json.dumps([files,spec["tests"],acceptance],sort_keys=True).encode()).hexdigest()
    return key,spec,files,acceptance,snapshot


def runtime_hint():
    if not registry_file().exists():
        return HINT + "No repositories registered: report this blocker rather than run code on the host."
    cfg=json.loads(registry_file().read_text())
    return HINT + " Registered repository ids/paths: " + json.dumps({k:v["path"] for k,v in cfg.items()})


def inspect(repo):
    key,spec,files,_,snapshot = _load(repo)
    out={"repo":key,"snapshot":snapshot,"files":files,"tests":spec["tests"],
         "constraints":"Original files remain untouched. Existing tests append-only. Validate exact diff with check_patch; fixed acceptance tests also run."}
    if len(json.dumps(out,ensure_ascii=False))>7500:
        raise ValueError("Inspection too large; operator must narrow the allowlist")
    return out


def _run(work, argv, log):
    if sys.platform != "linux" or not all(shutil.which(x) for x in ("bwrap","prlimit","git","ps")):
        return {"exit_code":None,"output":"BLOCKED: Linux + bubblewrap/prlimit/git/ps required; no unsandboxed fallback"}
    # RLIMIT_NPROC counts every thread of this shared uid, not only this sandbox.
    threads=len(subprocess.check_output(["/usr/bin/ps","-u",str(os.getuid()),"-L","-o","lwp="],text=True).splitlines())
    cmd=["prlimit","--cpu=10","--as=536870912","--fsize=1048576","--nofile=128",f"--nproc={threads+32}","--",
         "bwrap","--unshare-all","--die-with-parent","--new-session","--cap-drop","ALL",
         "--ro-bind","/usr","/usr","--symlink","usr/bin","/bin","--symlink","usr/lib","/lib","--symlink","usr/lib64","/lib64",
         "--ro-bind",str(Path(sys.executable).parent.parent),str(Path(sys.executable).parent.parent),
         "--proc","/proc","--dev","/dev","--tmpfs","/tmp","--bind",str(work),"/work",
         "--clearenv","--setenv","PATH","/usr/bin:/bin","--setenv","HOME","/tmp",
         "--setenv","GIT_CONFIG_NOSYSTEM","1","--setenv","PYTEST_DISABLE_PLUGIN_AUTOLOAD","1",
         "--setenv","PYTHONDONTWRITEBYTECODE","1","--chdir","/work"]
    acceptance=work.parent/"acceptance"
    if acceptance.exists(): cmd += ["--ro-bind",str(acceptance),"/acceptance"]
    if not Path(sys.base_prefix).is_relative_to("/usr"):
        cmd += ["--ro-bind",sys.base_prefix,sys.base_prefix]
    cmd += argv
    with log.open("wb") as stream:
        proc=subprocess.Popen(cmd,stdout=stream,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True,
                              env={"PATH":"/usr/bin:/bin"},close_fds=True)
        try: code=proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid,signal.SIGKILL);proc.wait();code=124
    data=log.read_bytes()
    return {"argv":argv,"exit_code":code,"output":data[:5000].decode(errors="replace"),"output_truncated":len(data)>5000}


def check(repo,snapshot,patch):
    key,spec,files,acceptance,current = _load(repo)
    if snapshot != current:
        raise ValueError("Source snapshot changed or inspection missing; inspect_repo again")
    if not isinstance(patch,str) or not patch or len(patch)>30000:
        raise ValueError("Expected a unified diff up to 30000 characters")
    names=[]
    for line in patch.splitlines():
        if line.startswith(("--- ","+++ ")):
            name=line[4:]
            if not name.startswith(("a/","b/")) or str(_relative(name[2:])) not in files:
                raise ValueError("Patch targets must be existing allowlisted files; no create/delete/rename")
            names.append(name[2:])
        elif line.startswith("diff --git "):
            parts=line.split()
            if len(parts)!=4 or any(not n.startswith(("a/","b/")) or str(_relative(n[2:])) not in files for n in parts[2:]):
                raise ValueError("Extended diff path is not allowlisted")
        elif line.startswith(("copy ","new file mode","deleted file mode","rename ","old mode","new mode","GIT binary patch")):
            raise ValueError("Patch metadata changes forbidden")
    if not names: raise ValueError("No unified diff file headers")
    with tempfile.TemporaryDirectory(prefix="osa-check-") as temporary:
        base=Path(temporary);work=base/"work";work.mkdir()
        for name,text in files.items():
            dest=work/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(text)
        (work/"candidate.patch").write_text(patch)
        if acceptance:
            (base/"acceptance").mkdir();(base/"acceptance/test_contract.py").write_text(acceptance)
        stages=[_run(work,["/usr/bin/git","apply","--check","/work/candidate.patch"],base/"check.log")]
        if stages[-1]["exit_code"]==0:
            stages.append(_run(work,["/usr/bin/git","apply","/work/candidate.patch"],base/"apply.log"))
        intact=all(not (work/t).is_symlink() and (work/t).is_file() and (work/t).read_text().startswith(files[t]) for t in spec["tests"])
        if stages[-1]["exit_code"]==0 and intact:
            targets=["/work/"+t for t in spec["tests"]]+(["/acceptance/test_contract.py"] if acceptance else [])
            stages.append(_run(work,[sys.executable,"-I","-m","pytest","-q","-rA","-p","no:cacheprovider",*targets],base/"pytest.log"))
        unchanged=_load(repo)[-1]==current
        passed=len(stages)==3 and all(s["exit_code"]==0 for s in stages) and intact and unchanged
        blocked=any(s["exit_code"] is None or (s["exit_code"]!=0 and s["output"].startswith(("bwrap:","prlimit:"))) for s in stages)
        out={"status":"PASS" if passed else "BLOCKED" if blocked else "FAIL","repo":key,"snapshot":current,
             "patch_sha256":hashlib.sha256(patch.encode()).hexdigest(),"stages":stages,
             "existing_tests_preserved":intact,"original_repo_unchanged":unchanged,
             "isolation":"bubblewrap: new user/mount/pid/network namespaces; no network/host secrets; temp copy only; CPU/memory/time/output limits"}
    token=uuid.uuid4().hex;dest=memory.db_path.parent/"local-check-results"/token;dest.mkdir(parents=True)
    (dest/"result.json").write_text(json.dumps(out,ensure_ascii=False,indent=2))
    if passed:(dest/"accepted.patch").write_text(patch)
    out["evidence_id"]=token
    return out


def tool(name,args):
    try:
        out=inspect(args.get("repo")) if name=="inspect_repo" else check(args.get("repo"),args.get("snapshot"),args.get("patch"))
        raw=json.dumps(out,ensure_ascii=False)
        if len(raw)>7500:
            for stage in out.get("stages",[]):stage["output"]=stage["output"][:1500];stage["output_truncated"]=True
            raw=json.dumps(out,ensure_ascii=False)
        return raw
    except (ValueError,OSError,TypeError,KeyError) as e:
        return json.dumps({"status":"BLOCKED","error":str(e)},ensure_ascii=False)


SCHEMAS=[{"type":"function","function":{"name":"inspect_repo","description":"Read operator-registered real fixture source AND existing tests; return snapshot required by check_patch. No arbitrary host paths.","parameters":{"type":"object","properties":{"repo":{"type":"string"}},"required":["repo"]}}},
 {"type":"function","function":{"name":"check_patch","description":"Validate exact patch against inspected fixture snapshot: git apply --check, temp-copy apply, existing+trusted acceptance pytest in offline bubblewrap sandbox. Deliver only PASS exact patch SHA; iterate on FAIL. No host writes or arbitrary commands.","parameters":{"type":"object","properties":{"repo":{"type":"string"},"snapshot":{"type":"string"},"patch":{"type":"string"}},"required":["repo","snapshot","patch"]}}}]
NAMES={s["function"]["name"] for s in SCHEMAS}
