from athena.utils import config


def test_is_collection_on_list():
    assert config.is_collection([]) is True


def test_is_collection_on_dict():
    assert config.is_collection({}) is True


def test_is_collection_on_string():
    assert config.is_collection("some string") is False


def test_is_collection_on_int():
    assert config.is_collection(666) is False
