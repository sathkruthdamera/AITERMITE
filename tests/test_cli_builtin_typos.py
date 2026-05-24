from aitermite.cli import main


def test_aitermite_dotcor_maps_to_doctor(capsys):
    code = main(["dotcor", "--no-color"])
    output = capsys.readouterr().out
    assert code == 0
    assert "Fix: aitermite doctor" in output
    assert "AITERMITE doctor" in output


def test_aitermite_doctor_alias_runs(capsys):
    code = main(["doctor", "--no-color"])
    output = capsys.readouterr().out
    assert code == 0
    assert "AITERMITE doctor" in output
