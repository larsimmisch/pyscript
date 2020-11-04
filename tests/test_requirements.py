"""Test requirements helpers."""
from custom_components.pyscript.const import (
    ATTR_INSTALLED_VERSION,
    ATTR_SOURCES,
    ATTR_VERSION,
    CONF_INSTALLED_PACKAGES,
    DOMAIN,
    REQUIREMENTS_FILE,
    REQUIREMENTS_PATHS,
    UNPINNED_VERSION,
)
from custom_components.pyscript.requirements import install_requirements, process_all_requirements
from pytest import fixture
from pytest_homeassistant_custom_component.async_mock import patch
from pytest_homeassistant_custom_component.common import MockConfigEntry

PYSCRIPT_FOLDER = "tests/test_data/test_requirements"


@fixture(autouse=True)
def bypass_package_install_fixture():
    """Bypass package installation."""
    with patch("custom_components.pyscript.requirements.async_process_requirements"):
        yield


async def test_install_requirements(hass, caplog):
    """Test install_requirements function."""
    with patch(
        "custom_components.pyscript.requirements.process_all_requirements"
    ) as process_requirements, patch(
        "custom_components.pyscript.requirements.async_process_requirements"
    ) as ha_install_requirements:
        entry = MockConfigEntry(domain=DOMAIN, data={})
        entry.add_to_hass(hass)

        # Check that packages get installed correctly
        process_requirements.return_value = {
            "my-package-name": {
                ATTR_SOURCES: [
                    f"{PYSCRIPT_FOLDER}/requirements.txt",
                    f"{PYSCRIPT_FOLDER}/apps/app1/requirements.txt",
                ],
                ATTR_VERSION: "2.0.1",
                ATTR_INSTALLED_VERSION: None,
            },
            "my-package-name-alternate": {
                ATTR_SOURCES: [f"{PYSCRIPT_FOLDER}/requirements.txt"],
                ATTR_VERSION: "2.0.1",
                ATTR_INSTALLED_VERSION: None,
            },
        }
        await install_requirements(hass, entry, PYSCRIPT_FOLDER)
        await hass.async_block_till_done()
        assert ha_install_requirements.called
        assert ha_install_requirements.call_args[0][2] == [
            "my-package-name==2.0.1",
            "my-package-name-alternate==2.0.1",
        ]
        assert CONF_INSTALLED_PACKAGES in entry.data
        assert entry.data[CONF_INSTALLED_PACKAGES] == {
            "my-package-name": "2.0.1",
            "my-package-name-alternate": "2.0.1",
        }

        # Check that we stop tracking packages whose version no longer matches what
        # we have stored (see previous line for what we currently have stored)
        ha_install_requirements.reset_mock()
        caplog.clear()
        process_requirements.return_value = {
            "my-package-name": {
                ATTR_SOURCES: [
                    f"{PYSCRIPT_FOLDER}/requirements.txt",
                    f"{PYSCRIPT_FOLDER}/apps/app1/requirements.txt",
                ],
                ATTR_VERSION: "2.0.1",
                ATTR_INSTALLED_VERSION: "2.0.1",
            },
            "my-package-name-alternate": {
                ATTR_SOURCES: [f"{PYSCRIPT_FOLDER}/requirements.txt"],
                ATTR_VERSION: "2.0.1",
                ATTR_INSTALLED_VERSION: "1.2.1",
            },
        }
        await install_requirements(hass, entry, PYSCRIPT_FOLDER)
        await hass.async_block_till_done()
        assert not ha_install_requirements.called
        assert "WARNING" in caplog.text and "installed outside of pyscript" in caplog.text
        assert entry.data[CONF_INSTALLED_PACKAGES] == {"my-package-name": "2.0.1"}

        # Check that version upgrades are handled if the version was installed
        # by us before
        ha_install_requirements.reset_mock()
        caplog.clear()
        process_requirements.return_value = {
            "my-package-name": {
                ATTR_SOURCES: [
                    f"{PYSCRIPT_FOLDER}/requirements.txt",
                    f"{PYSCRIPT_FOLDER}/apps/app1/requirements.txt",
                ],
                ATTR_VERSION: "2.2.0",
                ATTR_INSTALLED_VERSION: "2.0.1",
            },
        }
        await install_requirements(hass, entry, PYSCRIPT_FOLDER)
        await hass.async_block_till_done()
        assert ha_install_requirements.called
        assert ha_install_requirements.call_args[0][2] == ["my-package-name==2.2.0"]
        assert entry.data[CONF_INSTALLED_PACKAGES] == {"my-package-name": "2.2.0"}

        # Check that we don't install untracked but existing packages
        ha_install_requirements.reset_mock()
        caplog.clear()
        process_requirements.return_value = {
            "my-package-name-alternate": {
                ATTR_SOURCES: [f"{PYSCRIPT_FOLDER}/requirements.txt"],
                ATTR_VERSION: "2.0.1",
                ATTR_INSTALLED_VERSION: "1.2.1",
            },
        }
        await install_requirements(hass, entry, PYSCRIPT_FOLDER)
        await hass.async_block_till_done()
        assert not ha_install_requirements.called
        assert entry.data[CONF_INSTALLED_PACKAGES] == {"my-package-name": "2.2.0"}

        # Check that we can downgrade as long as we installed the package
        ha_install_requirements.reset_mock()
        caplog.clear()
        process_requirements.return_value = {
            "my-package-name": {
                ATTR_SOURCES: [f"{PYSCRIPT_FOLDER}/requirements.txt"],
                ATTR_VERSION: "2.0.1",
                ATTR_INSTALLED_VERSION: "2.2.0",
            },
        }
        await install_requirements(hass, entry, PYSCRIPT_FOLDER)
        await hass.async_block_till_done()
        assert ha_install_requirements.called
        assert ha_install_requirements.call_args[0][2] == ["my-package-name==2.0.1"]
        assert entry.data[CONF_INSTALLED_PACKAGES] == {"my-package-name": "2.0.1"}


async def test_install_unpinned_requirements(hass, caplog):
    """Test install_requirements function with unpinned versions."""
    with patch(
        "custom_components.pyscript.requirements.process_all_requirements"
    ) as process_requirements, patch(
        "custom_components.pyscript.requirements.async_process_requirements"
    ) as ha_install_requirements:
        entry = MockConfigEntry(domain=DOMAIN, data={})
        entry.add_to_hass(hass)

        process_requirements.return_value = {
            "my-package-name": {
                ATTR_SOURCES: [
                    f"{PYSCRIPT_FOLDER}/requirements.txt",
                    f"{PYSCRIPT_FOLDER}/apps/app1/requirements.txt",
                ],
                ATTR_VERSION: UNPINNED_VERSION,
                ATTR_INSTALLED_VERSION: "2.0.1",
            },
        }
        await install_requirements(hass, entry, PYSCRIPT_FOLDER)
        await hass.async_block_till_done()
        assert not ha_install_requirements.called

        process_requirements.return_value = {
            "my-package-name": {
                ATTR_SOURCES: [
                    f"{PYSCRIPT_FOLDER}/requirements.txt",
                    f"{PYSCRIPT_FOLDER}/apps/app1/requirements.txt",
                ],
                ATTR_VERSION: UNPINNED_VERSION,
                ATTR_INSTALLED_VERSION: None,
            },
            "my-package-name-1": {
                ATTR_SOURCES: [
                    f"{PYSCRIPT_FOLDER}/requirements.txt",
                    f"{PYSCRIPT_FOLDER}/apps/app1/requirements.txt",
                ],
                ATTR_VERSION: "2.0.1",
                ATTR_INSTALLED_VERSION: None,
            },
        }
        await install_requirements(hass, entry, PYSCRIPT_FOLDER)
        await hass.async_block_till_done()
        assert ha_install_requirements.called
        assert ha_install_requirements.call_args[0][2] == ["my-package-name", "my-package-name-1==2.0.1"]
        assert entry.data[CONF_INSTALLED_PACKAGES] == {"my-package-name-1": "2.0.1"}


def test_process_requirements():
    """Test process requirements function."""
    with patch("custom_components.pyscript.requirements.installed_version", return_value=None):
        all_requirements = process_all_requirements(PYSCRIPT_FOLDER, REQUIREMENTS_PATHS, REQUIREMENTS_FILE)
        assert all_requirements == {
            "my-package-name": {
                ATTR_SOURCES: [
                    f"{PYSCRIPT_FOLDER}/requirements.txt",
                    f"{PYSCRIPT_FOLDER}/apps/app1/requirements.txt",
                ],
                ATTR_VERSION: "2.0.1",
                ATTR_INSTALLED_VERSION: None,
            },
            "my-package-name-alternate": {
                ATTR_SOURCES: [f"{PYSCRIPT_FOLDER}/requirements.txt"],
                ATTR_VERSION: "2.0.1",
                ATTR_INSTALLED_VERSION: None,
            },
            "my-package-name-alternate-1": {
                ATTR_SOURCES: [f"{PYSCRIPT_FOLDER}/requirements.txt"],
                ATTR_VERSION: "0.0.1",
                ATTR_INSTALLED_VERSION: None,
            },
        }

    with patch("custom_components.pyscript.requirements.installed_version") as installed_version:
        installed_version.side_effect = ["2.0.1", "1.0.0", None, None]
        all_requirements = process_all_requirements(PYSCRIPT_FOLDER, REQUIREMENTS_PATHS, REQUIREMENTS_FILE)
        assert all_requirements == {
            "my-package-name": {
                ATTR_SOURCES: [
                    f"{PYSCRIPT_FOLDER}/requirements.txt",
                    f"{PYSCRIPT_FOLDER}/apps/app1/requirements.txt",
                ],
                ATTR_VERSION: "2.0.1",
                ATTR_INSTALLED_VERSION: "2.0.1",
            },
            "my-package-name-alternate": {
                ATTR_SOURCES: [f"{PYSCRIPT_FOLDER}/requirements.txt"],
                ATTR_VERSION: "2.0.1",
                ATTR_INSTALLED_VERSION: "1.0.0",
            },
            "my-package-name-alternate-1": {
                ATTR_SOURCES: [f"{PYSCRIPT_FOLDER}/requirements.txt"],
                ATTR_VERSION: "0.0.1",
                ATTR_INSTALLED_VERSION: None,
            },
        }
