from tests.support.repository import REPOSITORY_ROOT


def test_verify_generated_uses_real_nul_delimiter_for_git_z_output():
    text = (REPOSITORY_ROOT / "Makefile").read_text(encoding="utf-8")
    recipe = next(line for line in text.splitlines() if "untracked=lambda:" in line)
    assert r".split(b'\0')" in recipe
    assert r"p+b'\0'" in recipe
    assert r".split(b'\\0')" not in recipe
    assert r"p+b'\\0'" not in recipe
