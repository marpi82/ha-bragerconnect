# bragerconnect

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]
![Project Maintenance][maintenance-shield]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

[![Community Forum][forum-shield]][forum]

![brager][bragerimg]
_Component to integrate with [BragerConnect][bragerconnect]._

**This component will set up the following platforms.**

Platform | Description
-- | --
`binary_sensor` | Show something `True` or `False`.
`sensor` | Show info from blueprint API.
`switch` | Switch something `True` or `False`.

## Installation

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
2. If you do not have a `custom_components` directory (folder) there, you need to create it.
3. In the `custom_components` directory (folder) create a new folder called `integration_blueprint`.
4. Download _all_ the files from the `custom_components/integration_blueprint/` directory (folder) in this repository.
5. Place the files you downloaded in the new directory (folder) you created.
6. Restart Home Assistant
7. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Integration blueprint"

Using your HA configuration directory (folder) as a starting point you should now also have this:

```text
custom_components/integration_blueprint/translations/en.json
custom_components/integration_blueprint/translations/nb.json
custom_components/integration_blueprint/translations/sensor.nb.json
custom_components/integration_blueprint/__init__.py
custom_components/integration_blueprint/api.py
custom_components/integration_blueprint/binary_sensor.py
custom_components/integration_blueprint/config_flow.py
custom_components/integration_blueprint/const.py
custom_components/integration_blueprint/manifest.json
custom_components/integration_blueprint/sensor.py
custom_components/integration_blueprint/switch.py
```

## Configuration is done in the UI

<!---->

## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

***

[bragerconnect]: https://cloud.bragerconnect.com
[buymecoffee]: https://www.buymeacoffee.com/marpi82
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge
[commits-shield]: https://img.shields.io/github/commit-activity/y/marpi82/ha-bragerconnect.svg?style=for-the-badge
[commits]: https://github.com/marpi82/ha-bragerconnect/commits/master
[hacs]: https://github.com/custom-components/hacs
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[bragerimg]: images/brager_logo.svg
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/github/license/marpi82/ha-bragerconnect.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-Marek%20Pilch%20%40marpi82-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/marpi82/ha-bragerconnect.svg?style=for-the-badge
[releases]: https://github.com/marpi82/ha-bragerconnect/releases
