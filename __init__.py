import json

import requests
from octoprint.events import Events
from octoprint.plugin import EventHandlerPlugin, SettingsPlugin, TemplatePlugin


class AlexaNotificationPlugin(EventHandlerPlugin, SettingsPlugin, TemplatePlugin):
    def __init__(self):
        self.cancelled = False
        self.token = None
        self.handled_events = {
            "PrintStarted": False,
            "PrintDone": False,
            "PrintFailed": False,
            "PrintCancelled": False,
            "PrintPaused": False,
            "PrintResumed": False,
        }

    def get_template_vars(self):
        self.token = self._settings.get(["token"])
        output = "Handled events:"
        for key in self.handled_events:
            self.handled_events[key] = self._settings.get([key])
            if self.handled_events[key]:
                output += f" {key},"
        output = output[:-1] + "."
        self._logger.info(f"using access code: {self.token}. {output}")
        return self.handled_events.copy().update({"token": self.token})

    def get_template_configs(self):
        return [
            dict(type="navbar", custom_bindings=False),
            dict(type="settings", custom_bindings=False),
        ]

    def on_event(self, event, payload):
        self._logger.debug(
            f"I got an event, which is {event} with payload of {payload}"
        )
        if self.handled_events.get(event):
            if event == Events.PRINT_FAILED:
                # the cancelled job is handled or ignored already
                # no additional notifications will be sent
                if payload["reason"] == "cancelled":
                    return
            self.send_notification(event, payload)
        elif event == Events.SETTINGS_UPDATED:
            self._logger.debug("update settings instantly")
            return self.get_template_vars()

    def send_notification(self, event: str, payload: dict):
        """
        Send the notification to Echo.

        Args:
            event (str): event name
            payload (dict): payload of the event
        """
        # get the access code from the settings
        token = self._settings.get(["token"])
        # if no access code given, throw an error
        if not token:
            self._logger.error(
                "Notify me access code is NOT set. Unable to send notifications."
            )
        if event == Events.ERROR:
            # TODO: handle unrecoverable errors
            pass
        else:
            msg = self.print_job_messages(event, payload)
        # build the message
        body = json.dumps({"notification": msg, "accessCode": token})
        self._logger.debug(f"Message body {body}")
        # send it out
        response = requests.post(
            url="https://api.notifymyecho.com/v1/NotifyMe", data=body
        )
        # check HTTP return code, throw an error is the request fails
        if response.ok:
            self._logger.debug(f"Notification successfully sent to your Echo devices.")
        else:
            self._logger.error(
                (
                    "Failed to send the notification."
                    f"HTTP error code {response.status_code}. Reason {response.reason}."
                )
            )

    def print_job_messages(self, event: str, payload: dict):
        """
        Construct the message for the notification for a print related event.

        Args:
            event (str): event name
            payload (dict): payload of the event

        Returns:
            str: message
        """
        status = event[5:].lower()
        flnm = payload["name"]
        msg = f"Print job {flnm} is {status}!"
        if status == "started" or status == "paused" or status == "resumed":
            return msg
        elapsed_time = payload["time"]
        # format time
        elapsed_time = self.time_format(elapsed_time)
        msg += f" Time taken {elapsed_time}."
        if status == "failed":
            if payload["reason"] == "error":
                error_msg = payload["error"]
                if not error_msg:
                    error_msg = "empty"
            msg += f" Failure was because of error. Error message was {error_msg}"
        return msg

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


__plugin_name__ = "Alexa Notifications"
__plugin_version__ = "0.0.1a2"
__plugin_description__ = (
    "Send notifications to Amazon Echo devices on print job statuses."
)
__plugin_pythoncompat__ = ">=3.7,<4"
__plugin_implementation__ = AlexaNotificationPlugin()
