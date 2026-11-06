import difflib,json,sys
from pathlib import Path
import pytest
from osa import local_checks

SANDBOX = sys.platform == "linux" and all(local_checks.shutil.which(x) for x in ("bwrap","prlimit","git","ps"))


@pytest.fixture
def registered(tmp_path,monkeypatch):
    repo=tmp_path/'fixture';repo.mkdir()
    (repo/'calc.py').write_text('def answer():\n    return 1\n')
    (repo/'test_calc.py').write_text('from calc import answer\ndef test_answer():\n    assert answer()==2\n')
    config=tmp_path/'local-checks.json';config.write_text(json.dumps({'fixture':{'path':str(repo),'files':['calc.py','test_calc.py'],'tests':['test_calc.py']}}))
    monkeypatch.setattr(local_checks,'registry_file',lambda:config)
    monkeypatch.setattr(local_checks.memory,'db_path',tmp_path/'osa.db')
    return repo


def patch_for(repo):
    old=(repo/'calc.py').read_text();new=old.replace('return 1','return 2')
    return ''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/calc.py',tofile='b/calc.py'))


def test_registered_inspection_and_reject_stale(registered):
    result=local_checks.inspect('fixture')
    assert 'test_calc.py' in result['files']
    assert json.loads(local_checks.tool('inspect_repo',{'repo':'/etc'}))['status']=='BLOCKED'
    assert json.loads(local_checks.tool('check_patch',{'repo':'fixture','snapshot':'stale','patch':patch_for(registered)}))['status']=='BLOCKED'


@pytest.mark.parametrize('patch',['--- a/../../secret\n+++ b/../../secret\n','--- /dev/null\n+++ b/new.py\n','diff --git a/evil b/evil\n--- a/calc.py\n+++ b/calc.py\n','old mode 100644\nnew mode 120000\n'])
def test_reject_paths_metadata(registered,patch):
    snap=local_checks.inspect('fixture')['snapshot']
    assert json.loads(local_checks.tool('check_patch',{'repo':'fixture','snapshot':snap,'patch':patch}))['status']=='BLOCKED'


@pytest.mark.skipif(not SANDBOX,reason="Linux bubblewrap sandbox unavailable")
def test_real_offline_sandbox_apply_and_pytest(registered):
    before={p.name:p.read_bytes() for p in registered.iterdir()}
    snap=local_checks.inspect('fixture')['snapshot'];out=local_checks.check('fixture',snap,patch_for(registered))
    assert out['status']=='PASS',out
    assert [s['exit_code'] for s in out['stages']]==[0,0,0]
    assert out['original_repo_unchanged'] and before=={p.name:p.read_bytes() for p in registered.iterdir()}


@pytest.mark.skipif(not SANDBOX,reason="Linux bubblewrap sandbox unavailable")
def test_sandbox_hides_host_files_and_network(tmp_path):
    work=tmp_path/'work';work.mkdir();canary=tmp_path/'private';canary.write_text('host only')
    code=f"import pathlib,socket;assert not pathlib.Path({str(canary)!r}).exists();s=socket.socket();s.settimeout(1);\ntry:s.connect(('127.0.0.1',8765));raise AssertionError('host network reached')\nexcept OSError:print('ISOLATED')"
    r=local_checks._run(work,[sys.executable,'-I','-c',code],tmp_path/'log')
    assert r['exit_code']==0 and 'ISOLATED' in r['output'],r


@pytest.mark.skipif(not SANDBOX,reason="Linux bubblewrap sandbox unavailable")
def test_test_weakening_is_not_pass(registered):
    snap=local_checks.inspect('fixture')['snapshot'];old=(registered/'test_calc.py').read_text()
    p=''.join(difflib.unified_diff(old.splitlines(True),old.replace('==2','==1').splitlines(True),fromfile='a/test_calc.py',tofile='b/test_calc.py'))
    out=local_checks.check('fixture',snap,p)
    assert out['status']=='FAIL' and not out['existing_tests_preserved']


def test_missing_sandbox_never_falls_back(registered,monkeypatch):
    monkeypatch.setattr(local_checks.shutil,'which',lambda _:None)
    out=local_checks.check('fixture',local_checks.inspect('fixture')['snapshot'],patch_for(registered))
    assert out['status']=='BLOCKED' and out['stages'][0]['exit_code'] is None
