import json

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
            elapsed_time = payload["time"]
            status = event.replace("Print", "").lower()
            self.send_notification(status, flnm, elapsed_time)

    @staticmethod
    def time_format(elapsed_time: float):
        """
        Convert the elapsed time in seconds to D:H:M:S format.
        Modified based on this post https://stackoverflow.com/a/68321739/7066315.

        Args:
            elapsed_time (float): elapsed time for the job

        Returns:
            str: formatted time string
        """
        # less 1 second doesn't really matter in this case
        # get rid of it
        elapsed_time = int(elapsed_time)
        d = elapsed_time // (3600 * 24)
        h = elapsed_time // 3600 % 24
        m = elapsed_time % 3600 // 60
        s = elapsed_time % 3600 % 60
        formatted_time = ""
        if d > 0:
            formatted_time += f" {d} day"
            if d > 1:
                formatted_time += "s"
        if h > 0:
            formatted_time += f" {h} hour"
            if h > 1:
                formatted_time += "s"
        if m > 0:
            formatted_time += f" {m} minute"
            if m > 1:
                formatted_time += "s"
        if s > 0:
            formatted_time += f" {s} second"
            if s > 1:
                formatted_time += "s"
        return formatted_time

    def send_notification(self, status: str, file: str, elapsed_time: float):
        """
        Send the notification to Echo.

        Args:
            status (str): the status of the job
            file (str): name of the print
            elapsed_time (float): elapsed time from the Octoprint payload
        """
        # get the access code from the settings
        token = self._settings.get(["token"])
        # if no access code given, throw an error
        if not token:
            self._logger.error(
                "Notify me access code is NOT set. Unable to send notifications."
            )
        # format time
        elapsed_time = self.time_format(elapsed_time)
        # build the message
        body = json.dumps(
            {
                "notification": f"Print job {file} is {status}! Time taken {elapsed_time}.",
                "accessCode": token,
            }
        )
        # self._logger.warning(f"Message body {body}")
        # send it out
        response = requests.post(
            url="https://api.notifymyecho.com/v1/NotifyMe", data=body
        )
        # check HTTP return code, throw an error is the request fails
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
