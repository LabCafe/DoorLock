# Lab.cafe Door Lock

This is a program written in Python used to control the doors in Lab.cafe.

## Installation

Use [pip](https://pip.pypa.io/en/stable/) to install all the required libraries.

```bash
sudo pip3 install requests datetime rdm6300 python-dotenv RPi.GPIO RPLCD smbus2
```

Create a `.env` file containing the Fabmab API key under `API_KEY` variable
```bash
nano ./src/.env
```
```yaml
API_KEY=<key>
```

Set up CRON
```bash
sudo crontab -e
```
```text
@reboot cd /home/DoorLock/src && sudo python3 ./<file_name>.py
```
Reboot
```bash
sudo reboot
```

## License
[MIT](https://choosealicense.com/licenses/mit/)
