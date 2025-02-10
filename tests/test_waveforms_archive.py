import os
import shutil
import pytest
from obspy.core.event import read_events
from obspy.core.inventory import read_inventory
from seed_vault.service.seismoloader import  run_event, run_continuous
from seed_vault.models.config import SeismoLoaderSettings


@pytest.fixture
def test_settings():
    """Fixture to load real settings from a test config file."""
    settings = SeismoLoaderSettings.from_cfg_file("tests/config_test.cfg")  # Load config

    catalogs = read_events("tests/event_selected_test.xml")
    invs     = read_inventory("tests/station_selected_test.xml")

    settings.event.selected_catalogs = catalogs
    settings.station.selected_invs   = invs

    return settings



@pytest.fixture
def clean_up_data(test_settings):
    if os.path.exists(test_settings.sds_path):
        shutil.rmtree(test_settings.sds_path)
    if os.path.exists(test_settings.db_path):
        os.remove(test_settings.db_path)
    yield


@pytest.fixture
def check_real_data(pytestconfig):
    if not pytestconfig.getoption("--run-real-fdsn"):
        pytest.skip("Skipping real FDSN test")
    

# ========================================
# TEST WITH REAL FDSN API
# ========================================

def test_get_fresh_data(test_settings: SeismoLoaderSettings, clean_up_data, check_real_data):
    
    test_settings.download_type = 'event'
    event_streams = run_event(test_settings)

    assert event_streams, "Expected waveform data but got None or an empty list."
    for stream in event_streams:
        assert len(stream) > 0, "Expected non-empty waveform data."

    assert os.path.exists(test_settings.sds_path)
    assert os.path.exists(test_settings.db_path)



