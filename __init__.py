import json
from typing import Union

import requests
from octoprint.events import Events
from octoprint.plugin import EventHandlerPlugin, SettingsPlugin, TemplatePlugin


class AlexaNotificationPlugin(EventHandlerPlugin, SettingsPlugin, TemplatePlugin):
    _setting_fields = [
        "PrintStarted",
        "PrintDone",
        "PrintFailed",
        "PrintCancelled",
        "PrintPaused",
        "PrintResumed",
    ]

    def __init__(self):
        self.job_failed = False

    def get_template_vars(self):
        settings = {"token": self._settings.get(["token"])}
        for key in self._setting_fields:
            settings[key] = self._settings.get([key])
        self._logger.info(f"Current settings: {settings}")
        return settings

    def get_template_configs(self):
        return [
            dict(type="navbar", custom_bindings=False),
            dict(type="settings", custom_bindings=False),
        ]

    def on_event(self, event, payload):
        # self._logger.warning(f"I got an event, which is {event}")
        if self._settings.get([event]):
            if event == Events.PRINT_CANCELLED:
                self.job_failed = True
            elif event == Events.PRINT_FAILED and self.job_failed:
                # if job_failed = True, the cancelled job is handled already
                # no additional notifications will be sent
                self.job_failed = False
                return
            # self._logger.warning(f"The payload is {payload}")
            flnm = payload["name"]
            print_time = payload["time"]
            status = event.replace("Print", "").lower()
            self.send_notifications(status, flnm, print_time)

    @staticmethod
    def time_format(print_time: Union[int, float]):
        if type(print_time) != int:
            if type(print_time) == float:
                print_time = int(print_time)
            else:
                return
        d = print_time // (3600 * 24)
        h = print_time // 3600 % 24
        m = print_time % 3600 // 60
        s = print_time % 3600 % 60
        converted_time = ""
        if d > 0:
            converted_time += f" {d} days"
        if h > 0:
            converted_time += f" {h} hours"
        if m > 0:
            converted_time += f" {m} minutes"
        if s > 0:
            converted_time += f" {s} seconds"
        return converted_time

    def send_notifications(self, status, file, print_time):
        token = self._settings.get(["token"])
        if not token:
            self._logger.error(
                "Notify me access code is NOT set. Unable to send notifications"
            )
        print_time = self.time_format(print_time)
        body = json.dumps(
            {
                "notification": f"Print job {file} is {status}! Time taken {print_time}.",
                "accessCode": token,
            }
        )
        # self._logger.warning(f"Message body {body}")
        response = requests.post(
            url="https://api.notifymyecho.com/v1/NotifyMe", data=body
        )
        if response.ok:
            self._logger.info(f"Notification successfully sent to your Echo devices.")
        else:
            self._logger.error(
                (
                    "Failed to send the notification."
                    f"HTTP error code {response.status_code}. Reason {response.reason}."
                )
            )


__plugin_name__ = "Alexa Notifications"
__plugin_version__ = "0.0.1a1"
__plugin_description__ = (
    "Send notifications to Amazon Echo devices on print job statuses."
)
__plugin_pythoncompat__ = ">=3.7,<4"
__plugin_implementation__ = AlexaNotificationPlugin()
