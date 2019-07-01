from pytest import main

class TestMy:
    def test_silly(self):
        assert True

main(['{}::{}'.format(__file__, TestMy.__name__)])