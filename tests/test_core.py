from envguard.core import parse_env, validate
from envguard.leaks import find_leaks
from envguard.diff import diff_envs


def test_parse_env_strips_comments_and_quotes():
    text = "# comment\nAPI_URL=https://x.com\nPORT=8080\nNAME=\"hi\"\n"
    env = parse_env(text)
    assert env == {"API_URL": "https://x.com", "PORT": "8080", "NAME": "hi"}


def test_validate_pass():
    env = {"API_URL": "https://x.com", "PORT": "8080"}
    schema = {
        "API_URL": {"required": True, "type": "url"},
        "PORT": {"required": True, "type": "int"},
    }
    res = validate(env, schema)
    assert res.ok, res.errors


def test_validate_missing_required():
    res = validate({}, {"API_URL": {"required": True, "type": "url"}})
    assert not res.ok
    assert res.errors[0].key == "API_URL"


def test_validate_wrong_type():
    res = validate({"PORT": "abc"}, {"PORT": {"required": True, "type": "int"}})
    assert not res.ok


def test_validate_unknown_key_flagged():
    res = validate({"MYSTERY": "x"}, {})
    assert any(e.key == "MYSTERY" for e in res.errors)


def test_find_leaks_aws():
    env = {"AWS_KEY": "AKIAIOSFODNN7EXAMPLE"}
    leaks = find_leaks(env)
    assert ("AWS_KEY", "AWS_ACCESS_KEY") in leaks


def test_diff_detects_change_and_add():
    d = diff_envs({"A": "1"}, {"A": "2", "B": "3"})
    assert d["changed"] == {"A": ("1", "2")}
    assert d["added"] == {"B": "3"}
