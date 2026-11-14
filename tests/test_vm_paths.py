"""C54: máy ảo không phải host — prompt phải nói đường dẫn của host không tồn tại ở đó."""
from osa.computer import tools


class C:
    workspace = '/data/workspace'
    backend = 'instabox'

    def shell_enabled(self):
        return True

    def desktop_enabled(self):
        return False


def test_a_vm_prompt_names_the_machine_and_its_folder():
    for text in (tools._intro(C()), tools.capability(C())):
        assert 'different machine' in text and '/data/workspace' in text


def test_a_host_prompt_does_not_claim_another_machine():
    c = C(); c.backend = 'host'
    assert 'different machine' not in tools._intro(c)
    assert 'different machine' not in tools.capability(c)
